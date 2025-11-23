"""Проверка разрешений пользователей в командах на основе ролей."""

from django.db.models import Q



class RolePermissionChecker:
    """Проверка разрешений пользователей в командах."""
    
    @staticmethod
    def user_has_team_permission(user, team, permission):
        """Проверка наличия разрешения у пользователя в команде."""
        if not user or not user.is_authenticated or not team:
            return False
        
        if user.is_superuser or team.creator == user:
            return True
        
        try:
            from .models import TeamMembership
            
            membership = TeamMembership.objects.filter(
                user=user, team=team, is_active=True
            ).prefetch_related('roles__permissions').first()
            
            if not membership:
                return False
            
            return any(role.has_permission(permission) for role in membership.roles.all())
            
        except Exception as e:
            return False
    
    @staticmethod
    def get_user_permissions_in_team(user, team):
        """Получить все разрешения пользователя в команде."""
        if not user or not user.is_authenticated or not team:
            return set()
        
        if user.is_superuser or team.creator == user:
            return RolePermissionChecker._get_all_team_permissions()
        
        try:
            from .models import TeamMembership
            
            membership = TeamMembership.objects.filter(
                user=user, team=team, is_active=True
            ).prefetch_related('roles__permissions').first()
            
            if not membership:
                return set()
            
            permissions = set()
            for role in membership.roles.all():
                permissions.update(role.get_permission_names())
            return permissions
            
        except Exception as e:
            return set()
    
    @staticmethod
    def filter_teams_by_permission(user, permission):
        """Фильтр команд где у пользователя есть указанное разрешение."""
        if not user or not user.is_authenticated:
            from .models import Team
            return Team.objects.none()
        
        if user.is_superuser:
            from .models import Team
            return Team.objects.all()
        
        try:
            from .models import Team
            
            creator_teams = Team.objects.filter(creator=user)
            permission_teams = Team.objects.filter(
                teammembership__user=user,
                teammembership__is_active=True,
                teammembership__roles__permissions__codename=permission
            ).distinct()
            
            return creator_teams.union(permission_teams)
            
        except Exception as e:
            from .models import Team
            return Team.objects.none()
    
    @staticmethod
    def user_has_any_team_permission(user, team, permissions):
        """Проверка наличия хотя бы одного из указанных разрешений."""
        if not permissions:
            return False
        
        for permission in permissions:
            if RolePermissionChecker.user_has_team_permission(user, team, permission):
                return True
        
        return False
    
    @staticmethod
    def user_has_all_team_permissions(user, team, permissions):
        """Проверка наличия всех указанных разрешений."""
        if not permissions:
            return True
        
        for permission in permissions:
            if not RolePermissionChecker.user_has_team_permission(user, team, permission):
                return False
        
        return True
    
    @staticmethod
    def get_user_teams_with_permission(user, permission):
        """Список команд где у пользователя есть указанное разрешение."""
        teams_queryset = RolePermissionChecker.filter_teams_by_permission(user, permission)
        return list(teams_queryset)
    
    @staticmethod
    def get_team_members_with_permission(team, permission):
        """Список участников команды с указанным разрешением."""
        if not team:
            return []
        
        try:
            from .models import TeamMembership
            
            # Получаем всех активных участников команды
            memberships = TeamMembership.objects.filter(
                team=team,
                is_active=True
            ).select_related('user').prefetch_related('roles__permissions')
            
            members_with_permission = []
            
            for membership in memberships:
                user = membership.user
                
                # Проверяем разрешение для каждого участника
                if RolePermissionChecker.user_has_team_permission(user, team, permission):
                    members_with_permission.append(user)
            
            return members_with_permission
            
        except Exception as e:
            return []
    
    @staticmethod
    def _get_all_team_permissions():
        """Все доступные разрешения для команд."""
        try:
            # Получаем все разрешения из мета-класса Role
            from .models import Role
            meta_permissions = [perm[0] for perm in Role._meta.permissions]
            return set(meta_permissions)
            
        except Exception as e:
            return set()
    
    @staticmethod
    def check_permission_exists(permission):
        """Проверка существования разрешения в системе."""
        try:
            from django.contrib.auth.models import Permission
            
            return Permission.objects.filter(
                codename=permission,
                content_type__app_label='teams'
            ).exists()
            
        except Exception as e:
            return False