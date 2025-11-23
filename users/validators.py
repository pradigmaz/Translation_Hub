# users/validators.py

from django.core.exceptions import ValidationError
import re


def validate_safe_username(username):
    """
    Валидатор для проверки безопасности username
    """
    if not username:
        return
    
    # Проверяем длину
    if len(username) < 3:
        raise ValidationError('Логин должен содержать минимум 3 символа.')
    
    if len(username) > 150:
        raise ValidationError('Логин не может быть длиннее 150 символов.')
    
    # Проверяем допустимые символы
    if not re.match(r'^[\w.@+-]+$', username):
        raise ValidationError(
            'Логин может содержать только буквы, цифры и символы @/./+/-/_'
        )
    
    # Проверяем на зарезервированные имена
    reserved_names = [
        'admin', 'root', 'administrator', 'moderator', 'system', 'api', 'www',
        'mail', 'email', 'support', 'help', 'info', 'contact', 'about',
        'login', 'register', 'signup', 'signin', 'logout', 'profile', 'settings'
    ]
    
    if username.lower() in reserved_names:
        raise ValidationError(f'Логин "{username}" зарезервирован системой. Выберите другой.')
