"""Управление статусом команд через TeamStatusManager."""

import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import View, DetailView
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from ..mixins import TeamPermissionMixin, AjaxResponseMixin
from ..components import TeamStatusManager, TeamContextBuilder
from ..models import Team, TeamStatus
from ..exceptions import TeamPermissionDenied, TeamStatusError



class TeamStatusChangeView(TeamPermissionMixin, AjaxResponseMixin, View):
    """Изменение статуса команды (AJAX/HTTP). Логика в TeamStatusManager."""
    
    team_permission_required = 'can_change_team_status'
    team_url_kwarg = 'team_id'
    
    def _parse_request_data(self, request):
        """Извлекает новый статус и причину из запроса."""
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            return data.get('status'), data.get('reason', '')
        return request.POST.get('status'), request.POST.get('reason', '')
    
    def _handle_error(self, request, team_id, message, status=400):
        """Обрабатывает ошибку в зависимости от типа запроса."""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.ajax_error(message=message, status=status)
        messages.error(request, message)
        return redirect('teams:team_detail', pk=team_id)
    
    def _handle_success(self, request, team_id, result, new_status):
        """Обрабатывает успешное изменение статуса."""
        success_message = f'Статус команды изменен на "{dict(TeamStatus.choices).get(new_status, new_status)}"'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return self.ajax_success(
                data={
                    'team_id': result.get('team_id', team_id),
                    'old_status': result['old_status'],
                    'new_status': result['new_status'],
                    'reason': result['reason'],
                    'changed_by': result['changed_by'],
                    'status_display': dict(TeamStatus.choices).get(result['new_status'], result['new_status'])
                },
                message=success_message
            )
        messages.success(request, success_message)
        return redirect('teams:team_detail', pk=team_id)
    
    def post(self, request, team_id):
        """Изменить статус команды."""
        try:
            team = self.get_team_or_404(team_id)
            
            # Парсим данные запроса
            try:
                new_status, reason = self._parse_request_data(request)
            except json.JSONDecodeError:
                return self._handle_error(request, team_id, "Некорректный формат JSON данных")
            
            if not new_status:
                return self._handle_error(request, team_id, "Не указан новый статус команды")
            
            # Проверяем и изменяем статус
            status_manager = TeamStatusManager(team, request.user)
            can_change = status_manager.can_change_status(new_status)
            
            if not can_change['can_change']:
                return self._handle_error(request, team_id, can_change['reason'])
            
            result = status_manager.change_status(new_status, reason)
            
            return self._handle_success(request, team_id, result, new_status)
            
        except TeamStatusError as e:
            return self._handle_error(request, team_id, str(e))
        except TeamPermissionDenied as e:
            return self.handle_permission_denied(e)
        except Exception as e:
            import logging
            logger = logging.getLogger('role_audit')
            logger.error(
                f"Error in TeamStatusChangeView | Team ID: {team_id} | "
                f"User: {request.user.username} | Error: {str(e)}",
                exc_info=True
            )
            return self._handle_error(request, team_id, f"Произошла ошибка при изменении статуса команды: {str(e)}", 500)


# TeamStatusHistoryView удалена - история теперь в file-based logging


class TeamStatusInfoView(LoginRequiredMixin, TeamPermissionMixin, AjaxResponseMixin, View):
    """
    Представление для получения информации о статусе команды.
    
    Возвращает полную информацию о текущем статусе команды,
    доступных переходах и ограничениях. Поддерживает только AJAX запросы.
    """
    
    team_url_kwarg = 'team_id'
    
    def get(self, request, team_id):
        """
        Получить информацию о статусе команды.
        
        Args:
            request: HTTP запрос
            team_id: ID команды
            
        Returns:
            JsonResponse: Информация о статусе команды
        """
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)
            
            # Используем TeamStatusManager для получения информации
            status_manager = TeamStatusManager(team, request.user)
            status_info = status_manager.get_status_info()
            
            # Добавляем дополнительную информацию
            status_info.update({
                'team_id': team.id,
                'team_name': team.name,
                'user_can_change_status': status_info.get('available_transitions', []) != []
            })
            
            return self.ajax_success(
                data=status_info,
                message='Информация о статусе команды загружена'
            )
            
        except (TeamPermissionDenied) as e:
            return self.handle_ajax_error(e, context='TeamStatusInfoView.get')
        except Exception as e:
            return self.handle_ajax_error(e, context='TeamStatusInfoView.get')


class TeamStatusValidateView(LoginRequiredMixin, TeamPermissionMixin, AjaxResponseMixin, View):
    """
    Представление для валидации возможности изменения статуса команды.
    
    Проверяет возможность изменения статуса без фактического изменения.
    Поддерживает только AJAX запросы.
    """
    
    team_permission_required = 'can_change_team_status'
    team_url_kwarg = 'team_id'
    
    def post(self, request, team_id):
        """Валидация возможности изменения статуса через TeamStatusManager."""
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
            
            new_status = data.get('status')
            
            if not new_status:
                return self.ajax_error(
                    message="Не указан статус для проверки",
                    status=400
                )
            
            # Используем TeamStatusManager для валидации
            status_manager = TeamStatusManager(team, request.user)
            validation_result = status_manager.can_change_status(new_status)
            
            # Добавляем дополнительную информацию
            validation_result.update({
                'team_id': team.id,
                'team_name': team.name,
                'new_status_display': dict(TeamStatus.choices).get(new_status, new_status),
                'current_status_display': dict(TeamStatus.choices).get(
                    validation_result['current_status'], 
                    validation_result['current_status']
                )
            })
            
            message = 'Изменение статуса возможно' if validation_result['can_change'] else 'Изменение статуса невозможно'
            
            return self.ajax_success(
                data=validation_result,
                message=message
            )
            
        except (TeamPermissionDenied) as e:
            return self.handle_ajax_error(e, context='TeamStatusValidateView.post')
        except Exception as e:
            return self.handle_ajax_error(e, context='TeamStatusValidateView.post')


class TeamStatusBulkChangeView(LoginRequiredMixin, TeamPermissionMixin, AjaxResponseMixin, View):
    """Массовое изменение статуса команд (AJAX only)."""
    
    def post(self, request):
        """Массовое изменение статуса (JSON с массивом операций)."""
        try:
            # Парсим JSON данные
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return self.ajax_error(
                    message="Некорректный формат JSON данных",
                    status=400
                )
            
            operations = data.get('operations', [])
            if not operations:
                return self.ajax_error(
                    message="Не указаны операции для выполнения",
                    status=400
                )
            
            results = []
            errors = []
            
            # Выполняем операции
            for i, operation in enumerate(operations):
                try:
                    team_id = operation.get('team_id')
                    new_status = operation.get('status')
                    reason = operation.get('reason', '')
                    
                    if not team_id or not new_status:
                        errors.append(f"Операция {i+1}: отсутствует ID команды или статус")
                        continue
                    
                    # Получаем команду с проверкой доступа
                    team = self.get_team_or_404(team_id)
                    
                    # Используем TeamStatusManager
                    status_manager = TeamStatusManager(team, request.user)
                    
                    # Проверяем возможность изменения
                    can_change = status_manager.can_change_status(new_status)
                    
                    if not can_change['can_change']:
                        errors.append(f"Операция {i+1} (команда {team.name}): {can_change['reason']}")
                        continue
                    
                    # Изменяем статус
                    result = status_manager.change_status(new_status, reason)
                    
                    results.append({
                        'team_id': team_id,
                        'team_name': team.name,
                        'old_status': result['old_status'],
                        'new_status': result['new_status'],
                        'success': True
                    })
                    
                except Exception as e:
                    errors.append(f"Операция {i+1}: {str(e)}")
            
            # Формируем ответ
            response_data = {
                'results': results,
                'total_operations': len(operations),
                'successful_operations': len(results),
                'failed_operations': len(errors)
            }
            
            if errors:
                response_data['errors'] = errors
            
            message = f"Выполнено {len(results)} из {len(operations)} операций"
            if errors:
                message += f", {len(errors)} ошибок"
            
            return self.ajax_success(
                data=response_data,
                message=message
            )
            
        except Exception as e:
            return self.handle_ajax_error(e, context='TeamStatusBulkChangeView.post')