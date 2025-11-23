"""
Миксины для расширения функциональности пользователя в системе ролей.

Этот модуль содержит миксины, которые можно использовать для расширения
модели User дополнительными методами работы с ролями.
"""

from django.db import models

class UserRoleMixin:

    def get_global_roles(self, active_only=True):
        """Глобальные роли пользователя."""
        from .models import UserRole
        
        user_roles = UserRole.objects.filter(user=self)
        if active_only:
            user_roles = user_roles.filter(is_active=True)
        
        return user_roles.select_related('role')
    
    def has_global_role(self, role_name):
        """Проверка наличия глобальной роли."""
        return self.get_global_roles().filter(role__name=role_name).exists()
    
    def is_default_user(self):
        """Проверка дефолтной роли пользователя."""
        global_roles = self.get_global_roles()
        return (global_roles.count() == 1 and 
                global_roles.filter(role__name='Пользователь').exists())
    
    def get_all_permissions_from_roles(self):
        """Все разрешения из глобальных ролей."""
        from django.contrib.auth.models import Permission
        
        role_ids = self.get_global_roles().values_list('role_id', flat=True)
        return Permission.objects.filter(roles__id__in=role_ids).distinct()
    
    def add_global_role(self, role_name, assigned_by=None):
        """Добавление глобальной роли."""
        from .models import Role, UserRole
        
        try:
            role = Role.objects.get(name=role_name)
            user_role, created = UserRole.objects.get_or_create(
                user=self,
                role=role,
                defaults={
                    'is_active': True,
                    'assigned_by': assigned_by
                }
            )
            
            if not created and not user_role.is_active:
                # Реактивируем роль если она была деактивирована
                user_role.reactivate(assigned_by)
            
            return user_role, created
            
        except Role.DoesNotExist:
            raise ValueError(f"Роль '{role_name}' не найдена")
    
    def remove_global_role(self, role_name, removed_by=None):
        """Удаление глобальной роли."""
        from .models import UserRole
        
        try:
            user_role = UserRole.objects.get(
                user=self,
                role__name=role_name,
                is_active=True
            )
            user_role.deactivate(removed_by)
            return True
            
        except UserRole.DoesNotExist:
            return False
    
    def get_role_summary(self):
        """Сводка о ролях пользователя."""
        global_roles = self.get_global_roles()
        team_memberships = getattr(self, 'teammembership_set', None)
        
        summary = {
            'global_roles': [ur.role.name for ur in global_roles],
            'global_roles_count': global_roles.count(),
            'is_default_user': self.is_default_user(),
            'team_memberships': []
        }
        
        if team_memberships:
            for membership in team_memberships.filter(is_active=True).select_related('team'):
                team_roles = [role.name for role in membership.roles.all()]
                summary['team_memberships'].append({
                    'team': membership.team.name,
                    'roles': team_roles
                })
        
        return summary


def add_role_methods_to_user():
    """Добавление методов работы с ролями к модели User."""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Добавляем методы из миксина к модели User
    for method_name in dir(UserRoleMixin):
        if not method_name.startswith('_'):
            method = getattr(UserRoleMixin, method_name)
            if callable(method):
                setattr(User, method_name, method)