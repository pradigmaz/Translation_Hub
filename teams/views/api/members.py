"""AJAX API для управления участниками команд."""

import json
from django.views.generic import View
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from ...mixins import TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, PerformanceMonitoringMixin
from ...components import TeamMemberManager
from ...models import Role
from ...exceptions import TeamPermissionDenied, TeamNotFoundError

User = get_user_model()


class TeamMemberListAPI(
    PerformanceMonitoringMixin, TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View
):
    # API для получения списка участников команды.

    team_url_kwarg = "team_id"

    def get(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)

            # Используем TeamMemberManager для получения участников
            member_manager = TeamMemberManager(team, request.user)

            # Получаем параметры запроса
            include_inactive = (
                request.GET.get("include_inactive", "false").lower() == "true"
            )

            # Получаем участников
            members_data = member_manager.get_members_with_roles(
                include_inactive=include_inactive
            )

            # Получаем разрешения пользователя для команды
            from ...permission_checker import RolePermissionChecker
            permissions = {
                'can_assign_roles': RolePermissionChecker.user_has_team_permission(
                    request.user, team, 'can_assign_roles'
                ),
                'can_remove_members': RolePermissionChecker.user_has_team_permission(
                    request.user, team, 'can_remove_members'
                ),
                'can_invite_members': RolePermissionChecker.user_has_team_permission(
                    request.user, team, 'can_invite_members'
                ),
                'can_manage_team': RolePermissionChecker.user_has_team_permission(
                    request.user, team, 'can_manage_team'
                ),
            }

            return self.ajax_success(
                data={
                    "members": members_data,
                    "total_count": len(members_data),
                    "team_id": team.id,
                    "team_name": team.name,
                    "permissions": permissions,
                },
                message=f"Загружено {len(members_data)} участников",
            )

        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context="TeamMemberListAPI.get")
        except Exception as e:
            return self.handle_ajax_error(e, context="TeamMemberListAPI.get")


@method_decorator(csrf_exempt, name="dispatch")
class TeamMemberAddAPI(PerformanceMonitoringMixin, TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View):
    """API для добавления участника в команду."""

    team_permission_required = "can_invite_members"
    team_url_kwarg = "team_id"

    def post(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)

            # Парсим JSON данные
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return self.ajax_error(
                    message="Некорректный формат JSON данных", status=400
                )

            # Валидируем обязательные поля
            user_id = data.get("user_id")
            role_ids = data.get("role_ids", [])

            if not user_id:
                return self.ajax_error(message="Не указан ID пользователя", status=400)

            # Получаем пользователя
            try:
                new_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return self.ajax_error(message="Пользователь не найден", status=404)

            # Используем TeamMemberManager для добавления участника
            member_manager = TeamMemberManager(team, request.user)

            # Добавляем участника
            member_data = member_manager.add_member(new_user, role_ids)

            return self.ajax_success(
                data={"member": member_data, "team_id": team.id},
                message=f"Пользователь {new_user.username} добавлен в команду",
            )

        except ValidationError as e:
            return self.ajax_error(message=str(e), status=400)
        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context="TeamMemberAddAPI.post")
        except Exception as e:
            return self.handle_ajax_error(e, context="TeamMemberAddAPI.post")


@method_decorator(csrf_exempt, name="dispatch")
class TeamMemberRemoveAPI(
    PerformanceMonitoringMixin, TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View
):
    # API для удаления участника из команды.

    team_permission_required = "can_remove_members"
    team_url_kwarg = "team_id"

    def post(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)

            # Парсим JSON данные
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return self.ajax_error(
                    message="Некорректный формат JSON данных", status=400
                )

            # Валидируем обязательные поля
            user_id = data.get("user_id")

            if not user_id:
                return self.ajax_error(message="Не указан ID пользователя", status=400)

            # Получаем пользователя
            try:
                member_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return self.ajax_error(message="Пользователь не найден", status=404)

            # Используем TeamMemberManager для удаления участника
            member_manager = TeamMemberManager(team, request.user)

            # Удаляем участника
            success = member_manager.remove_member(member_user)

            if success:

                return self.ajax_success(
                    data={"removed_user_id": user_id, "team_id": team.id},
                    message=f"Пользователь {member_user.username} удален из команды",
                )
            else:
                return self.ajax_error(
                    message="Не удалось удалить участника", status=500
                )

        except ValidationError as e:
            return self.ajax_error(message=str(e), status=400)
        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context="TeamMemberRemoveAPI.post")
        except Exception as e:
            return self.handle_ajax_error(e, context="TeamMemberRemoveAPI.post")


@method_decorator(csrf_exempt, name="dispatch")
class TeamMemberRoleUpdateAPI(
    PerformanceMonitoringMixin, TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View
):
    # API для изменения ролей участника команды.

    team_permission_required = "can_assign_roles"
    team_url_kwarg = "team_id"

    def post(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)

            # Парсим JSON данные
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return self.ajax_error(
                    message="Некорректный формат JSON данных", status=400
                )

            # Валидируем обязательные поля
            user_id = data.get("user_id")
            role_ids = data.get("role_ids", [])

            if not user_id:
                return self.ajax_error(message="Не указан ID пользователя", status=400)

            # Получаем пользователя
            try:
                member_user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return self.ajax_error(message="Пользователь не найден", status=404)

            # Используем TeamMemberManager для обновления ролей
            member_manager = TeamMemberManager(team, request.user)

            # Обновляем роли участника
            updated_member = member_manager.update_member_roles(member_user, role_ids)

            return self.ajax_success(
                data={"member": updated_member, "team_id": team.id},
                message=f"Роли пользователя {member_user.username} обновлены",
            )

        except ValidationError as e:
            return self.ajax_error(message=str(e), status=400)
        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context="TeamMemberRoleUpdateAPI.post")
        except Exception as e:
            return self.handle_ajax_error(e, context="TeamMemberRoleUpdateAPI.post")


@method_decorator(csrf_exempt, name="dispatch")
class TeamMemberBulkUpdateAPI(
    PerformanceMonitoringMixin, TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View
):
    # API для массового обновления участников команды.

    team_url_kwarg = "team_id"

    def post(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)

            # Парсим JSON данные
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return self.ajax_error(
                    message="Некорректный формат JSON данных", status=400
                )

            operations = data.get("operations", [])
            if not operations:
                return self.ajax_error(
                    message="Не указаны операции для выполнения", status=400
                )

            # Используем TeamMemberManager
            member_manager = TeamMemberManager(team, request.user)

            results = []
            errors = []

            # Выполняем операции
            for i, operation in enumerate(operations):
                try:
                    op_type = operation.get("type")
                    user_id = operation.get("user_id")

                    if not op_type or not user_id:
                        errors.append(
                            f"Операция {i+1}: отсутствует тип операции или ID пользователя"
                        )
                        continue

                    # Получаем пользователя
                    try:
                        user = User.objects.get(id=user_id)
                    except User.DoesNotExist:
                        errors.append(
                            f"Операция {i+1}: пользователь с ID {user_id} не найден"
                        )
                        continue

                    # Выполняем операцию
                    if op_type == "add":
                        role_ids = operation.get("role_ids", [])
                        result = member_manager.add_member(user, role_ids)
                        results.append(
                            {
                                "operation": "add",
                                "user_id": user_id,
                                "success": True,
                                "data": result,
                            }
                        )

                    elif op_type == "remove":
                        success = member_manager.remove_member(user)
                        results.append(
                            {
                                "operation": "remove",
                                "user_id": user_id,
                                "success": success,
                            }
                        )

                    elif op_type == "update_roles":
                        role_ids = operation.get("role_ids", [])
                        result = member_manager.update_member_roles(user, role_ids)
                        results.append(
                            {
                                "operation": "update_roles",
                                "user_id": user_id,
                                "success": True,
                                "data": result,
                            }
                        )

                    else:
                        errors.append(
                            f"Операция {i+1}: неизвестный тип операции '{op_type}'"
                        )

                except Exception as e:
                    errors.append(f"Операция {i+1}: {str(e)}")

            # Формируем ответ
            response_data = {
                "results": results,
                "total_operations": len(operations),
                "successful_operations": len(results),
                "failed_operations": len(errors),
            }

            if errors:
                response_data["errors"] = errors

            message = f"Выполнено {len(results)} из {len(operations)} операций"
            if errors:
                message += f", {len(errors)} ошибок"

            return self.ajax_success(data=response_data, message=message)

        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context="TeamMemberBulkUpdateAPI.post")
        except Exception as e:
            return self.handle_ajax_error(e, context="TeamMemberBulkUpdateAPI.post")


@method_decorator(csrf_exempt, name="dispatch")
class TeamTransferLeadershipAPI(
    PerformanceMonitoringMixin, TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View
):
    # API для передачи лидерства команды.

    team_url_kwarg = "team_id"

    def post(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)

            # Проверяем, что текущий пользователь является создателем команды
            if team.creator != request.user:
                return self.ajax_error(
                    message="Только создатель команды может передать лидерство",
                    status=403
                )

            # Парсим JSON данные
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return self.ajax_error(
                    message="Некорректный формат JSON данных", status=400
                )

            # Валидируем обязательные поля
            new_leader_id = data.get("user_id")

            if not new_leader_id:
                return self.ajax_error(
                    message="Не указан ID нового лидера", status=400
                )

            # Получаем нового лидера
            try:
                new_leader = User.objects.get(id=new_leader_id)
            except User.DoesNotExist:
                return self.ajax_error(message="Пользователь не найден", status=404)

            # Проверяем, что новый лидер является активным участником команды
            from ...models import TeamMembership
            if not TeamMembership.objects.filter(
                team=team, user=new_leader, is_active=True
            ).exists():
                return self.ajax_error(
                    message="Новый лидер должен быть активным участником команды",
                    status=400
                )

            # Передаем лидерство
            try:
                team.transfer_leadership(new_leader, request.user)

                return self.ajax_success(
                    data={"new_leader_id": new_leader.id, "team_id": team.id},
                    message=f"Лидерство команды передано пользователю {new_leader.username}",
                )

            except Exception as e:
                return self.ajax_error(message=str(e), status=400)

        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context="TeamTransferLeadershipAPI.post")
        except Exception as e:
            return self.handle_ajax_error(e, context="TeamTransferLeadershipAPI.post")


class TeamRoleListAPI(
    PerformanceMonitoringMixin, TeamPermissionMixin, AjaxResponseMixin, AjaxRequiredMixin, View
):
    # API для получения списка доступных ролей команды.

    team_url_kwarg = "team_id"

    def get(self, request, team_id):
        try:
            # Получаем команду с проверкой доступа
            team = self.get_team_or_404(team_id)

            # Получаем все доступные роли
            roles = Role.objects.all().order_by('name')
            
            # Определяем иерархию ролей вручную
            role_hierarchy = {
                'Руководитель': 1,
                'Редактор': 2,
                'Переводчик': 3,
                'Клинер': 4,
                'Тайпер': 5
            }
            
            roles_data = []
            for role in roles:
                roles_data.append({
                    'id': role.id,
                    'name': role.name,
                    'description': role.description,
                    'level': role_hierarchy.get(role.name, 99),
                    'permissions': [perm.codename for perm in role.permissions.all()],
                    'color_class': self.get_role_color_class(role.name),
                    'icon_class': self.get_role_icon_class(role.name),
                })

            # Сортируем по иерархии
            roles_data.sort(key=lambda x: x['level'])

            # Получаем разрешения пользователя для команды
            from ...permission_checker import RolePermissionChecker
            permissions = {
                'canAssignRoles': RolePermissionChecker.user_has_team_permission(
                    request.user, team, 'can_assign_roles'
                ),
                'canRemoveRoles': RolePermissionChecker.user_has_team_permission(
                    request.user, team, 'can_assign_roles'  # Используем то же разрешение
                ),
                'canRemoveMembers': RolePermissionChecker.user_has_team_permission(
                    request.user, team, 'can_remove_members'
                ),
                'canInviteMembers': RolePermissionChecker.user_has_team_permission(
                    request.user, team, 'can_invite_members'
                ),
            }

            return self.ajax_success(
                data={
                    "roles": roles_data,
                    "total_count": len(roles_data),
                    "team_id": team.id,
                    "team_name": team.name,
                    "permissions": permissions,
                },
                message=f"Загружено {len(roles_data)} ролей",
            )

        except (TeamPermissionDenied, TeamNotFoundError) as e:
            return self.handle_ajax_error(e, context="TeamRoleListAPI.get")
        except Exception as e:
            return self.handle_ajax_error(e, context="TeamRoleListAPI.get")

    def get_role_color_class(self, role_name):
        """Получить CSS класс цвета для роли."""
        role_colors = {
            'Руководитель': 'text-bg-danger',
            'Редактор': 'text-bg-info',
            'Переводчик': 'text-bg-primary',
            'Клинер': 'text-bg-success',
            'Тайпер': 'text-bg-warning'
        }
        return role_colors.get(role_name, 'text-bg-secondary')

    def get_role_icon_class(self, role_name):
        """Получить CSS класс иконки для роли."""
        role_icons = {
            'Руководитель': 'fas fa-crown',
            'Редактор': 'fas fa-edit',
            'Переводчик': 'fas fa-language',
            'Клинер': 'fas fa-broom',
            'Тайпер': 'fas fa-keyboard'
        }
        return role_icons.get(role_name, 'fas fa-tag')
