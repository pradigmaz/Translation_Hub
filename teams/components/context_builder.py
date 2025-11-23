"""Построение контекста для представлений команд."""

from django.db.models import Count, Q, Prefetch

from ..models import Team, TeamMembership, Role, TeamStatus
from ..permission_checker import RolePermissionChecker
from ..query_optimizers import optimize_team_detail_context, optimize_team_list_context



class TeamContextBuilder:
    """Построение оптимизированного контекста для страниц команд."""
    
    def __init__(self, team, user):
        """Инициализация построителя контекста."""
        if not user:
            raise ValueError("User is required")
        
        self.team = team
        self.user = user
    
    def build_detail_context(self):
        """Контекст для детальной страницы команды."""
        try:
            # Используем существующую оптимизированную функцию как базу
            base_context = optimize_team_detail_context(self.team, self.user)
            
            # Получаем permissions и добавляем их на верхний уровень контекста
            permissions_context = self._build_permissions_context()
            
            # Расширяем контекст дополнительной информацией
            extended_context = {
                **base_context,
                **permissions_context,  # Распаковываем permissions на верхний уровень
                'permissions': permissions_context,  # Оставляем также в permissions для совместимости
                'team_stats': self._build_team_stats(),
                'status_info': self._build_status_info(),
                'member_management': self._build_member_management_context(),
                'project_summary': self._build_project_summary()
            }
            return extended_context
            
        except Exception as e:
            return {
                'error': 'Ошибка при построении контекста команды'
            }
    
    def build_list_context(self):
        """Контекст для списка команд."""
        try:
            # Используем существующую оптимизированную функцию как базу
            base_context = optimize_team_list_context(self.user)
            
            # Расширяем контекст дополнительной информацией
            extended_context = {
                **base_context,
                'user_stats': self._build_user_stats(),
                'filter_options': self._build_filter_options(),
                'create_permissions': self._build_create_permissions()
            }
            return extended_context
            
        except Exception as e:
            return {
                'teams': Team.objects.none(),
                'status_counts': {},
                'error': 'Ошибка при построении списка команд'
            }
    
    def build_permissions_context(self):
        """Контекст разрешений для команды."""
        try:
            return self._build_permissions_context()
        except Exception as e:
            return {
                'error': 'Ошибка при построении контекста разрешений'
            }
    
    def _build_permissions_context(self):
        """Детальный контекст разрешений."""
        # Получаем все разрешения пользователя в команде
        user_permissions = RolePermissionChecker.get_user_permissions_in_team(self.user, self.team)
        
        # Проверяем конкретные разрешения
        permissions = {
            'user_permissions': user_permissions,
            'can_manage_team': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_manage_team'
            ),
            'can_invite_members': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_invite_members'
            ),
            'can_remove_members': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_remove_members'
            ),
            'can_assign_roles': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_assign_roles'
            ),
            'can_change_team_status': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_change_team_status'
            ),
            'can_create_project': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_create_project'
            ),
            'can_manage_project': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_manage_project'
            ),
            'can_delete_project': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_delete_project'
            ),
            'can_edit_content': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_edit_content'
            ),
            'can_review_content': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_review_content'
            ),
            'can_publish_content': RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_publish_content'
            ),
        }
        
        # Добавляем информацию о роли пользователя
        try:
            user_membership = TeamMembership.objects.filter(
                team=self.team,
                user=self.user,
                is_active=True
            ).prefetch_related('roles').first()
            
            if user_membership:
                user_roles = list(user_membership.roles.values('id', 'name'))
                permissions.update({
                    'user_roles': user_roles,
                    'user_role_names': [role['name'] for role in user_roles],
                    'is_team_member': True
                })
            else:
                permissions.update({
                    'user_roles': [],
                    'user_role_names': [],
                    'is_team_member': False
                })
                
        except Exception as e:
            permissions.update({
                'user_roles': [],
                'user_role_names': [],
                'is_team_member': False
            })
        
        # Добавляем информацию о создателе команды
        permissions['is_creator'] = self.team.creator == self.user
        permissions['is_superuser'] = self.user.is_superuser
        
        # Добавляем возможность покинуть команду
        permissions['can_leave_team'] = (
            permissions['is_team_member'] and  # Активный участник команды
            not permissions['is_creator'] and  # Не создатель команды
            self.team.status != TeamStatus.DISBANDED  # Команда не распущена
        )
        
        return permissions
    
    def _build_team_stats(self):
        """Статистика команды."""
        try:
            # Получаем статистику одним запросом
            from projects.models import Project
            
            # Комбинированная статистика участников и проектов
            team_stats = {
                'total_members': TeamMembership.objects.filter(team=self.team, is_active=True).count(),
                'projects': Project.objects.filter(team=self.team).aggregate(
                    total_projects=Count('id'),
                    active_projects=Count('id', filter=Q(status='translating')),
                    completed_projects=Count('id', filter=Q(status='completed'))
                )
            }
            
            # Оптимизированная статистика ролей одним запросом
            role_distribution = TeamMembership.objects.filter(
                team=self.team,
                is_active=True
            ).values('roles__name').annotate(
                count=Count('roles__name')
            ).exclude(roles__name__isnull=True).order_by('-count')
            
            team_stats['role_distribution'] = list(role_distribution)
            team_stats['team_age_days'] = 0  # Упрощаем вычисление возраста команды
            
            return team_stats
            
        except Exception as e:
            return {}
    
    def _build_status_info(self):
        """Информация о статусе команды."""
        try:
            status_display = dict(TeamStatus.choices)
            
            return {
                'current_status': self.team.status,
                'current_status_display': status_display.get(self.team.status, self.team.status),
                'is_active': self.team.is_active(),
                'can_be_reactivated': self.team.can_be_reactivated(),
                'can_be_disbanded': self.team.can_be_disbanded(),
                'created_at': self.team.created_at.isoformat() if self.team.created_at else None,
                'updated_at': self.team.updated_at.isoformat() if self.team.updated_at else None
            }
            
        except Exception as e:
            return {}
    
    def _build_member_management_context(self):
        """Контекст управления участниками."""
        try:
            # Получаем доступные роли для назначения одним запросом с аннотацией
            available_roles = Role.objects.exclude(
                name__in=['Пользователь']  # Исключаем системные роли
            ).annotate(
                permission_count=Count('permissions')
            ).only('id', 'name', 'description').order_by('name')
            
            # Формируем данные о ролях без дополнительных запросов
            roles_data = [
                {
                    'id': role.id,
                    'name': role.name,
                    'description': role.description,
                    'permission_count': role.permission_count
                }
                for role in available_roles
            ]
            
            return {
                'available_roles': roles_data,
                'can_invite': RolePermissionChecker.user_has_team_permission(
                    self.user, self.team, 'can_invite_members'
                ),
                'can_remove': RolePermissionChecker.user_has_team_permission(
                    self.user, self.team, 'can_remove_members'
                ),
                'can_assign_roles': RolePermissionChecker.user_has_team_permission(
                    self.user, self.team, 'can_assign_roles'
                )
            }
            
        except Exception as e:
            return {}
    
    def _build_project_summary(self):
        """Краткая сводка по проектам."""
        try:
            from projects.models import Project
            
            # Получаем последние проекты только с нужными полями
            recent_projects = Project.objects.filter(team=self.team).only(
                'id', 'title', 'status', 'created_at'
            ).order_by('-created_at')[:5]
            
            # Формируем данные без дополнительных запросов
            projects_data = [
                {
                    'id': project.id,
                    'name': project.title,
                    'status': project.status,
                    'status_display': project.get_status_display() if hasattr(project, 'get_status_display') else project.status,
                    'created_at': project.created_at.isoformat() if project.created_at else None
                }
                for project in recent_projects
            ]
            
            return {
                'recent_projects': projects_data,
                'can_create_project': RolePermissionChecker.user_has_team_permission(
                    self.user, self.team, 'can_create_project'
                ),
                'can_manage_projects': RolePermissionChecker.user_has_team_permission(
                    self.user, self.team, 'can_manage_project'
                )
            }
            
        except Exception as e:
            return {}
    
    def _build_user_stats(self):
        """Статистика пользователя."""
        try:
            # Статистика участия в командах - получаем команды где пользователь создатель или участник
            user_teams = Team.objects.filter(
                Q(creator=self.user) | Q(teammembership__user=self.user, teammembership__is_active=True)
            ).distinct()
            
            team_stats = {
                'total_teams': user_teams.count(),
                'active_teams': user_teams.filter(status=TeamStatus.ACTIVE).count(),
                'created_teams': Team.objects.filter(creator=self.user).count()
            }
            
            # Статистика ролей
            user_memberships = TeamMembership.objects.filter(
                user=self.user,
                is_active=True
            ).prefetch_related('roles')
            
            all_roles = set()
            for membership in user_memberships:
                all_roles.update(membership.roles.values_list('name', flat=True))
            
            return {
                'teams': team_stats,
                'roles': list(all_roles),
                'total_roles': len(all_roles)
            }
            
        except Exception as e:
            return {}
    
    def _build_filter_options(self):
        """Опции фильтрации для списка команд."""
        try:
            return {
                'status_choices': TeamStatus.choices,
                'available_statuses': [
                    {'value': status[0], 'label': status[1]} 
                    for status in TeamStatus.choices
                ]
            }
            
        except Exception as e:
            return {}
    
    def _build_create_permissions(self):
        """Разрешения на создание."""
        try:
            return {
                'can_create_team': self.user.is_authenticated,  # Любой аутентифицированный пользователь может создать команду
                'is_authenticated': self.user.is_authenticated
            }
            
        except Exception as e:
            return {}
    
    @classmethod
    def build_list_context_for_user(cls, user):
        """Контекст списка команд для пользователя."""
        builder = cls(None, user)  # team не нужна для списка
        return builder.build_list_context()