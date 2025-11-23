from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model


User = get_user_model()


@receiver(post_save, sender=User)
def assign_default_role_to_new_user(sender, instance, created, **kwargs):
    """Назначение дефолтной роли новому пользователю."""
    if created:  # Только для новых пользователей
        try:
            from .models import UserRole
            from .role_manager import DefaultRoleManager
            
            # Получаем дефолтную роль
            default_role = DefaultRoleManager.get_default_user_role()
            
            if default_role:
                # Создаем глобальную роль для пользователя
                user_role, role_created = UserRole.objects.get_or_create(
                    user=instance,
                    role=default_role,
                    defaults={
                        'is_active': True,
                        'assigned_by': None  # Автоматическое назначение системой
                    }
                )
                
                if role_created:
                    pass
                
        except Exception as e:
            pass


@receiver(post_save, sender='teams.UserRole')
def log_user_role_changes(sender, instance, created, **kwargs):
    """Логирование изменений глобальных ролей."""
    if created:
        pass


@receiver(post_save, sender='teams.Team')
def assign_leader_role_to_team_creator(sender, instance, created, **kwargs):
    """Назначение роли Руководитель создателю команды."""
    if created and instance.creator:  # Только для новых команд с создателем
        try:
            from .models import TeamMembership
            from .role_manager import DefaultRoleManager
            
            # Получаем роль "Руководитель"
            leader_role = None
            try:
                from .models import Role
                leader_role = Role.objects.get(name='Руководитель', is_default=True)
            except Role.DoesNotExist:
                # Если роль не найдена, создаем её через DefaultRoleManager
                DefaultRoleManager.ensure_default_roles_exist()
                leader_role = Role.objects.get(name='Руководитель', is_default=True)
            
            if leader_role:
                # Создаем членство в команде для создателя
                membership, membership_created = TeamMembership.objects.get_or_create(
                    user=instance.creator,
                    team=instance,
                    defaults={'is_active': True}
                )
                
                # Назначаем роль "Руководитель"
                membership.roles.add(leader_role)
                
                # Обновляем глобальный статус пользователя если он был новичком
                if hasattr(instance.creator, 'is_default_user') and instance.creator.is_default_user():
                    pass
            else:
                pass
                
        except Exception:
            pass