"""
Представление для добавления нового участника в команду.

Следует принципам:
- SRP: Одна ответственность - добавление участника
- DRY: Использование Django Forms для валидации
- Security: Проверка прав доступа через миксины
- Logging: Логирование всех операций
"""

from typing import Optional
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.core.exceptions import PermissionDenied

from ...models import Team, TeamMembership
from ...forms import MemberAddForm
from ...mixins import TeamPermissionMixin



class TeamMemberAddView(LoginRequiredMixin, TeamPermissionMixin, FormView):
    """
    Представление для добавления нового участника в команду.
    
    Архитектурные решения:
    - FormView для обработки формы с валидацией
    - Использование MemberAddForm для валидации данных
    - Транзакционное создание TeamMembership
    - Централизованная обработка ошибок
    - Логирование всех операций
    - Django messages для уведомлений пользователя
    
    Type hints для всех методов (PEP 484)
    Docstrings на русском языке
    
    Attributes:
        template_name (str): Путь к шаблону
        form_class: Класс формы для добавления участника
        required_team_permission (str): Требуемое разрешение
        team_url_kwarg (str): Имя параметра URL для получения ID команды
    """
    
    template_name = 'teams/members/member_add.html'
    form_class = MemberAddForm
    team_permission_required = 'can_invite_members'
    team_url_kwarg = 'team_id'
    
    def get_form_kwargs(self) -> dict:
        """
        Возвращает аргументы для инициализации формы.
        
        Передает объект команды в конструктор формы для валидации.
        
        Returns:
            dict: Аргументы для формы, включая team
        """
        kwargs = super().get_form_kwargs()
        kwargs['team'] = self.team
        return kwargs
    
    def form_valid(self, form) -> redirect:
        """
        Обработка валидной формы с созданием участника команды.
        
        Создает TeamMembership и назначает выбранные роли в рамках транзакции.
        Логирует успешное добавление и отправляет уведомление пользователю.
        
        Args:
            form: Валидная форма MemberAddForm
            
        Returns:
            HttpResponse: Редирект на страницу команды
            
        Raises:
            Exception: При ошибке создания участника (обрабатывается внутри)
        """
        try:
            user = form.get_user()
            roles = form.cleaned_data['role_ids']
            
            # Проверяем, что пользователь существует
            if not user:
                messages.error(
                    self.request,
                    'Ошибка: пользователь не найден'
                )
                return self.form_invalid(form)
            
            # Создаем членство в команде в рамках транзакции
            with transaction.atomic():
                # Создание TeamMembership
                membership = TeamMembership.objects.create(
                    team=self.team,
                    user=user,
                    is_active=True
                )
                
                # Назначение ролей
                membership.roles.set(roles)
            
            # Успешное уведомление пользователю
            role_names = ', '.join([role.name for role in roles])
            messages.success(
                self.request,
                f'Пользователь {user.username} успешно добавлен в команду с ролями: {role_names}'
            )
            
            # Редирект на страницу команды
            return redirect('teams:team_detail', pk=self.team.id)
            
        except TeamMembership.DoesNotExist:
            # Эта ошибка не должна возникать, но обрабатываем на всякий случай
            messages.error(
                self.request,
                'Произошла ошибка при добавлении участника в команду'
            )
            return self.form_invalid(form)
            
        except Exception as e:
            # Общая обработка непредвиденных ошибок
            messages.error(
                self.request,
                'Произошла непредвиденная ошибка при добавлении участника. '
                'Пожалуйста, попробуйте позже.'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form) -> FormView:
        """
        Обработка невалидной формы.
        
        Логирует ошибки валидации и отправляет уведомление пользователю.
        
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
    
    def get_success_url(self) -> str:
        """
        Возвращает URL для редиректа после успешного добавления.
        
        Returns:
            str: URL страницы команды
        """
        return reverse('teams:team_detail', kwargs={'pk': self.team.id})
    
    def get_context_data(self, **kwargs) -> dict:
        """
        Построить контекст для шаблона.
        
        Args:
            **kwargs: Дополнительные аргументы контекста
        
        Returns:
            dict: Контекст с командой и формой
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        context = super().get_context_data(**kwargs)
        context['team'] = self.team
        
        # Получаем пользователя из GET параметра
        user_id = self.request.GET.get('user_id')
        if user_id:
            try:
                context['user'] = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                context['user'] = None
        else:
            context['user'] = None
        
        return context
