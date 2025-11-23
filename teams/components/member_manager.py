
from django.db import transaction
from django.db.models import Q, Prefetch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied

from ..models import Team, TeamMembership, Role
from ..permission_checker import RolePermissionChecker
from ..exceptions import TeamPermissionDenied, TeamNotFoundError

User = get_user_model()


class TeamMemberManager:
    """Управление участниками команды с проверкой прав доступа."""
    
    def __init__(self, team, user):
        if not team:
            raise ValueError("Team is required")
        if not user:
            raise ValueError("User is required")
        
        self.team = team
        self.user = user
    
    def get_members_with_roles(self, include_inactive=False):
        """Получить участников команды с ролями (оптимизированный запрос)."""
        try:
            # Оптимизированный запрос участников с ролями
            memberships_query = TeamMembership.objects.filter(team=self.team)
            
            if not include_inactive:
                memberships_query = memberships_query.filter(is_active=True)
            
            # Используем select_related для user и prefetch_related для roles
            memberships = memberships_query.select_related('user').prefetch_related(
                Prefetch('roles', queryset=Role.objects.only('id', 'name'))
            ).order_by('user__username')
            
            members_data = []
            for membership in memberships:
                member_user = membership.user
                roles = list(membership.roles.values('id', 'name'))
                
                member_data = {
                    'id': member_user.id,  # Для совместимости с JavaScript
                    'user_id': member_user.id,  # Для обратной совместимости
                    'name': getattr(member_user, 'display_name', '') or member_user.username,  # Для JavaScript
                    'username': member_user.username,
                    'display_name': getattr(member_user, 'display_name', '') or member_user.username,
                    'email': member_user.email,
                    'is_creator': member_user == self.team.creator,
                    'is_active': membership.is_active,
                    'joined_at': membership.joined_at.isoformat() if membership.joined_at else None,
                    'roles': roles,
                    'role_names': [role['name'] for role in roles],
                    'membership_id': membership.id
                }
                
                # Добавляем аватар если есть
                if hasattr(member_user, 'avatar') and member_user.avatar:
                    member_data['avatar'] = member_user.avatar.url
                    member_data['avatar_url'] = member_user.avatar.url  # Для обратной совместимости
                else:
                    member_data['avatar'] = None
                
                members_data.append(member_data)
            
            return members_data
            
        except Exception as e:
            raise
    
    def add_member(self, new_user, roles=None):
        """Добавить участника в команду с проверкой прав."""
        # Проверяем разрешение на приглашение участников
        if not RolePermissionChecker.user_has_team_permission(
            self.user, self.team, 'can_invite_members'
        ):
            raise TeamPermissionDenied("У вас нет разрешения на приглашение участников")
        
        # Проверяем, что пользователь не является уже участником
        existing_membership = TeamMembership.objects.filter(
            team=self.team,
            user=new_user
        ).first()
        
        if existing_membership and existing_membership.is_active:
            raise ValidationError(f"Пользователь {new_user.username} уже является участником команды")
        
        try:
            with transaction.atomic():
                # Создаем или реактивируем участие
                if existing_membership:
                    membership = existing_membership
                    membership.reactivate()
                else:
                    membership = TeamMembership.objects.create(
                        team=self.team,
                        user=new_user,
                        is_active=True
                    )
                
                # Назначаем роли если указаны
                if roles:
                    role_objects = self._resolve_roles(roles)
                    for role in role_objects:
                        membership.add_role(role, admin_user=self.user)
                
                # Возвращаем информацию о добавленном участнике
                return {
                    'user_id': new_user.id,
                    'username': new_user.username,
                    'display_name': getattr(new_user, 'display_name', '') or new_user.username,
                    'email': new_user.email,
                    'roles': [{'id': role.id, 'name': role.name} for role in role_objects] if roles else [],
                    'joined_at': membership.joined_at.isoformat() if membership.joined_at else None
                }
                
        except Exception as e:
            raise
    
    def remove_member(self, member_user):
        """Удалить участника из команды (создателя удалить нельзя)."""
        # Проверяем разрешение на удаление участников
        if not RolePermissionChecker.user_has_team_permission(
            self.user, self.team, 'can_remove_members'
        ):
            raise TeamPermissionDenied("У вас нет разрешения на удаление участников")
        
        # Нельзя удалить создателя команды
        if member_user == self.team.creator:
            raise ValidationError("Нельзя удалить создателя команды")
        
        # Получаем участие пользователя
        try:
            membership = TeamMembership.objects.get(
                team=self.team,
                user=member_user,
                is_active=True
            )
        except TeamMembership.DoesNotExist:
            raise ValidationError(f"Пользователь {member_user.username} не является активным участником команды")
        
        try:
            with transaction.atomic():
                # Сохраняем информацию о ролях для логирования
                role_names = [role.name for role in membership.roles.all()]
                
                # Деактивируем участие
                membership.deactivate()
                return True
                
        except Exception as e:
            raise
    
    def update_member_roles(self, member_user, roles):
        """Обновить роли участника команды."""
        # Проверяем разрешение на назначение ролей
        if not RolePermissionChecker.user_has_team_permission(
            self.user, self.team, 'can_assign_roles'
        ):
            raise TeamPermissionDenied("У вас нет разрешения на назначение ролей")
        
        # Получаем участие пользователя
        try:
            membership = TeamMembership.objects.get(
                team=self.team,
                user=member_user,
                is_active=True
            )
        except TeamMembership.DoesNotExist:
            raise ValidationError(f"Пользователь {member_user.username} не является активным участником команды")
        
        try:
            with transaction.atomic():
                # Получаем текущие и новые роли
                current_roles = set(membership.roles.all())
                new_role_objects = set(self._resolve_roles(roles))
                
                # Определяем роли для добавления и удаления
                roles_to_add = new_role_objects - current_roles
                roles_to_remove = current_roles - new_role_objects
                
                # Удаляем роли
                for role in roles_to_remove:
                    membership.remove_role(role, admin_user=self.user)
                
                # Добавляем роли
                for role in roles_to_add:
                    membership.add_role(role, admin_user=self.user)
                
                # Возвращаем обновленную информацию
                updated_roles = list(new_role_objects)
                return {
                    'user_id': member_user.id,
                    'username': member_user.username,
                    'roles': [{'id': role.id, 'name': role.name} for role in updated_roles],
                    'role_names': [role.name for role in updated_roles]
                }
                
        except Exception as e:
            raise
    
    def search_potential_members(self, query, limit=10):
        """Поиск пользователей для приглашения в команду."""
        if not query or len(query.strip()) < 2:
            raise ValidationError("Минимум 2 символа для поиска")
        
        query = query.strip()
        
        try:
            # Получаем ID уже добавленных активных участников
            existing_member_ids = TeamMembership.objects.filter(
                team=self.team,
                is_active=True
            ).values_list('user_id', flat=True)
            
            # Выполняем поиск пользователей с оптимизацией
            users = User.objects.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(display_name__icontains=query)
            ).exclude(
                id__in=existing_member_ids
            ).exclude(
                id=self.user.id  # Исключаем текущего пользователя
            ).only('id', 'username', 'display_name', 'email', 'avatar')[:limit]
            
            # Формируем результаты поиска
            results = []
            for found_user in users:
                user_data = {
                    'id': found_user.id,
                    'username': found_user.username,
                    'display_name': getattr(found_user, 'display_name', '') or found_user.username,
                    'email': found_user.email
                }
                
                # Добавляем аватар если есть
                if hasattr(found_user, 'avatar') and found_user.avatar:
                    user_data['avatar_url'] = found_user.avatar.url
                
                results.append(user_data)
            
            return results
            
        except Exception as e:
            raise
    
    def _resolve_roles(self, roles):
        """Преобразовать ID ролей в объекты Role."""
        if not roles:
            return []
        
        role_objects = []
        for role in roles:
            if isinstance(role, Role):
                role_objects.append(role)
            elif isinstance(role, (int, str)):
                try:
                    role_obj = Role.objects.get(pk=int(role))
                    role_objects.append(role_obj)
                except (Role.DoesNotExist, ValueError):
                    raise ValueError(f"Роль с ID {role} не найдена")
            else:
                raise ValueError(f"Некорректный тип роли: {type(role)}")
        
        return role_objects