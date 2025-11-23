"""Управление статусом команды."""

from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied

from ..models import Team, TeamStatus, TeamStatusChangeType
from ..permission_checker import RolePermissionChecker
from ..exceptions import TeamPermissionDenied, TeamStatusError
from ..utils import deactivate_team, reactivate_team, disband_team, can_perform_team_action



class TeamStatusManager:
    """Управление статусом команды с проверкой прав и логированием."""
    
    def __init__(self, team, user):
        """Инициализация менеджера."""
        if not team:
            raise ValueError("Team is required")
        if not user:
            raise ValueError("User is required")
        
        self.team = team
        self.user = user
    
    def can_change_status(self, new_status):
        """Проверка возможности изменения статуса."""
        try:
            # Проверяем разрешение на изменение статуса команды
            has_permission = RolePermissionChecker.user_has_team_permission(
                self.user, self.team, 'can_change_team_status'
            )
            
            if not has_permission:
                return {
                    'can_change': False,
                    'reason': 'У вас нет разрешения на изменение статуса команды',
                    'current_status': self.team.status,
                    'new_status': new_status
                }
            
            # Проверяем валидность нового статуса
            valid_statuses = [choice[0] for choice in TeamStatus.choices]
            if new_status not in valid_statuses:
                return {
                    'can_change': False,
                    'reason': f'Некорректный статус: {new_status}',
                    'current_status': self.team.status,
                    'new_status': new_status
                }
            
            # Если статус не изменяется
            if self.team.status == new_status:
                return {
                    'can_change': False,
                    'reason': 'Команда уже имеет указанный статус',
                    'current_status': self.team.status,
                    'new_status': new_status
                }
            
            # Проверяем бизнес-правила переходов статусов
            current_status = self.team.status
            
            # Правила переходов статусов
            allowed_transitions = {
                TeamStatus.ACTIVE: [TeamStatus.INACTIVE, TeamStatus.DISBANDED],
                TeamStatus.INACTIVE: [TeamStatus.ACTIVE, TeamStatus.DISBANDED],
                TeamStatus.DISBANDED: []  # Из распущенного состояния нельзя вернуться
            }
            
            if new_status not in allowed_transitions.get(current_status, []):
                transition_names = {
                    TeamStatus.ACTIVE: 'Активная',
                    TeamStatus.INACTIVE: 'Неактивная',
                    TeamStatus.DISBANDED: 'Распущена'
                }
                
                return {
                    'can_change': False,
                    'reason': f'Нельзя изменить статус с "{transition_names[current_status]}" на "{transition_names[new_status]}"',
                    'current_status': current_status,
                    'new_status': new_status
                }
            
            # Дополнительные проверки с использованием существующих утилит
            # Преобразуем статус в действие для проверки
            status_to_action = {
                TeamStatus.INACTIVE: 'deactivate',
                TeamStatus.ACTIVE: 'reactivate',
                TeamStatus.DISBANDED: 'disband'
            }
            action = status_to_action.get(new_status)
            
            if action:
                can_perform, reason = can_perform_team_action(self.team, self.user, action)
                if not can_perform:
                    return {
                        'can_change': False,
                        'reason': reason,
                        'current_status': current_status,
                        'new_status': new_status
                    }
            
            # Все проверки пройдены
            return {
                'can_change': True,
                'reason': None,
                'current_status': current_status,
                'new_status': new_status
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('role_audit')
            logger.error(
                f"Error checking status change | Team: {self.team.name} (ID: {self.team.id}) | "
                f"User: {self.user.username} | New status: {new_status} | Error: {str(e)}",
                exc_info=True
            )
            return {
                'can_change': False,
                'reason': f'Произошла ошибка при проверке возможности изменения статуса: {str(e)}',
                'current_status': self.team.status,
                'new_status': new_status
            }
    
    def change_status(self, new_status, reason=""):
        """Изменение статуса команды с логированием."""
        # Проверяем возможность изменения статуса
        check_result = self.can_change_status(new_status)
        
        if not check_result['can_change']:
            if 'разрешения' in check_result['reason']:
                raise TeamPermissionDenied(check_result['reason'])
            else:
                raise TeamStatusError(check_result['reason'])
        
        old_status = self.team.status
        
        try:
            with transaction.atomic():
                # Используем существующие утилиты для изменения статуса
                if new_status == TeamStatus.INACTIVE:
                    success = deactivate_team(self.team, self.user, reason)
                elif new_status == TeamStatus.ACTIVE:
                    success = reactivate_team(self.team, self.user, reason)
                elif new_status == TeamStatus.DISBANDED:
                    success = disband_team(self.team, self.user, reason)
                else:
                    raise ValidationError(f"Неподдерживаемый статус: {new_status}")
                
                if not success:
                    raise TeamStatusError("Не удалось изменить статус команды")
                
                # Обновляем объект команды
                self.team.refresh_from_db()
                
                # Определяем тип изменения для логирования
                change_type_mapping = {
                    (TeamStatus.ACTIVE, TeamStatus.INACTIVE): TeamStatusChangeType.DEACTIVATED,
                    (TeamStatus.INACTIVE, TeamStatus.ACTIVE): TeamStatusChangeType.REACTIVATED,
                    (TeamStatus.ACTIVE, TeamStatus.DISBANDED): TeamStatusChangeType.DISBANDED,
                    (TeamStatus.INACTIVE, TeamStatus.DISBANDED): TeamStatusChangeType.DISBANDED,
                }
                
                change_type = change_type_mapping.get((old_status, new_status))
                
                return {
                    'success': True,
                    'old_status': old_status,
                    'new_status': new_status,
                    'reason': reason,
                    'changed_by': self.user.username,
                    'team_name': self.team.name
                }
                
        except Exception as e:
            raise
    
    # get_status_history удален - история теперь в logs/role_audit.log
    
    def get_available_status_transitions(self):
        """Список доступных переходов статуса."""
        try:
            current_status = self.team.status
            
            # Определяем возможные переходы
            transitions = {
                TeamStatus.ACTIVE: [
                    {'status': TeamStatus.INACTIVE, 'label': 'Приостановить', 'action': 'deactivate'},
                    {'status': TeamStatus.DISBANDED, 'label': 'Распустить', 'action': 'disband'}
                ],
                TeamStatus.INACTIVE: [
                    {'status': TeamStatus.ACTIVE, 'label': 'Возобновить', 'action': 'reactivate'},
                    {'status': TeamStatus.DISBANDED, 'label': 'Распустить', 'action': 'disband'}
                ],
                TeamStatus.DISBANDED: []  # Из распущенного состояния нельзя вернуться
            }
            
            available_transitions = []
            for transition in transitions.get(current_status, []):
                # Проверяем возможность каждого перехода
                check_result = self.can_change_status(transition['status'])
                if check_result['can_change']:
                    available_transitions.append(transition)
            
            return available_transitions
            
        except Exception as e:
            return []
    
    def get_status_info(self):
        """Информация о текущем статусе команды."""
        try:
            status_display = dict(TeamStatus.choices)
            
            return {
                'current_status': self.team.status,
                'current_status_display': status_display.get(self.team.status, self.team.status),
                'is_active': self.team.is_active(),
                'can_be_reactivated': self.team.can_be_reactivated(),
                'can_be_disbanded': self.team.can_be_disbanded(),
                'available_transitions': self.get_available_status_transitions(),
                'last_status_change': self.get_status_history(1)
            }
            
        except Exception as e:
            return {
                'current_status': self.team.status,
                'error': 'Ошибка при получении информации о статусе'
            }