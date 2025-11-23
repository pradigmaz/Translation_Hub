from django import template
from glossary.models import CONTENT_TYPE_ICONS

register = template.Library()


@register.filter
def content_type_icon(content_type):
    """Возвращает иконку для типа контента"""
    return CONTENT_TYPE_ICONS.get(content_type, '❓')
