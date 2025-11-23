"""Кастомные исключения для приложения teams."""

from django.core.exceptions import PermissionDenied


class TeamPermissionDenied(PermissionDenied):
    """Исключение для ошибок разрешений в команде."""
    
    def __init__(self, message=None, team=None, permission=None, user=None):
        self.team = team
        self.permission = permission
        self.user = user
        
        if not message:
            if permission and team:
                message = f"У вас нет разрешения '{permission}' в команде '{team.name}'"
            elif team:
                message = f"У вас нет прав для выполнения этого действия в команде '{team.name}'"
            else:
                message = "У вас нет прав для выполнения этого действия в команде"
        
        super().__init__(message)


class TeamNotFoundError(Exception):
    """Исключение для случаев, когда команда не найдена."""
    
    def __init__(self, team_id=None, message=None):
        self.team_id = team_id
        
        if not message:
            if team_id:
                message = f"Команда с ID {team_id} не найдена"
            else:
                message = "Команда не найдена"
        
        super().__init__(message)


class TeamStatusError(Exception):
    """Исключение для ошибок, связанных со статусом команды."""
    
    def __init__(self, team=None, current_status=None, required_status=None, message=None):
        self.team = team
        self.current_status = current_status
        self.required_status = required_status
        
        if not message:
            if team and current_status and required_status:
                message = (
                    f"Команда '{team.name}' имеет статус '{current_status}', "
                    f"но требуется статус '{required_status}'"
                )
            elif team and current_status:
                message = f"Команда '{team.name}' имеет неподходящий статус '{current_status}'"
            else:
                message = "Неподходящий статус команды для выполнения операции"
        
        super().__init__(message)


class RoleAssignmentError(Exception):
    """Исключение для ошибок назначения ролей."""
    
    def __init__(self, user=None, role=None, team=None, message=None):
        self.user = user
        self.role = role
        self.team = team
        
        if not message:
            if user and role and team:
                message = f"Не удалось назначить роль '{role.name}' пользователю '{user.username}' в команде '{team.name}'"
            else:
                message = "Ошибка при назначении роли"
        
        super().__init__(message)


class TeamMemberPermissionDenied(TeamPermissionDenied):
    """Исключение для ошибок доступа к управлению участниками команды."""
    
    def __init__(self, team, permission, user, action=None, message=None):
        self.action = action
        
        if not message:
            action_text = f" для действия '{action}'" if action else ""
            message = f"У пользователя {user.username} нет разрешения {permission} в команде {team.name}{action_text}"
        
        super().__init__(message, team, permission, user)


class MemberAlreadyExistsError(Exception):
    """Исключение для случаев, когда пользователь уже является участником команды."""
    
    def __init__(self, user=None, team=None, message=None):
        self.user = user
        self.team = team
        
        if not message:
            if user and team:
                message = f"Пользователь {user.username} уже является участником команды {team.name}"
            else:
                message = "Пользователь уже является участником команды"
        
        super().__init__(message)


class CannotRemoveCreatorError(Exception):
    """Исключение для случаев, когда пытаются удалить создателя команды."""
    
    def __init__(self, user=None, team=None, message=None):
        self.user = user
        self.team = team
        
        if not message:
            if user and team:
                message = f"Нельзя удалить создателя команды {user.username} из команды {team.name}"
            else:
                message = "Нельзя удалить создателя команды"
        
        super().__init__(message)