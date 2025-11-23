"""AJAX API для управления статусом команд."""

import json
from django.views.generic import View
from django.core.exceptions import ValidationError

from ...mixins import TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin
from ...components import TeamStatusManager
from ...models import TeamStatus
from ...exceptions import TeamPermissionDenied, TeamNotFoundError, TeamStatusError



class TeamStatusChangeAPI(TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View):
    """API для изменения статуса команды."""
    
    team_permission_required = 'can_change_team_status'
    
    def post(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)
            
            # Парсим JSON данные
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return self.ajax_error(
                    message="Некорректный формат JSON данных",
                    status=400
                )
            
            # Валидируем обязательные поля
            new_status = data.get('status')
            reason = data.get('reason', '')
            
            if not new_status:
                return self.ajax_error(
                    message="Не указан новый статус команды",
                    status=400
                )
            
            # Проверяем валидность статуса
            valid_statuses = [choice[0] for choice in TeamStatus.choices]
            if new_status not in valid_statuses:
                return self.ajax_error(
                    message=f"Некорректный статус: {new_status}",
                    status=400
                )
            
            # Используем TeamStatusManager для изменения статуса
            status_manager = TeamStatusManager(team, request.user)
            
            # Сначала проверяем возможность изменения
            can_change = status_manager.can_change_status(new_status)
            
            if not can_change['can_change']:
                return self.ajax_error(
                    message=can_change['reason'],
                    status=400
                )
            
            # Изменяем статус
            result = status_manager.change_status(new_status, reason)
            
            return self.ajax_success(
                data={
                    'team_id': team.id,
                    'old_status': result['old_status'],
                    'new_status': result['new_status'],
                    'reason': result['reason'],
                    'changed_by': result['changed_by'],
                    'status_display': dict(TeamStatus.choices).get(result['new_status'], result['new_status'])
                },
                message=f'Статус команды изменен на "{dict(TeamStatus.choices).get(new_status, new_status)}"'
            )
            
        except TeamStatusError as e:
            return self.ajax_error(
                message=str(e),
                status=400
            )
        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context='TeamStatusChangeAPI.post')
        except Exception as e:
            return self.handle_ajax_error(e, context='TeamStatusChangeAPI.post')
    
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except TeamStatusError as e:
            return self.ajax_error(
                message=str(e),
                status=400
            )


# TeamStatusHistoryAPI удалена - история теперь в file-based logging


class TeamStatusInfoAPI(TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View):
    """API для получения полной информации о статусе команды."""
    
    def get(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)
            
            # Используем TeamStatusManager для получения информации
            status_manager = TeamStatusManager(team, request.user)
            
            # Получаем полную информацию о статусе
            status_info = status_manager.get_status_info()
            
            # Добавляем информацию о разрешениях пользователя
            from ...permission_checker import RolePermissionChecker
            
            can_change_status = RolePermissionChecker.user_has_team_permission(
                request.user, team, 'can_change_team_status'
            )
            
            status_info.update({
                'team_id': team.id,
                'team_name': team.name,
                'user_can_change_status': can_change_status
            })
            
            return self.ajax_success(
                data=status_info,
                message='Информация о статусе команды загружена'
            )
            
        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context='TeamStatusInfoAPI.get')
        except Exception as e:
            return self.handle_ajax_error(e, context='TeamStatusInfoAPI.get')


class TeamStatusValidationAPI(TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View):
    """API для проверки возможности изменения статуса команды."""
    
    team_permission_required = 'can_change_team_status'
    
    def post(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)
            
            # Парсим JSON данные
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return self.ajax_error(
                    message="Некорректный формат JSON данных",
                    status=400
                )
            
            # Валидируем обязательные поля
            new_status = data.get('status')
            
            if not new_status:
                return self.ajax_error(
                    message="Не указан статус для проверки",
                    status=400
                )
            
            # Проверяем валидность статуса
            valid_statuses = [choice[0] for choice in TeamStatus.choices]
            if new_status not in valid_statuses:
                return self.ajax_error(
                    message=f"Некорректный статус: {new_status}",
                    status=400
                )
            
            # Используем TeamStatusManager для проверки
            status_manager = TeamStatusManager(team, request.user)
            
            # Проверяем возможность изменения
            validation_result = status_manager.can_change_status(new_status)
            
            # Добавляем дополнительную информацию
            validation_result.update({
                'team_id': team.id,
                'team_name': team.name,
                'new_status_display': dict(TeamStatus.choices).get(new_status, new_status),
                'current_status_display': dict(TeamStatus.choices).get(validation_result['current_status'], validation_result['current_status'])
            })
            
            message = 'Изменение статуса возможно' if validation_result['can_change'] else 'Изменение статуса невозможно'
            
            return self.ajax_success(
                data=validation_result,
                message=message
            )
            
        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context='TeamStatusValidationAPI.post')
        except Exception as e:
            return self.handle_ajax_error(e, context='TeamStatusValidationAPI.post')
    
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except (TeamStatusError, ValidationError) as e:
            return self.ajax_error(
                message=str(e),
                status=400
            )
        except Exception as e:
            return self.ajax_error(
                message="Произошла внутренняя ошибка сервера",
                status=500
            )