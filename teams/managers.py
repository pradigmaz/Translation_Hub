"""
Менеджеры моделей для оптимизации запросов в приложении teams.
"""

from django.db import models
from django.db.models import Prefetch, Count, Q


class TeamQuerySet(models.QuerySet):
    """Оптимизированные запросы для модели Team"""
    
    def with_members(self):
        """Предзагружает участников команды"""
        return self.prefetch_related(
            Prefetch(
                'teammembership_set',
                queryset=models.get_model('teams', 'TeamMembership').objects
                .select_related('user')
                .prefetch_related('roles')
                .filter(is_active=True)
            )
        )
    
    def with_projects(self):
        """Предзагружает проекты команды"""
        return self.prefetch_related('projects')
    
    def with_creator(self):
        """Предзагружает создателя команды"""
        return self.select_related('creator')
    
    def with_status_history(self):
        """Предзагружает историю статусов"""
        return self.prefetch_related(
            Prefetch(
                'status_history',
                queryset=models.get_model('teams', 'TeamStatusHistory').objects
                .select_related('changed_by')
                .order_by('-timestamp')
            )
        )
    
    def for_user(self, user):
        """
        Возвращает команды пользователя (создатель или активный участник).
        Оптимизирован для предотвращения N+1 запросов.
        """
        return self.filter(
            Q(creator=user) | 
            Q(teammembership__user=user, teammembership__is_active=True)
        ).select_related('creator').distinct()
    
    def active(self):
        """Возвращает только активные команды"""
        return self.filter(status='active')
    
    def with_stats(self):
        """Добавляет статистику к командам"""
        return self.annotate(
            member_count=Count('members', distinct=True),
            project_count=Count('projects', distinct=True)
        )


class TeamManager(models.Manager):
    """Менеджер для модели Team"""
    
    def get_queryset(self):
        return TeamQuerySet(self.model, using=self._db)
    
    def with_members(self):
        return self.get_queryset().with_members()
    
    def with_projects(self):
        return self.get_queryset().with_projects()
    
    def with_creator(self):
        return self.get_queryset().with_creator()
    
    def with_status_history(self):
        return self.get_queryset().with_status_history()
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def active(self):
        return self.get_queryset().active()
    
    def with_stats(self):
        return self.get_queryset().with_stats()
    
    def user_teams_with_full_data(self, user):
        """Получает команды пользователя со всеми связанными данными"""
        return self.get_queryset()\
            .for_user(user)\
            .with_creator()\
            .with_members()\
            .with_projects()\
            .with_stats()


class TeamMembershipQuerySet(models.QuerySet):
    """Оптимизированные запросы для модели TeamMembership"""
    
    def with_user_and_roles(self):
        """Предзагружает пользователя и роли"""
        return self.select_related('user').prefetch_related('roles')
    
    def active(self):
        """Возвращает только активных участников"""
        return self.filter(is_active=True)
    
    def for_team(self, team):
        """Возвращает участников конкретной команды"""
        return self.filter(team=team)
    
    def with_role(self, role_name):
        """Возвращает участников с определенной ролью"""
        return self.filter(roles__name=role_name)


class TeamMembershipManager(models.Manager):
    """Менеджер для модели TeamMembership"""
    
    def get_queryset(self):
        return TeamMembershipQuerySet(self.model, using=self._db)
    
    def with_user_and_roles(self):
        return self.get_queryset().with_user_and_roles()
    
    def active(self):
        return self.get_queryset().active()
    
    def for_team(self, team):
        return self.get_queryset().for_team(team)
    
    def with_role(self, role_name):
        return self.get_queryset().with_role(role_name)
    
    def team_members_optimized(self, team):
        """Получает участников команды с оптимизированными запросами"""
        return self.get_queryset()\
            .for_team(team)\
            .active()\
            .with_user_and_roles()\
            .order_by('user__username')


class RoleQuerySet(models.QuerySet):
    """Оптимизированные запросы для модели Role"""
    
    def with_permissions(self):
        """Предзагружает разрешения роли"""
        return self.prefetch_related('permissions')
    
    def with_usage_stats(self):
        """Добавляет статистику использования ролей"""
        return self.annotate(
            usage_count=Count('teammembership', distinct=True),
            active_usage_count=Count(
                'teammembership',
                filter=Q(teammembership__is_active=True),
                distinct=True
            )
        )
    
    def default_roles(self):
        """Возвращает стандартные роли"""
        return self.filter(is_default=True)
    
    def custom_roles(self):
        """Возвращает пользовательские роли"""
        return self.filter(is_default=False)


class RoleManager(models.Manager):
    """Менеджер для модели Role"""
    
    def get_queryset(self):
        return RoleQuerySet(self.model, using=self._db)
    
    def with_permissions(self):
        return self.get_queryset().with_permissions()
    
    def with_usage_stats(self):
        return self.get_queryset().with_usage_stats()
    
    def default_roles(self):
        return self.get_queryset().default_roles()
    
    def custom_roles(self):
        return self.get_queryset().custom_roles()
    
    def roles_with_full_data(self):
        """Получает роли со всеми связанными данными"""
        return self.get_queryset()\
            .with_permissions()\
            .with_usage_stats()\
            .order_by('name')


class TeamStatusHistoryQuerySet(models.QuerySet):
    """Оптимизированные запросы для модели TeamStatusHistory"""
    
    def with_changed_by(self):
        """Предзагружает пользователя, изменившего статус"""
        return self.select_related('changed_by')
    
    def for_team(self, team):
        """Возвращает историю для конкретной команды"""
        return self.filter(team=team)
    
    def recent(self, limit=10):
        """Возвращает последние изменения"""
        return self.order_by('-timestamp')[:limit]


class TeamStatusHistoryManager(models.Manager):
    """Менеджер для модели TeamStatusHistory"""
    
    def get_queryset(self):
        return TeamStatusHistoryQuerySet(self.model, using=self._db)
    
    def with_changed_by(self):
        return self.get_queryset().with_changed_by()
    
    def for_team(self, team):
        return self.get_queryset().for_team(team)
    
    def recent(self, limit=10):
        return self.get_queryset().recent(limit)
    
    def team_history_optimized(self, team, limit=50):
        """Получает историю команды с оптимизированными запросами"""
        return self.get_queryset()\
            .for_team(team)\
            .with_changed_by()\
            .order_by('-timestamp')[:limit]