# users/admin.py

# Импортируем сам Django admin, чтобы регистрировать модели.
from django.contrib import admin

# Импортируем UserAdmin - это готовый, мощный интерфейс от Django
# для управления пользователями (с поиском, фильтрами, управлением паролями).
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Импортируем нашу кастомную модель User из текущего приложения (users).
from django import forms
from django.core.exceptions import ValidationError
from .models import User


# UserAdminForm удален, так как display_name больше не используется


class CustomUserAdmin(BaseUserAdmin):
    """
    Кастомный админ для пользователей с возможностью удаления.
    """

    # Добавляем кастомные поля в список отображения
    list_display = BaseUserAdmin.list_display + (
        "user_status",
        "date_joined",
    )

    # Добавляем поля для поиска (важно для autocomplete_fields в других админках)
    search_fields = BaseUserAdmin.search_fields

    # Добавляем фильтры для удобного поиска заблокированных пользователей
    list_filter = BaseUserAdmin.list_filter + ("date_joined",)

    # Упрощенные fieldsets - убираем сложные права и ненужные поля
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Контактная информация", {"fields": ("email",)}),
        (
            "Дополнительная информация",
            {
                "fields": ("avatar",),
            },
        ),
        (
            "Статус аккаунта",
            {
                "fields": ("is_active", "date_joined", "last_login"),
                "description": 'Снимите галочку "Active" чтобы заблокировать пользователя',
            },
        ),
    )

    # Упрощенные поля для создания пользователя - без имени и фамилии
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
        (
            "Дополнительная информация",
            {
                "fields": ("email",),
            },
        ),
    )

    # Поля только для чтения
    readonly_fields = ("date_joined", "last_login")

    # Явно разрешаем все операции для суперпользователей
    def has_add_permission(self, request):
        """Разрешаем создание пользователей суперпользователям."""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Разрешаем изменение пользователей суперпользователям."""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Разрешаем удаление пользователей суперпользователям."""
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """Разрешаем просмотр пользователей суперпользователям."""
        return request.user.is_superuser

    # Простые действия - только бан/разбан и удаление
    actions = ["ban_users", "unban_users", "delete_selected_users"]

    def delete_selected_users(self, request, queryset):
        """
        Кастомное действие для удаления выбранных пользователей с очисткой файлов.
        """
        from django.db import connection

        count = queryset.count()
        usernames = [user.username for user in queryset]
        success_count = 0

        for user in queryset:
            try:
                user_id = user.id
                username = user.username

                # Очищаем связанные объекты
                self._cleanup_user_relations(user)

                # Очищаем файлы пользователя
                try:
                    from utils.file_system import FileCleanupManager

                    FileCleanupManager.cleanup_user_files(user_id)
                except Exception as e:
                    pass

                # Удаляем пользователя напрямую из базы
                with connection.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys = OFF")
                    cursor.execute("DELETE FROM users_user WHERE id = %s", [user_id])
                    cursor.execute("PRAGMA foreign_keys = ON")

                success_count += 1

            except Exception as e:
                logging.error(f"Ошибка при удалении пользователя {user.username}: {e}")

        if success_count == count:
            self.message_user(request, f"Успешно удалено пользователей: {success_count}")
        else:
            self.message_user(request, f"Удалено {success_count} из {count} пользователей", level="WARNING")

    delete_selected_users.short_description = (
        "Безопасно удалить выбранных пользователей"
    )

    def ban_users(self, request, queryset):
        """
        Массовый бан пользователей (деактивация).
        """
        count = queryset.filter(is_active=True).update(is_active=False)

        self.message_user(request, f"Заблокировано пользователей: {count}")

    ban_users.short_description = "🚫 Заблокировать выбранных пользователей (БАН)"

    def unban_users(self, request, queryset):
        """
        Массовый разбан пользователей (активация).
        """
        count = queryset.filter(is_active=False).update(is_active=True)

        self.message_user(request, f"Разблокировано пользователей: {count}")

    unban_users.short_description = "✅ Разблокировать выбранных пользователей (РАЗБАН)"

    def user_status(self, obj):
        """Простое отображение статуса пользователя"""
        from django.utils.html import format_html

        if not obj.is_active:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">🚫 ЗАБЛОКИРОВАН</span>'
            )
        else:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✅ АКТИВЕН</span>'
            )

    user_status.short_description = "Статус"
    user_status.admin_order_field = "is_active"

    def _cleanup_user_relations(self, user):
        """Очищает связанные с пользователем объекты."""

        # 1. Удаляем членство в командах
        try:
            from teams.models import TeamMembership

            TeamMembership.objects.filter(user=user).delete()
        except Exception as e:
            logging.warning(f"Не удалось удалить членства в командах: {e}")

        # 2. Удаляем глобальные роли
        try:
            from teams.models import UserRole

            UserRole.objects.filter(user=user).delete()
        except Exception as e:
            logging.warning(f"Не удалось удалить глобальные роли: {e}")

        # 3. Удаляем записи из базы знаний
        try:
            from glossary.models import GlossaryTerm

            GlossaryTerm.objects.filter(created_by=user).delete()
        except Exception as e:
            logging.warning(f"Не удалось удалить записи базы знаний: {e}")

        # 6. Обнуляем assignee в главах
        try:
            from projects.models import Chapter

            Chapter.objects.filter(assignee=user).update(assignee=None)
        except Exception as e:
            logging.warning(f"Не удалось обнулить назначения в главах: {e}")

    def save_model(self, request, obj, form, change):
        """Дополнительная проверка при сохранении через админ-панель"""
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            raise

    def get_actions(self, request):
        """Возвращаем доступные действия для суперпользователей."""
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            # Убираем все действия удаления для не-суперпользователей
            if "delete_selected" in actions:
                del actions["delete_selected"]
            if "delete_selected_users" in actions:
                del actions["delete_selected_users"]
        return actions


# Регистрируем модель с кастомным админом
admin.site.register(User, CustomUserAdmin)
