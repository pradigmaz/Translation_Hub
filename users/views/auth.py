"""
Представления аутентификации для приложения users.

Содержит представления для регистрации и связанные формы.
"""

from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib import messages

from utils.network import get_client_ip
from ..models import User
from ..validators import validate_safe_username
from ..mixins import PerformanceMonitoringMixin

# Настройка логгера безопасности


class CustomUserCreationForm(UserCreationForm):
    """
    Кастомная форма регистрации для модели User с дополнительной валидацией
    """

    class Meta:
        model = User
        fields = ("username", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавление CSS классов для стилизации полей формы
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            
        # Добавление подсказок для безопасности
        self.fields['username'].help_text = "Только буквы, цифры и символы @/./+/-/_"
        self.fields['password1'].help_text = "Минимум 12 символов, не должен быть слишком простым"

    def clean_username(self):
        """Валидация имени пользователя"""
        username = self.cleaned_data.get('username')
        
        if username:
            # Проверка безопасности username
            validate_safe_username(username)
            
            # Проверка уникальности
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('Пользователь с таким логином уже существует.')
            
        return username


class RegisterView(PerformanceMonitoringMixin, CreateView):
    """Представление для регистрации новых пользователей с логированием"""
    
    form_class = CustomUserCreationForm
    model = User
    template_name = "users/register.html"
    success_url = reverse_lazy("users:login")
    
    def form_valid(self, form):
        """Обработка успешной регистрации с логированием"""
        response = super().form_valid(form)
        
        # Логирование успешной регистрации
        
        return response
    
    def form_invalid(self, form):
        """Обработка неудачной регистрации с логированием"""
        # Логирование неудачной попытки регистрации
        
        return super().form_invalid(form)