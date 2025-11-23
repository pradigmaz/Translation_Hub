"""
Миксины для представлений команд.

Этот модуль содержит переиспользуемые миксины для упрощения
разработки представлений команд и обеспечения единообразия.
"""

# Импорты будут добавлены по мере создания миксинов
from .permissions import TeamPermissionMixin, TeamOwnerRequiredMixin, TeamMemberRequiredMixin
from .ajax import AjaxResponseMixin, AjaxRequiredMixin, AjaxFormMixin
from .context import TeamContextMixin, TeamMemberContextMixin
from .performance import PerformanceMonitoringMixin, CacheControlMixin, QueryOptimizationMixin

__all__ = [
    'TeamPermissionMixin',
    'TeamOwnerRequiredMixin',
    'TeamMemberRequiredMixin',
    'AjaxResponseMixin',
    'AjaxRequiredMixin',
    'AjaxFormMixin',
    'TeamContextMixin',
    'TeamMemberContextMixin',
    'PerformanceMonitoringMixin',
    'CacheControlMixin',
    'QueryOptimizationMixin',
]