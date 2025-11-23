from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def add_class(field, css_class):
    """Добавляет CSS класс к полю формы Django"""
    return field.as_widget(attrs={'class': css_class})

@register.filter
def avatar_url(user):
    """Возвращает URL аватарки пользователя или None если аватарки нет"""
    if user and hasattr(user, 'avatar') and user.avatar:
        return user.avatar.url
    return None

@register.inclusion_tag('users/components/avatar.html')
def user_avatar(user, size='40', css_class=''):
    """
    Отображает аватарку пользователя или Font Awesome заглушку.
    
    Args:
        user: объект пользователя
        size: размер аватарки в пикселях (по умолчанию 40)
        css_class: дополнительные CSS классы
    """
    return {
        'user': user,
        'avatar_url': avatar_url(user),
        'size': size,
        'css_class': css_class
    }


@register.filter
def russian_pluralize(value, forms):
    """
    Склонение русских существительных.
    
    Использование:
        {{ count|russian_pluralize:"команда,команды,команд" }}
        {{ count|russian_pluralize:"задача,задачи,задач" }}
        {{ count|russian_pluralize:"проект,проекта,проектов" }}
    
    Args:
        value: число
        forms: строка с тремя формами через запятую (1, 2-4, 5+)
    
    Returns:
        Правильная форма слова
    """
    try:
        value = int(value)
    except (ValueError, TypeError):
        return forms.split(',')[0]
    
    forms_list = [form.strip() for form in forms.split(',')]
    
    if len(forms_list) != 3:
        return forms_list[0] if forms_list else ''
    
    # Правила русского языка
    if value % 10 == 1 and value % 100 != 11:
        return forms_list[0]  # 1, 21, 31... (команда)
    elif 2 <= value % 10 <= 4 and (value % 100 < 10 or value % 100 >= 20):
        return forms_list[1]  # 2-4, 22-24... (команды)
    else:
        return forms_list[2]  # 0, 5-20, 25-30... (команд)
