"""
Менеджер стандартных ролей для системы управления ролями TranslationHub.

Этот модуль содержит класс DefaultRoleManager, который отвечает за создание
и управление стандартными ролями системы с их предустановленными разрешениями.
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import Role



class DefaultRoleManager:
    # Определение стандартных ролей с их разрешениями
    DEFAULT_ROLES = {
        'Пользователь': {
            'description': 'Базовая роль для всех зарегистрированных пользователей',
            'permissions': []  # Никаких специальных разрешений, только базовые права Django
        },
        'Руководитель': {
            'description': 'Руководитель команды с полными правами управления',
            'permissions': [
                # Разрешения для команд
                'teams.can_manage_team',
                'teams.can_invite_members',
                'teams.can_remove_members',
                'teams.can_assign_roles',
                'teams.can_change_team_status',
                # Разрешения для проектов
                'teams.can_create_project',
                'teams.can_manage_project',
                'teams.can_delete_project',
                'teams.can_assign_chapters',
                # Разрешения для контента
                'teams.can_edit_content',
                'teams.can_review_content',
                'teams.can_publish_content',
            ]
        },
        'Редактор': {
            'description': 'Редактор с правами проверки и адаптации переводов',
            'permissions': [
                # Разрешения для работы с переводами
                'teams.can_edit_content',
                'teams.can_review_content',
            ]
        },
        'Переводчик': {
            'description': 'Переводчик с правами создания и редактирования переводов',
            'permissions': [
                # Разрешения для контента
                'teams.can_edit_content',
            ]
        },
        'Клинер': {
            'description': 'Клинер с правами обработки изображений и очистки',
            'permissions': [
                # Разрешения для контента
                'teams.can_edit_content',
            ]
        },
        'Тайпер': {
            'description': 'Тайпер с правами типографского оформления',
            'permissions': [
                # Разрешения для контента
                'teams.can_edit_content',
            ]
        }
    }
    
    @classmethod
    def ensure_default_roles_exist(cls, user=None):
        """Создание стандартных ролей если не существуют."""
        results = {
            'created': [],
            'updated': [],
            'errors': []
        }
        
        for role_name, role_data in cls.DEFAULT_ROLES.items():
            try:
                with transaction.atomic():
                    role, created = cls.get_or_create_role(
                        name=role_name,
                        description=role_data['description'],
                        permissions=role_data['permissions'],
                        user=user
                    )
                    
                    if created:
                        results['created'].append(role_name)
                    else:
                        # Проверяем и обновляем разрешения для существующей роли
                        updated = cls._update_role_permissions(role, role_data['permissions'])
                        if updated:
                            results['updated'].append(role_name)
                        
            except Exception as e:
                error_msg = f"Ошибка при создании роли {role_name}: {str(e)}"
                results['errors'].append(error_msg)
        
        return results
    
    @classmethod
    def get_or_create_role(cls, name, description, permissions, user=None):
        """Создание или получение роли с разрешениями."""
        try:
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'is_default': True
                }
            )
            
            # Устанавливаем пользователя для аудита
            if user:
                role._audit_user = user
            
            if created:
                # Назначаем разрешения новой роли
                cls._assign_permissions_to_role(role, permissions)
            
            return role, created
            
        except Exception as e:
            raise Exception(f"Не удалось создать роль {name}: {str(e)}")
    
    @classmethod
    def _assign_permissions_to_role(cls, role, permission_codenames):
        """Назначение разрешений роли."""
        permissions_to_add = []
        
        for permission_codename in permission_codenames:
            try:
                # Разбираем полное имя разрешения (app_label.codename)
                if '.' in permission_codename:
                    app_label, codename = permission_codename.split('.', 1)
                else:
                    # Если не указано приложение, предполагаем teams
                    app_label = 'teams'
                    codename = permission_codename
                
                # Ищем разрешение
                permission = Permission.objects.filter(
                    codename=codename,
                    content_type__app_label=app_label
                ).first()
                
                if permission:
                    permissions_to_add.append(permission)
                else:
                    pass

                    pass
            except Exception as e:
                pass
        
        # Добавляем все найденные разрешения
        if permissions_to_add:
            role.permissions.add(*permissions_to_add)
    
    @classmethod
    def _update_role_permissions(cls, role, permission_codenames):
        """Обновление разрешений роли."""
        current_permissions = set(role.get_permission_names())
        expected_permissions = set()
        
        # Получаем ожидаемые разрешения
        for permission_codename in permission_codenames:
            if '.' in permission_codename:
                _, codename = permission_codename.split('.', 1)
            else:
                codename = permission_codename
            expected_permissions.add(codename)
        
        # Проверяем нужно ли обновление
        if current_permissions == expected_permissions:
            return False
        
        # Очищаем текущие разрешения и назначаем новые
        role.permissions.clear()
        cls._assign_permissions_to_role(role, permission_codenames)
        
        return True
    
    @classmethod
    def recreate_role(cls, role_name):
        """Пересоздание стандартной роли."""
        if role_name not in cls.DEFAULT_ROLES:
            raise ValueError(f"Роль {role_name} не является стандартной")
        
        try:
            with transaction.atomic():
                # Удаляем существующую роль если она есть
                Role.objects.filter(name=role_name).delete()
                
                # Создаем роль заново
                role_data = cls.DEFAULT_ROLES[role_name]
                role, _ = cls.get_or_create_role(
                    name=role_name,
                    description=role_data['description'],
                    permissions=role_data['permissions']
                )
                return role
                
        except Exception as e:
            raise Exception(f"Не удалось пересоздать роль {role_name}: {str(e)}")
    
    @classmethod
    def get_default_role_names(cls):
        """Список названий стандартных ролей."""
        return list(cls.DEFAULT_ROLES.keys())
    
    @classmethod
    def is_default_role(cls, role_name):
        """Проверка стандартной роли."""
        return role_name in cls.DEFAULT_ROLES
    
    @classmethod
    def get_role_permissions(cls, role_name):
        """Список разрешений для стандартной роли."""
        return cls.DEFAULT_ROLES.get(role_name, {}).get('permissions')
    
    @classmethod
    def get_default_user_role(cls):
        """Дефолтная роль для новых пользователей."""
        try:
            return Role.objects.get(name='Пользователь', is_default=True)
        except Role.DoesNotExist:
            return None
    
    @classmethod
    def assign_default_role_to_user(cls, user):
        """Назначение дефолтной роли пользователю."""
        try:
            default_role = cls.get_default_user_role()
            if not default_role:
                return False
            
            # Создаем запись о том, что пользователь имеет базовую роль
            # Это не привязано к конкретной команде, а является глобальным статусом
            from .models import UserRole
            user_role, created = UserRole.objects.get_or_create(
                user=user,
                role=default_role,
                defaults={'is_active': True}
            )
            
            return True
            
        except Exception:
            return False