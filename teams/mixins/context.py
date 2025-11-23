"""Миксины для построения контекста представлений команд."""

from django.db.models import Q, Count, Prefetch

from ..models import Team, TeamMembership, Role, TeamStatus
from ..permission_checker import RolePermissionChecker
from ..query_optimizers import optimize_team_detail_context, optimize_team_list_context



class TeamContextMixin:
    """Миксин для добавления контекста команды в представления."""
    
    def get_team_context(self, team=None):
        if team is None:
            team = self.get_object() if hasattr(self, 'get_object') else None
        
        if not team:
            return {}
        
        user = self.request.user
        
        try:
            # Используем оптимизированную функцию для получения контекста
            context = optimize_team_detail_context(team, user)
            
            # Добавляем дополнительную информацию о статусе команды
            context.update({
                'team_status_display': team.get_status_display(),
                'team_is_active': team.is_active(),
                'can_deactivate': team.status == TeamStatus.ACTIVE,
                'can_reactivate': team.status == TeamStatus.INACTIVE,
                'can_disband': team.status in [TeamStatus.ACTIVE, TeamStatus.INACTIVE],
            })
            
            return context
            
        except Exception as e:
            return {
                'error': 'Ошибка при загрузке данных команды'
            }
    
    def get_permissions_context(self, team=None):
        if team is None:
            team = self.get_object() if hasattr(self, 'get_object') else None
        
        if not team:
            return {}
        
        user = self.request.user
        
        try:
            # Получаем все разрешения пользователя в команде
            user_permissions = RolePermissionChecker.get_user_permissions_in_team(user, team)
            
            # Проверяем конкретные разрешения для отображения элементов интерфейса
            permissions_context = {
                'user_permissions': user_permissions,
                'can_manage_team': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_manage_team'
                ),
                'can_invite_members': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_invite_members'
                ),
                'can_remove_members': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_remove_members'
                ),
                'can_assign_roles': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_assign_roles'
                ),
                'can_change_team_status': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_change_team_status'
                ),
                'can_create_project': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_create_project'
                ),
                'can_manage_project': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_manage_project'
                ),
                'can_delete_project': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_delete_project'
                ),
                'can_edit_content': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_edit_content'
                ),
                'can_review_content': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_review_content'
                ),
                'can_publish_content': RolePermissionChecker.user_has_team_permission(
                    user, team, 'can_publish_content'
                ),
            }
            
            # Добавляем информацию о роли пользователя в команде
            try:
                user_membership = TeamMembership.objects.filter(
                    team=team, 
                    user=user, 
                    is_active=True
                ).prefetch_related('roles').first()
                
                if user_membership:
                    user_roles = list(user_membership.roles.values('id', 'name'))
                    permissions_context['user_roles'] = user_roles
                    permissions_context['user_role_names'] = [role['name'] for role in user_roles]
                else:
                    permissions_context['user_roles'] = []
                    permissions_context['user_role_names'] = []
                    
            except Exception as e:
                permissions_context['user_roles'] = []
                permissions_context['user_role_names'] = []
            
            return permissions_context
            
        except Exception as e:
            return {
                'error': 'Ошибка при загрузке разрешений'
            }
    
    def get_user_teams_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return Team.objects.none()
        
        try:
            return Team.objects.for_user(user).prefetch_related('teammembership_set__user')
        except Exception as e:
            return Team.objects.none()
    
    def get_team_list_context(self):
        user = self.request.user
        
        try:
            # Используем оптимизированную функцию
            context = optimize_team_list_context(user)
            
            # Добавляем дополнительную информацию
            context.update({
                'total_teams': context.get('teams', Team.objects.none()).count(),
                'status_choices': TeamStatus.choices,
            })
            
            return context
            
        except Exception as e:
            return {
                'teams': Team.objects.none(),
                'status_counts': {},
                'error': 'Ошибка при загрузке списка команд'
            }
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Определяем тип представления и добавляем соответствующий контекст
        if hasattr(self, 'object') and isinstance(self.object, Team):
            # Детальное представление команды
            team_context = self.get_team_context(self.object)
            permissions_context = self.get_permissions_context(self.object)
            
            context.update(team_context)
            context.update(permissions_context)
            
        elif hasattr(self, 'model') and self.model == Team:
            # Список команд
            if hasattr(self, 'object_list'):
                list_context = self.get_team_list_context()
                context.update(list_context)
        
        return context


class TeamMemberContextMixin:
    """Миксин для добавления контекста участников команды."""
    
    def get_members_context(self, team):
        try:
            # Получаем участников с оптимизированными запросами
            memberships = TeamMembership.objects.filter(
                team=team,
                is_active=True
            ).select_related('user').prefetch_related('roles').order_by('user__username')
            
            # Формируем данные об участниках
            members_data = []
            for membership in memberships:
                member_user = membership.user
                roles = list(membership.roles.values('id', 'name'))
                
                members_data.append({
                    'user_id': member_user.id,
                    'username': member_user.username,
                    'display_name': getattr(member_user, 'display_name', '') or member_user.username,
                    'email': member_user.email,
                    'avatar_url': member_user.avatar.url if hasattr(member_user, 'avatar') and member_user.avatar else None,
                    'is_creator': member_user == team.creator,
                    'joined_at': membership.joined_at.isoformat() if membership.joined_at else None,
                    'roles': roles,
                    'role_names': [role['name'] for role in roles]
                })
            
            # Получаем доступные роли для назначения
            available_roles = Role.objects.exclude(
                name__in=['Пользователь']  # Исключаем системные роли
            ).order_by('name')
            
            return {
                'members_data': members_data,
                'available_roles': available_roles,
                'total_members': len(members_data),
                'active_members_count': len([m for m in members_data if m['user_id'] != team.creator.id])
            }
            
        except Exception as e:
            return {
                'members_data': [],
                'available_roles': Role.objects.none(),
                'total_members': 0,
                'active_members_count': 0,
                'error': 'Ошибка при загрузке участников'
            }
    
    def get_roles_context(self):
        try:
            # Получаем все роли кроме системных
            roles = Role.objects.exclude(
                name__in=['Пользователь']
            ).prefetch_related('permissions').order_by('name')
            
            # Формируем данные о ролях с разрешениями
            roles_data = []
            for role in roles:
                permissions = list(role.permissions.values('codename', 'name'))
                
                roles_data.append({
                    'id': role.id,
                    'name': role.name,
                    'description': role.description,
                    'permissions': permissions,
                    'permission_count': len(permissions),
                    'usage_count': role.get_usage_count() if hasattr(role, 'get_usage_count') else 0
                })
            
            return {
                'roles_data': roles_data,
                'total_roles': len(roles_data)
            }
            
        except Exception as e:
            return {
                'roles_data': [],
                'total_roles': 0,
                'error': 'Ошибка при загрузке ролей'
            }