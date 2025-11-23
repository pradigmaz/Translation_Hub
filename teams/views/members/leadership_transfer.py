"""
Представление для передачи прав руководителя команды.

Серверный рендеринг без JavaScript:
- GET: Отображение формы подтверждения с выбором ролей
- POST: Передача прав и редирект

Design Patterns:
- FormView для обработки формы
- Strategy Pattern для различных стратегий передачи

Best Practices:
- Type hints для всех методов (PEP 484)
- Docstrings на русском языке
- Логирование операций
- Django messages для уведомлений
"""

from typing import Optional
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from ...models import Team, TeamMembership, Role
from ...mixins import TeamPermissionMixin
from ...forms import LeadershipTransferForm

User = get_user_model()


class LeadershipTransferView(LoginRequiredMixin, TeamPermissionMixin, FormView):
    """
    Представление для передачи прав руководителя команды.
    
    Архитектурные решения:
    - FormView для обработки формы с валидацией
    - GET запрос отображает форму подтверждения
    - POST запрос передает права и делает редирект
    - Использование Django messages для уведомлений
    - Проверка, что текущий пользователь - создатель команды
    
    Attributes:
        template_name (str): Путь к шаблону
        form_class: Класс формы для передачи прав
        team_url_kwarg (str): Имя параметра URL для получения ID команды
    """
    
    template_name = 'teams/members/leadership_transfer.html'
    form_class = LeadershipTransferForm
    team_url_kwarg = 'team_id'
    
    def dispatch(self, request, *args, **kwargs):
        """Переопределяем dispatch для проверки прав и кэширования объектов."""
        # Получаем команду через миксин
        self.team = self.get_team_or_404()
        
        # Проверяем, что текущий пользователь - создатель команды
        if self.team.creator != request.user:
            messages.error(request, 'Только создатель команды может передать права руководителя.')
            return redirect('teams:team_member_list', team_id=self.team.id)
        
        # Получаем нового руководителя
        user_id = self.kwargs.get('user_id')
        self.new_leader = get_object_or_404(User, pk=user_id)
        
        # Проверяем, что новый руководитель - участник команды
        try:
            self.new_leader_membership = TeamMembership.objects.get(
                team=self.team,
                user=self.new_leader,
                is_active=True
            )
        except TeamMembership.DoesNotExist:
            messages.error(request, 'Пользователь не является участником команды.')
            return redirect('teams:team_member_list', team_id=self.team.id)
        
        # Проверяем, что не пытаемся передать права самому себе
        if self.new_leader == request.user:
            messages.error(request, 'Вы уже являетесь руководителем команды.')
            return redirect('teams:team_member_list', team_id=self.team.id)
        
        # Получаем текущее членство руководителя
        try:
            self.current_leader_membership = TeamMembership.objects.get(
                team=self.team,
                user=request.user,
                is_active=True
            )
        except TeamMembership.DoesNotExist:
            self.current_leader_membership = None
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        """Возвращает аргументы для инициализации формы."""
        kwargs = super().get_form_kwargs()
        kwargs['team'] = self.team
        kwargs['current_leader_membership'] = self.current_leader_membership
        return kwargs
    
    def form_valid(self, form):
        """
        Обработка валидной формы с передачей прав.
        
        Args:
            form: Валидная форма LeadershipTransferForm
            
        Returns:
            HttpResponse: Редирект на страницу команды
        """
        try:
            # Получаем выбранное действие
            action = form.cleaned_data.get('action')
            new_roles = form.cleaned_data.get('new_roles', [])
            
            # Получаем роль руководителя
            leader_role = Role.objects.get(name='Руководитель')
            
            # Передаем права
            # 1. Меняем создателя команды
            old_creator = self.team.creator
            self.team.creator = self.new_leader
            self.team.save()
            
            # 2. Добавляем роль руководителя новому лидеру
            self.new_leader_membership.roles.add(leader_role)
            
            # 3. Обрабатываем текущего руководителя
            if self.current_leader_membership:
                # Убираем роль руководителя
                self.current_leader_membership.roles.remove(leader_role)
                
                if action == 'leave':
                    # Покидаем команду
                    self.current_leader_membership.is_active = False
                    self.current_leader_membership.save()
                elif action == 'choose':
                    # Устанавливаем выбранные роли
                    self.current_leader_membership.roles.set(new_roles)
                else:  # action == 'keep'
                    # Сохраняем все остальные роли (роль "Руководитель" уже убрана выше)
                    remaining_roles = self.current_leader_membership.roles.all()
            
            # Успешное уведомление
            if action == 'leave':
                messages.success(
                    self.request,
                    f'Права руководителя успешно переданы пользователю {self.new_leader.username}. '
                    f'Вы покинули команду.'
                )
            else:
                # Получаем роли для сообщения
                current_roles = self.current_leader_membership.roles.exclude(name='Руководитель')
                role_names = ', '.join([r.name for r in current_roles]) if current_roles.exists() else 'без дополнительных ролей'
                messages.success(
                    self.request,
                    f'Права руководителя успешно переданы пользователю {self.new_leader.username}. '
                    f'Вы остались в команде с ролями: {role_names}.'
                )
            
            return redirect('teams:team_detail', pk=self.team.id)
            
        except Exception as e:
            messages.error(
                self.request,
                'Произошла ошибка при передаче прав. Пожалуйста, попробуйте позже.'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """
        Обработка невалидной формы.
        
        Args:
            form: Невалидная форма с ошибками
            
        Returns:
            HttpResponse: Рендер формы с ошибками
        """
        
        messages.error(
            self.request,
            'Пожалуйста, исправьте ошибки в форме'
        )
        
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """
        Построить контекст для шаблона.
        
        Args:
            **kwargs: Дополнительные аргументы контекста
        
        Returns:
            dict: Контекст с командой, участниками и формой
        """
        context = super().get_context_data(**kwargs)
        context['team'] = self.team
        context['new_leader'] = self.new_leader
        context['current_leader_membership'] = self.current_leader_membership
        
        return context
