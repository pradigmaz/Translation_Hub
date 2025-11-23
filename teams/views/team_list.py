"""
Представления для отображения списков команд.

Этот модуль содержит представления для отображения различных списков команд
с фильтрацией, сортировкой и оптимизированными запросами.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q

from ..models import Team, TeamStatus
from ..mixins import TeamContextMixin, PerformanceMonitoringMixin
from ..components import TeamContextBuilder



class TeamFilterMixin:
    """
    Mixin для общей логики фильтрации команд.
    
    Централизует повторяющуюся логику фильтрации по статусу,
    поиску и сортировке, используемую в нескольких представлениях.
    """
    
    def apply_team_filters(self, queryset):
        """
        Применить фильтры статуса, поиска и сортировки к queryset.
        
        Args:
            queryset: Базовый QuerySet команд для фильтрации
            
        Returns:
            QuerySet: Отфильтрованный и отсортированный queryset
        """
        # Фильтр по статусу
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter in [choice[0] for choice in TeamStatus.choices]:
            queryset = queryset.filter(status=status_filter)
        
        # Фильтр поиска по названию
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        
        # Сортировка с валидацией
        sort_by = self.request.GET.get('sort', '-updated_at')
        valid_sort_fields = [
            'name', '-name',
            'created_at', '-created_at',
            'updated_at', '-updated_at',
            'status', '-status'
        ]
        
        if sort_by in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-updated_at')
        
        return queryset


class TeamListView(LoginRequiredMixin, PerformanceMonitoringMixin, TeamContextMixin, ListView):
    """Список команд пользователя с фильтрацией (статус, поиск) и сортировкой."""
    
    model = Team
    template_name = "teams/team_list.html"
    context_object_name = "teams"
    paginate_by = 20
    
    def get_queryset(self):
        """Фильтрация по участию, статусу, поиску. Сортировка (whitelist)."""
        try:
            # Получаем базовый QuerySet команд пользователя
            queryset = self.get_user_teams_queryset()
            
            # Фильтрация по статусу
            status_filter = self.request.GET.get('status')
            if status_filter and status_filter in [choice[0] for choice in TeamStatus.choices]:
                queryset = queryset.filter(status=status_filter)
                
            # Поиск по названию команды
            search_query = self.request.GET.get('search', '').strip()
            if search_query:
                queryset = queryset.filter(
                    Q(name__icontains=search_query)
                )
            
            # Сортировка
            sort_by = self.request.GET.get('sort', '-updated_at')
            valid_sort_fields = [
                'name', '-name',
                'created_at', '-created_at',
                'updated_at', '-updated_at',
                'status', '-status'
            ]
            
            if sort_by in valid_sort_fields:
                queryset = queryset.order_by(sort_by)
            else:
                queryset = queryset.order_by('-updated_at')
            
            return queryset
            
        except Exception as e:
            return Team.objects.none()
    
    def get_context_data(self, **kwargs):
        """Контекст через TeamContextBuilder.build_list_context_for_user()."""
        context = super().get_context_data(**kwargs)
        
        try:
            # Используем TeamContextBuilder для построения контекста списка
            list_context = TeamContextBuilder.build_list_context_for_user(self.request.user)
            context.update(list_context)
            
            # Добавляем информацию о текущих фильтрах
            context.update({
                'current_status_filter': self.request.GET.get('status', ''),
                'current_search': self.request.GET.get('search', ''),
                'current_sort': self.request.GET.get('sort', '-updated_at'),
                'sort_options': [
                    {'value': 'name', 'label': 'Название (А-Я)'},
                    {'value': '-name', 'label': 'Название (Я-А)'},
                    {'value': '-created_at', 'label': 'Дата создания (новые)'},
                    {'value': 'created_at', 'label': 'Дата создания (старые)'},
                    {'value': '-updated_at', 'label': 'Последнее обновление (новые)'},
                    {'value': 'updated_at', 'label': 'Последнее обновление (старые)'},
                    {'value': 'status', 'label': 'Статус'},
                ]
            })
            
            # Добавляем информацию о пагинации
            if context.get('is_paginated'):
                context.update({
                    'pagination_info': {
                        'current_page': context['page_obj'].number,
                        'total_pages': context['paginator'].num_pages,
                        'total_items': context['paginator'].count,
                        'items_per_page': self.paginate_by
                    }
                })
            
        except Exception as e:
            context['error'] = 'Ошибка при загрузке списка команд'
        
        return context


class TeamSearchView(LoginRequiredMixin, PerformanceMonitoringMixin, ListView):
    """Расширенный поиск команд с фильтрами (статус, даты) и сортировкой по релевантности."""
    
    model = Team
    template_name = "teams/team_search.html"
    context_object_name = "teams"
    paginate_by = 10
    
    def get_queryset(self):
        """Поиск по name/creator (username/email), фильтры (статус, даты). Сортировка по релевантности."""
        try:
            # Базовый QuerySet команд пользователя с оптимизацией
            queryset = Team.objects.filter(
                Q(creator=self.request.user) |
                Q(teammembership__user=self.request.user, teammembership__is_active=True)
            ).select_related(
                'creator'
            ).prefetch_related(
                'teammembership_set__user'
            ).distinct()
            
            # Расширенный поиск
            query = self.request.GET.get('q', '').strip()
            if query:
                queryset = queryset.filter(
                    Q(name__icontains=query) |
                    Q(creator__username__icontains=query) |
                    Q(creator__email__icontains=query)
                )
            
            # Дополнительные фильтры
            status_filter = self.request.GET.get('status')
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            created_from = self.request.GET.get('created_from')
            if created_from:
                queryset = queryset.filter(created_at__gte=created_from)
            
            created_to = self.request.GET.get('created_to')
            if created_to:
                queryset = queryset.filter(created_at__lte=created_to)
            
            # Сортировка по релевантности (если есть поисковый запрос)
            if query:
                # Простая сортировка по релевантности: сначала точные совпадения в названии
                queryset = queryset.extra(
                    select={
                        'name_exact': "CASE WHEN LOWER(name) = LOWER(%s) THEN 0 ELSE 1 END",
                        'name_starts': "CASE WHEN LOWER(name) LIKE LOWER(%s) THEN 0 ELSE 1 END"
                    },
                    select_params=[query, f"{query}%"]
                ).order_by('name_exact', 'name_starts', 'name')
            else:
                queryset = queryset.order_by('-updated_at')
            
            return queryset
            
        except Exception as e:
            return Team.objects.none()
    
    def get_context_data(self, **kwargs):
        """Контекст: search_query, фильтры, search_stats."""
        context = super().get_context_data(**kwargs)
        
        try:
            # Добавляем параметры поиска
            context.update({
                'search_query': self.request.GET.get('q', ''),
                'status_filter': self.request.GET.get('status', ''),
                'created_from': self.request.GET.get('created_from', ''),
                'created_to': self.request.GET.get('created_to', ''),
                'status_choices': TeamStatus.choices,
            })
            
            # Статистика поиска
            if context['search_query']:
                context['search_stats'] = {
                    'query': context['search_query'],
                    'total_results': context['paginator'].count if context.get('is_paginated') else len(context['teams']),
                    'has_results': context['paginator'].count > 0 if context.get('is_paginated') else len(context['teams']) > 0
                }
            
        except Exception as e:
            context['error'] = 'Ошибка при выполнении поиска'
        
        return context


class MyTeamsView(TeamFilterMixin, TeamListView):
    """Команды, созданные пользователем (creator)."""
    
    template_name = "teams/my_teams.html"
    
    def get_queryset(self):
        """Фильтр: creator=user + apply_team_filters()."""
        try:
            # Базовый queryset - только команды, созданные пользователем
            queryset = Team.objects.filter(creator=self.request.user)
            
            # Применяем общие фильтры через mixin
            return self.apply_team_filters(queryset)
            
        except Exception as e:
            return Team.objects.none()


class JoinedTeamsView(TeamFilterMixin, TeamListView):
    """Команды, где пользователь активный участник (не creator)."""
    
    template_name = "teams/joined_teams.html"
    
    def get_queryset(self):
        """Фильтр: teammembership (active) exclude creator + apply_team_filters()."""
        try:
            # Базовый queryset - только команды, где пользователь участник (но не создатель)
            queryset = Team.objects.filter(
                teammembership__user=self.request.user,
                teammembership__is_active=True
            ).exclude(creator=self.request.user).distinct()
            
            # Применяем общие фильтры через mixin
            return self.apply_team_filters(queryset)
            
        except Exception as e:
            return Team.objects.none()