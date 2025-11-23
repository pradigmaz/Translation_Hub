"""
Представления настроек для приложения users.

Содержит представления для управления командами, задачами и настройками аккаунта.
"""

from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from teams.models import TeamMembership
from projects.models import Chapter
from ..models import User
from ..forms import SettingsForm, CustomPasswordChangeForm
from ..mixins import PerformanceMonitoringMixin


class TeamsView(LoginRequiredMixin, PerformanceMonitoringMixin, TemplateView):
    """
    Представление для отображения команд пользователя с ролями
    """
    template_name = "users/teams.html"

    def get_context_data(self, **kwargs):
        """
        Подготовка данных о командах пользователя для шаблона с оптимизацией
        """
        context = super().get_context_data(**kwargs)
        current_user = self.request.user

        # Получаем активные членства пользователя в командах с ролями с оптимизированными запросами
        team_memberships = TeamMembership.objects.filter(
            user=current_user,
            is_active=True
        ).select_related('team').prefetch_related('roles').order_by('team__name')

        context["team_memberships"] = team_memberships
        context["teams_count"] = team_memberships.count()

        return context


class TasksView(LoginRequiredMixin, PerformanceMonitoringMixin, TemplateView):
    """
    Представление для отображения задач пользователя
    """
    template_name = "users/tasks.html"

    def get_context_data(self, **kwargs):
        """
        Подготовка данных о задачах пользователя для шаблона с оптимизацией
        """
        context = super().get_context_data(**kwargs)
        current_user = self.request.user

        # Получаем все назначенные пользователю задачи (исключая завершённые) с информацией о проекте с оптимизацией
        user_tasks = Chapter.objects.filter(
            assignee=current_user
        ).exclude(status='done').select_related('project', 'project__team').order_by('-created_at')

        context["user_tasks"] = user_tasks
        context["tasks_count"] = user_tasks.count()
        
        # Группировка задач по статусам для удобства отображения (без done, т.к. уже исключены)
        context["tasks_by_status"] = {
            'raw': user_tasks.filter(status='raw'),
            'translating': user_tasks.filter(status='translating'),
            'cleaning': user_tasks.filter(status='cleaning'),
            'typesetting': user_tasks.filter(status='typesetting'),
            'editing': user_tasks.filter(status='editing'),
        }

        return context


class SettingsView(LoginRequiredMixin, PerformanceMonitoringMixin, FormView):
    """
    Представление для изменения настроек аккаунта (email и пароль)
    """
    template_name = "users/settings.html"
    form_class = SettingsForm
    success_url = reverse_lazy("users:settings")

    def get_form_kwargs(self):
        """
        Передача текущего пользователя в форму
        """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Добавление формы смены пароля в контекст
        """
        context = super().get_context_data(**kwargs)
        
        # Добавляем форму смены пароля
        if 'password_form' not in context:
            context['password_form'] = CustomPasswordChangeForm(user=self.request.user)
        
        return context

    def post(self, request, *args, **kwargs):
        """
        Обработка POST запросов для профиля, настроек и смены пароля
        """
        form_type = request.POST.get('form_type')
        
        if form_type == 'profile':
            return self.handle_profile_update(request)
        elif form_type == 'password':
            return self.handle_password_change(request)
        else:
            return super().post(request, *args, **kwargs)

    def handle_profile_update(self, request):
        """
        Обработка обновления профиля (аватарка, email)
        Упрощенная версия - базовая валидация
        """
        user = request.user
        
        # Получаем данные из формы
        email = request.POST.get('email', '').strip()
        avatar = request.FILES.get('avatar')
        
        # Валидация email (необязательное поле)
        if email:
            try:
                validate_email(email)
                # Проверка уникальности email (исключая текущего пользователя)
                if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                    messages.error(request, 'Пользователь с таким email уже существует')
                    return HttpResponseRedirect(self.success_url)
                user.email = email
            except ValidationError:
                messages.error(request, 'Некорректный формат email адреса')
                return HttpResponseRedirect(self.success_url)
        else:
            # Разрешаем пустой email
            user.email = ''
        
        # Обновляем аватарку
        if avatar:
            # Простая валидация размера файла
            if avatar.size > 2 * 1024 * 1024:  # 2MB
                messages.error(request, 'Размер файла не должен превышать 2MB')
                return HttpResponseRedirect(self.success_url)
            
            # Проверка типа файла
            if not avatar.content_type in ['image/jpeg', 'image/png']:
                messages.error(request, 'Поддерживаются только JPG и PNG файлы')
                return HttpResponseRedirect(self.success_url)
            
            user.avatar = avatar
        
        # Сохраняем пользователя
        try:
            user.save()
            messages.success(request, 'Настройки успешно сохранены')
        except Exception:
            messages.error(request, 'Ошибка при сохранении настроек')
        
        return HttpResponseRedirect(self.success_url)

    def handle_password_change(self, request):
        """
        Обработка смены пароля
        """
        password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        
        if password_form.is_valid():
            password_form.save()
            messages.success(request, 'Пароль успешно изменен')
            return HttpResponseRedirect(self.success_url)
        else:
            # Если форма пароля невалидна, показываем ошибки
            for error in password_form.errors.values():
                messages.error(request, error[0])
            
            context = self.get_context_data()
            context['password_form'] = password_form
            return self.render_to_response(context)

    def form_valid(self, form):
        """
        Обработка успешной валидации формы email
        """
        user = self.request.user
        user.email = form.cleaned_data['email']
        
        try:
            user.save()
        except Exception:
            pass
        
        return super().form_valid(form)

    def form_invalid(self, form):
        """
        Обработка ошибок валидации
        """
        return super().form_invalid(form)