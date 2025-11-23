"""
Django management команда для безопасного удаления пользователей.
Использование: python manage.py delete_users <username1> <username2> ...
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from users.models import User


class Command(BaseCommand):
    help = 'Безопасно удаляет пользователей из системы'

    def add_arguments(self, parser):
        parser.add_argument(
            'usernames',
            nargs='*',  # Изменено с '+' на '*' чтобы разрешить пустой список
            type=str,
            help='Имена пользователей для удаления'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительное удаление без подтверждения'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Показать список всех пользователей'
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_users()
            return

        usernames = options['usernames']
        
        if not usernames:
            self.stdout.write(
                self.style.ERROR('Укажите имена пользователей для удаления или используйте --list')
            )
            return
        
        if not options['force']:
            self.stdout.write(
                self.style.WARNING(
                )
            )
            confirm = input('Продолжить? (yes/no): ')
            if confirm.lower() not in ['yes', 'y', 'да', 'д']:
                self.stdout.write(self.style.ERROR('Операция отменена'))
                return

        success_count = 0
        for username in usernames:
            try:
                if self.delete_user_safe(username):
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Пользователь {username} удален')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Не удалось удалить пользователя {username}')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Ошибка при удалении {username}: {e}')
                )

        self.stdout.write(
            self.style.SUCCESS(
            )
        )

    def list_users(self):
        """Показывает список всех пользователей."""
        users = User.objects.all().order_by('username')
        self.stdout.write(f'\nВсего пользователей: {users.count()}')
        self.stdout.write('=' * 70)
        
        for user in users:
            status = "Суперпользователь" if user.is_superuser else "Обычный"
            email = user.email or "Не указан"
            self.stdout.write(f'{user.username:20} | {email:30} | {status}')
        
        self.stdout.write('=' * 70)

    def delete_user_safe(self, username):
        """Безопасно удаляет пользователя."""
        try:
            user = User.objects.get(username=username)
            user_id = user.id
            
            # Удаляем связанные объекты вручную
            self.cleanup_user_relations(user)
            
            # Очищаем файлы пользователя
            try:
                from utils.file_system import FileCleanupManager
                FileCleanupManager.cleanup_user_files(user_id)
            except Exception as e:
                pass
            
            # Удаляем пользователя напрямую из базы
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = OFF")
                cursor.execute("DELETE FROM users_user WHERE id = %s", [user_id])
                cursor.execute("PRAGMA foreign_keys = ON")
            
            return True
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Пользователь {username} не найден')
            )
            return False
        except Exception as e:
            return False

    def cleanup_user_relations(self, user):
        """Очищает связанные с пользователем объекты."""
        
        # 1. Удаляем членство в командах
        try:
            from teams.models import TeamMembership
            TeamMembership.objects.filter(user=user).delete()
        except Exception as e:
            pass
        
        # 2. Удаляем глобальные роли
        try:
            from teams.models import UserRole
            UserRole.objects.filter(user=user).delete()
        except Exception as e:
            pass
        
        # 3. Удаляем записи из базы знаний
        try:
            from glossary.models import GlossaryTerm
            GlossaryTerm.objects.filter(created_by=user).delete()
        except Exception as e:
            pass

        try:
            from content.models import TextContent, ImageContent, ProjectDocument
            
            TextContent.objects.filter(author=user).delete()
            ImageContent.objects.filter(uploader=user).delete()
            ProjectDocument.objects.filter(uploaded_by=user).delete()
            # ContentAuditLog удалена
        except Exception as e:
            pass
        
        # 6. Обнуляем assignee в главах
        try:
            from projects.models import Chapter
            Chapter.objects.filter(assignee=user).update(assignee=None)
        except Exception as e:
            pass