from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from collections import defaultdict

User = get_user_model()


class Command(BaseCommand):
    help = 'Проверка и исправление конфликтов пользователей в системе'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Автоматически исправить найденные конфликты',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет исправлено без внесения изменений',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('=== Проверка конфликтов пользователей ===')
        )

        conflicts = self.find_conflicts()
        
        if not conflicts:
            self.stdout.write(
                self.style.SUCCESS('✅ Конфликтов не обнаружено')
            )
            return

        self.display_conflicts(conflicts)

        if options['fix'] or options['dry_run']:
            self.fix_conflicts(conflicts, dry_run=options['dry_run'])
        else:
            self.stdout.write(
                self.style.WARNING(
                    '\nДля исправления конфликтов запустите команду с флагом --fix'
                )
            )

    def find_conflicts(self):
        """Поиск всех типов конфликтов"""
        conflicts = {
            'username_display_conflicts': [],
            'duplicate_display_names': [],
            'duplicate_usernames': [],
        }

        users = User.objects.all()

        # 1. Конфликты username vs display_name
        for user in users:
            if user.display_name:
                conflicting_user = User.objects.filter(
                    username=user.display_name
                ).exclude(pk=user.pk).first()
                
                if conflicting_user:
                    conflicts['username_display_conflicts'].append({
                        'user_with_display': user,
                        'user_with_username': conflicting_user,
                        'conflicting_name': user.display_name
                    })

        # 2. Дублирующиеся display_name
        display_names = defaultdict(list)
        for user in users:
            if user.display_name:
                display_names[user.display_name].append(user)
        
        for name, user_list in display_names.items():
            if len(user_list) > 1:
                conflicts['duplicate_display_names'].append({
                    'name': name,
                    'users': user_list
                })

        # 3. Дублирующиеся username (не должно быть, но проверим)
        usernames = defaultdict(list)
        for user in users:
            usernames[user.username].append(user)
        
        for name, user_list in usernames.items():
            if len(user_list) > 1:
                conflicts['duplicate_usernames'].append({
                    'name': name,
                    'users': user_list
                })

        return conflicts

    def display_conflicts(self, conflicts):
        """Отображение найденных конфликтов"""
        total_conflicts = sum(len(v) for v in conflicts.values())
        
        self.stdout.write(
            self.style.ERROR(f'❌ Найдено конфликтов: {total_conflicts}')
        )

        # Username vs Display Name конфликты
        if conflicts['username_display_conflicts']:
            self.stdout.write('\n📋 Конфликты username vs display_name:')
            for conflict in conflicts['username_display_conflicts']:
                self.stdout.write(
                    f"  • Пользователь '{conflict['user_with_display'].username}' "
                    f"имеет display_name '{conflict['conflicting_name']}', "
                    f"но это username пользователя '{conflict['user_with_username'].username}'"
                )

        # Дублирующиеся display_name
        if conflicts['duplicate_display_names']:
            self.stdout.write('\n📋 Дублирующиеся display_name:')
            for conflict in conflicts['duplicate_display_names']:
                usernames = [u.username for u in conflict['users']]
                self.stdout.write(
                    f"  • Display name '{conflict['name']}' используется пользователями: "
                    f"{', '.join(usernames)}"
                )

        # Дублирующиеся username
        if conflicts['duplicate_usernames']:
            self.stdout.write('\n📋 Дублирующиеся username:')
            for conflict in conflicts['duplicate_usernames']:
                ids = [str(u.id) for u in conflict['users']]
                self.stdout.write(
                    f"  • Username '{conflict['name']}' используется пользователями с ID: "
                    f"{', '.join(ids)}"
                )

    def fix_conflicts(self, conflicts, dry_run=False):
        """Исправление конфликтов"""
        if dry_run:
            self.stdout.write(
                self.style.WARNING('\n🔍 РЕЖИМ ПРЕДВАРИТЕЛЬНОГО ПРОСМОТРА (изменения не будут сохранены)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n🔧 Исправление конфликтов...')
            )

        try:
            with transaction.atomic():
                # Исправление дублирующихся display_name
                self.fix_duplicate_display_names(conflicts['duplicate_display_names'], dry_run)
                
                # Исправление конфликтов username vs display_name
                self.fix_username_display_conflicts(conflicts['username_display_conflicts'], dry_run)
                
                # Дублирующиеся username - критическая ошибка
                if conflicts['duplicate_usernames']:
                    raise CommandError(
                        "Обнаружены дублирующиеся username! Это критическая ошибка базы данных."
                    )
                
                if dry_run:
                    # Откатываем транзакцию в режиме предварительного просмотра
                    transaction.set_rollback(True)
                    self.stdout.write(
                        self.style.SUCCESS('✅ Предварительный просмотр завершен')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS('✅ Все конфликты исправлены')
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка при исправлении конфликтов: {e}')
            )
            raise

    def fix_duplicate_display_names(self, conflicts, dry_run):
        """Исправление дублирующихся display_name"""
        for conflict in conflicts:
            name = conflict['name']
            users = conflict['users']
            
            # Оставляем display_name у первого пользователя (обычно старшего по ID)
            primary_user = min(users, key=lambda u: u.id)
            
            for user in users:
                if user.id != primary_user.id:
                    new_display_name = f"{name} ({user.username})"
                    
                    if dry_run:
                        self.stdout.write(
                            f"  📝 Изменить display_name пользователя '{user.username}' "
                            f"с '{user.display_name}' на '{new_display_name}'"
                        )
                    else:
                        user.display_name = new_display_name
                        user.save()
                        self.stdout.write(
                            f"  ✅ Изменен display_name пользователя '{user.username}' "
                            f"на '{new_display_name}'"
                        )

    def fix_username_display_conflicts(self, conflicts, dry_run):
        """Исправление конфликтов username vs display_name"""
        for conflict in conflicts:
            user_with_display = conflict['user_with_display']
            conflicting_name = conflict['conflicting_name']
            
            new_display_name = f"{conflicting_name} (display)"
            
            if dry_run:
                self.stdout.write(
                    f"  📝 Изменить display_name пользователя '{user_with_display.username}' "
                    f"с '{user_with_display.display_name}' на '{new_display_name}'"
                )
            else:
                user_with_display.display_name = new_display_name
                user_with_display.save()
                self.stdout.write(
                    f"  ✅ Изменен display_name пользователя '{user_with_display.username}' "
                    f"на '{new_display_name}'"
                )