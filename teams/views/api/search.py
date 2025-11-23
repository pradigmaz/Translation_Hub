"""
AJAX API для поиска пользователей и команд.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q

from ...components import TeamMemberManager
from .base import SearchAPIBase, handle_api_errors

User = get_user_model()


class TeamMemberSearchAPI(SearchAPIBase):
    """API для поиска пользователей для добавления в команду."""
    
    team_permission_required = 'can_invite_members'
    
    @handle_api_errors('TeamMemberSearchAPI.get')
    def get(self, request, team_id):
        """Выполнить поиск пользователей для добавления в команду."""
        team = self.get_team_or_404(team_id)
        query, limit = self.get_search_params(request)
        
        member_manager = TeamMemberManager(team, request.user)
        search_results = member_manager.search_potential_members(query, limit)
        
        return self.ajax_success(
            data={
                'users': search_results,
                'query': query,
                'total_found': len(search_results),
                'limit': limit,
                'team_id': team.id,
                'team_name': team.name
            },
            message=f'Найдено {len(search_results)} пользователей'
        )


class GlobalUserSearchAPI(SearchAPIBase):
    """API для глобального поиска пользователей."""
    
    team_permission_required = None
    
    @handle_api_errors('GlobalUserSearchAPI.get')
    def get(self, request):
        """Выполнить глобальный поиск пользователей."""
        if not request.user.is_authenticated:
            return self.ajax_error(message="Необходима аутентификация", status=401)
        
        query, limit = self.get_search_params(request)
        
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(display_name__icontains=query)
        ).exclude(id=request.user.id).select_related().order_by('username')[:limit]
        
        results = [
            {
                'id': user.id,
                'username': user.username,
                'display_name': getattr(user, 'display_name', '') or user.username,
                'email': user.email,
                'is_active': user.is_active
            }
            for user in users
        ]
        
        return self.ajax_success(
            data={'users': results, 'query': query, 'total_found': len(results), 'limit': limit},
            message=f'Найдено {len(results)} пользователей'
        )


class TeamSearchAPI(SearchAPIBase):
    """API для поиска команд."""
    
    team_permission_required = None
    
    @handle_api_errors('TeamSearchAPI.get')
    def get(self, request):
        """Выполнить поиск команд."""
        if not request.user.is_authenticated:
            return self.ajax_error(message="Необходима аутентификация", status=401)
        
        query, limit = self.get_search_params(request)
        
        from ...models import Team
        teams = Team.objects.for_user(request.user).filter(
            name__icontains=query
        ).order_by('name')[:limit]
        
        results = [
            {
                'id': team.id,
                'name': team.name,
                'status': team.status,
                'is_creator': team.creator == request.user
            }
            for team in teams
        ]
        
        return self.ajax_success(
            data={'teams': results, 'query': query, 'total_found': len(results), 'limit': limit},
            message=f'Найдено {len(results)} команд'
        )


class QuickSearchAPI(SearchAPIBase):
    """API для быстрого поиска по пользователям и командам."""
    
    team_permission_required = None
    max_limit = 5
    
    @handle_api_errors('QuickSearchAPI.get')
    def get(self, request):
        """Выполнить быстрый поиск."""
        if not request.user.is_authenticated:
            return self.ajax_error(message="Необходима аутентификация", status=401)
        
        query, _ = self.get_search_params(request)
        search_type = request.GET.get('type', 'all')
        
        results = {'query': query, 'users': [], 'teams': []}
        
        if search_type in ['users', 'all']:
            users = User.objects.filter(
                Q(username__icontains=query) | Q(display_name__icontains=query)
            ).exclude(id=request.user.id)[:5]
            results['users'] = [
                {'id': u.id, 'username': u.username, 'display_name': getattr(u, 'display_name', '') or u.username}
                for u in users
            ]
        
        if search_type in ['teams', 'all']:
            from ...models import Team
            teams = Team.objects.for_user(request.user).filter(name__icontains=query)[:5]
            results['teams'] = [
                {'id': t.id, 'name': t.name, 'status': t.status, 'is_creator': t.creator == request.user}
                for t in teams
            ]
        
        total = len(results['users']) + len(results['teams'])
        return self.ajax_success(data=results, message=f'Найдено {total} результатов')
