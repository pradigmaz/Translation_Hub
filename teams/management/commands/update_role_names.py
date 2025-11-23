"""
Management command для обновления названий ролей с английского на русский.

Использование:
    python manage.py update_role_names
"""

from django.core.management.base import BaseCommand
from teams.models import Role


class Command(BaseCommand):
    help = 'Обновляет названия ролей с английского на русский'

    # Маппинг старых названий на новые
    ROLE_MAPPING = {
        'Leader': 'Руководитель',
        'Editor': 'Редактор',
        'Translator': 'Переводчик',
        'Cleaner': 'Клинер',
        'Typesetter': 'Тайпер',
        'User': 'Пользователь',
    }

    def handle(self, *args, **options):
        """Выполнение команды обновления названий ролей."""
        self.stdout.write('Начинаем обновление названий ролей...')
        
        deleted_count = 0
        not_found_count = 0
        
        for old_name, new_name in self.ROLE_MAPPING.items():
            try:
                old_role = Role.objects.get(name=old_name)
                
                # Проверяем, существует ли уже роль с новым названием
                try:
                    new_role = Role.objects.get(name=new_name)
                    # Если существует, переносим связи и удаляем старую
                    self.stdout.write(f'Роль "{new_name}" уже существует. Переносим связи...')
                    
                    # Переносим участников команд со старой роли на новую
                    from teams.models import TeamMembership
                    memberships_with_old_role = TeamMembership.objects.filter(roles=old_role)
                    for membership in memberships_with_old_role:
                        membership.roles.remove(old_role)
                        membership.roles.add(new_role)
                    
                    # Удаляем старую роль
                    old_role.delete()
                    deleted_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Роль "{old_name}" удалена, связи перенесены на "{new_name}"')
                    )
                    
                except Role.DoesNotExist:
                    # Если новой роли нет, просто переименовываем
                    old_role.name = new_name
                    old_role.save()
                    deleted_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Роль "{old_name}" переименована в "{new_name}"')
                    )
                    
            except Role.DoesNotExist:
                not_found_count += 1
                self.stdout.write(
                    self.style.WARNING(f'⚠ Роль "{old_name}" не найдена (возможно уже обновлена)')
                )
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Обработано ролей: {deleted_count}')
        self.stdout.write(f'Не найдено: {not_found_count}')
        self.stdout.write('='*50)
        
        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS('\n✓ Обновление завершено успешно!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\n⚠ Нет ролей для обновления')
            )
