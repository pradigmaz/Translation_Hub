# teams/admin.py

from django.contrib import admin
from django.contrib import messages
from django.db import models
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

# Импортируются все модели из файла models.py этого приложения.
from .models import Role, Team, TeamMembership, TeamStatus
from .utils import deactivate_team, reactivate_team, disband_team

# Расширенная регистрация модели Role с кастомным админом
# НЕ используем @admin.register - регистрация в utils/admin_site.py
class RoleAdmin(admin.ModelAdmin):
    """Расширенный административный интерфейс для управления ролями"""
    
    list_display = (
        'name', 
        'description_short', 
        'permission_count', 
        'usage_count', 
        'is_default', 
        'created_at'
    )
    list_filter = ('is_default', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('permissions',)
    readonly_fields = ('created_at', 'updated_at', 'usage_count_display')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'is_default')
        }),
        ('Разрешения', {
            'fields': ('permissions',),
            'classes': ('wide',),
            'description': 'Выберите разрешения, которые будут назначены этой роли'
        }),
        ('Статистика и метаданные', {
            'fields': ('usage_count_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    ordering = ('name',)
    actions = ['create_default_roles']
    
    def get_urls(self):
        """Добавляем custom URL для создания стандартных ролей"""
        print("RoleAdmin.get_urls() called!")
        urls = super().get_urls()
        custom_urls = [
            path(
                'create-defaults/',
                self.admin_site.admin_view(self.create_defaults_view),
                name='teams_role_create_defaults',
            ),
        ]
        print(f"Custom URLs: {custom_urls}")
        result = custom_urls + urls
        print(f"Total URLs count: {len(result)}")
        return result
    
    def create_defaults_view(self, request):
        """View для создания стандартных ролей"""
        from django.db import transaction
        print("=" * 80)
        print("CREATE_DEFAULTS_VIEW CALLED!")
        print(f"Request path: {request.path}")
        print(f"Request method: {request.method}")
        print("=" * 80)
        
        try:
            with transaction.atomic():
                result = Role.ensure_default_roles_exist()
                print(f"Result: {result}")
            
            created_count = len(result.get('created', []))
            updated_count = len(result.get('updated', []))
            errors = result.get('errors', [])
            
            if created_count > 0:
                created_names = ', '.join(result['created'])
                messages.success(
                    request,
                    f'✓ Создано ролей: {created_count} ({created_names})'
                )
            
            if updated_count > 0:
                updated_names = ', '.join(result['updated'])
                messages.info(
                    request,
                    f'ℹ Обновлено ролей: {updated_count} ({updated_names})'
                )
            
            if created_count == 0 and updated_count == 0 and not errors:
                messages.info(
                    request,
                    '✓ Все стандартные роли уже существуют и актуальны'
                )
            
            if errors:
                for error in errors:
                    messages.error(request, error)
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            messages.error(
                request,
                f'✗ Ошибка при создании ролей: {str(e)}'
            )
        
        changelist_url = reverse('admin:teams_role_changelist')
        print(f"Redirecting to: {changelist_url}")
        return HttpResponseRedirect(changelist_url)
    
    def changelist_view(self, request, extra_context=None):
        """Добавляем кнопку создания стандартных ролей в список"""
        extra_context = extra_context or {}
        extra_context['show_create_defaults_button'] = True
        return super().changelist_view(request, extra_context=extra_context)
    
    def description_short(self, obj):
        """Сокращенное описание роли для списка"""
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    description_short.short_description = _("Описание")
    
    def permission_count(self, obj):
        """Отображение количества разрешений у роли"""
        count = obj.get_permission_count()
        if count == 0:
            return format_html('<span style="color: #dc3545;">0 разрешений</span>')
        elif count <= 3:
            return format_html('<span style="color: #ffc107;">{} разрешений</span>', count)
        else:
            return format_html('<span style="color: #28a745;">{} разрешений</span>', count)
    permission_count.short_description = _("Разрешения")
    permission_count.admin_order_field = 'permissions__count'
    
    def usage_count(self, obj):
        """Отображение количества использований роли"""
        count = obj.get_usage_count()
        if count == 0:
            return format_html('<span style="color: #6c757d;">Не используется</span>')
        else:
            return format_html(
                '<span style="color: #007cba; font-weight: bold;">{}</span>',
                ngettext(
                    "%(count)d участник",
                    "%(count)d участников",
                    count
                ) % {'count': count}
            )
    usage_count.short_description = _("Использование")
    
    def usage_count_display(self, obj):
        """Детальное отображение использования роли для формы редактирования"""
        count = obj.get_usage_count()
        if count == 0:
            return "Роль не назначена ни одному участнику"
        
        # Получаем список команд, где используется роль
        from django.db.models import Count
        teams_with_role = Team.objects.filter(
            teammembership__roles=obj
        ).annotate(
            member_count=Count('teammembership__roles', filter=models.Q(teammembership__roles=obj))
        ).distinct()
        
        result = f"Роль назначена {count} участникам в {teams_with_role.count()} командах:\n"
        for team in teams_with_role[:5]:  # Показываем первые 5 команд
            result += f"• {team.name} ({team.member_count} участников)\n"
        
        if teams_with_role.count() > 5:
            result += f"... и еще {teams_with_role.count() - 5} команд"
            
        return result
    usage_count_display.short_description = _("Детали использования")
    
    def get_queryset(self, request):
        """Оптимизируем запросы для списка ролей"""
        return super().get_queryset(request).prefetch_related('permissions')
    
    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление стандартных ролей"""
        if obj and obj.is_default:
            return False
        return super().has_delete_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        """Дополнительная логика при сохранении роли"""
        # Устанавливаем пользователя для аудита
        obj._audit_user = request.user
        
        super().save_model(request, obj, form, change)
        

    
    def delete_model(self, request, obj):
        """Дополнительная логика при удалении роли"""
        # Устанавливаем пользователя для аудита
        obj._audit_user = request.user
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """Дополнительная логика при массовом удалении ролей"""
        for obj in queryset:
            obj._audit_user = request.user
        super().delete_queryset(request, queryset)
    
    @admin.action(description='Создать стандартные роли')
    def create_default_roles(self, request, queryset):
        """Создает стандартные роли системы"""
        try:
            result = Role.ensure_default_roles_exist()
            
            created_count = len(result.get('created', []))
            updated_count = len(result.get('updated', []))
            errors = result.get('errors', [])
            
            if created_count > 0:
                created_names = ', '.join(result['created'])
                messages.success(
                    request,
                    f'Создано ролей: {created_count} ({created_names})'
                )
            
            if updated_count > 0:
                updated_names = ', '.join(result['updated'])
                messages.info(
                    request,
                    f'Обновлено ролей: {updated_count} ({updated_names})'
                )
            
            if created_count == 0 and updated_count == 0 and not errors:
                messages.info(
                    request,
                    'Все стандартные роли уже существуют и актуальны'
                )
            
            if errors:
                for error in errors:
                    messages.error(request, error)
                
        except Exception as e:
            messages.error(
                request,
                f'Ошибка при создании ролей: {str(e)}'
            )
        for obj in queryset:
            obj._audit_user = request.user
        super().delete_queryset(request, queryset)


# Этот класс описывает "встраиваемый" редактор.
# Он позволит управлять участниками (TeamMembership) прямо со страницы команды (Team).
class TeamMembershipInline(admin.TabularInline):
    # Указывается, что этот редактор предназначен для модели TeamMembership.
    model = TeamMembership
    # Убираем пустые поля для добавления участников
    extra = 0
    # Для поля 'user' будет использоваться удобный виджет с поиском,
    # а не гигантский выпадающий список.
    # autocomplete_fields = ["user"]  # Временно отключено
    
    def get_queryset(self, request):
        """Показываем только активных участников команды"""
        return super().get_queryset(request).filter(is_active=True)


# НЕ используем @admin.register - регистрация в utils/admin_site.py
class TeamAdmin(admin.ModelAdmin):
    # Определяет, какие поля модели Team будут отображаться в виде колонок
    # в общем списке команд.
    list_display = ("name", "creator", "status_display", "member_count", "created_at", "delete_team_button")
    # Добавляет поле поиска, которое будет искать по названию команды.
    search_fields = ("name", "creator__username")
    # Добавляем фильтры по статусу и дате создания
    list_filter = ("status", "created_at", "updated_at")
    # Подключает встраиваемый редактор. Теперь на странице редактирования
    # одной команды появится таблица для управления ее участниками.
    inlines = (TeamMembershipInline,)
    # Добавляем кастомные действия для удаления и управления статусом
    actions = [
        "delete_selected_teams_with_confirmation",
        "deactivate_selected_teams",
        "reactivate_selected_teams", 
        "disband_selected_teams"
    ]

    def get_urls(self):
        """Добавляем кастомные URL для подтверждения удаления"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:team_id>/delete-confirm/",
                self.admin_site.admin_view(self.delete_team_confirm_view),
                name="teams_team_delete_confirm",
            ),
        ]
        return custom_urls + urls

    def status_display(self, obj):
        """Отображение статуса команды с цветовой индикацией"""
        status_colors = {
            TeamStatus.ACTIVE: '#28a745',    # Bootstrap success green
            TeamStatus.INACTIVE: '#ffc107',  # Bootstrap warning yellow
            TeamStatus.DISBANDED: '#dc3545'  # Bootstrap danger red
        }
        status_icons = {
            TeamStatus.ACTIVE: '✓',
            TeamStatus.INACTIVE: '⏸',
            TeamStatus.DISBANDED: '✗'
        }
        
        color = status_colors.get(obj.status, '#6c757d')
        icon = status_icons.get(obj.status, '?')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            icon,
            obj.get_status_display()
        )
    status_display.short_description = _("Статус")
    status_display.admin_order_field = 'status'

    def member_count(self, obj):
        """Показывает количество участников в команде"""
        active_count = obj.get_active_members_count()
        total_count = obj.members.count()
        
        if obj.status == TeamStatus.ACTIVE:
            return ngettext(
                "%(count)d участник",
                "%(count)d участников", 
                active_count
            ) % {'count': active_count}
        else:
            return format_html(
                '{} <small style="color: #6c757d;">(всего: {})</small>',
                ngettext(
                    "%(count)d участник",
                    "%(count)d участников", 
                    active_count
                ) % {'count': active_count},
                total_count
            )

    member_count.short_description = _("Участники")

    def delete_team_button(self, obj):
        """Добавляет кнопку удаления с подтверждением для каждой команды"""
        url = reverse("admin:teams_team_delete_confirm", args=[obj.pk])
        return format_html(
            '<a class="button delete-team-btn" href="{}" '
            'style="background-color: #dc3545; color: white; '
            'padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px; '
            'border: 1px solid #dc3545; display: inline-block;">'
            '{}</a>'
            '<style>'
            '.delete-team-btn:hover {{ '
            'background-color: #c82333 !important; '
            'border-color: #bd2130 !important; '
            'color: white !important; '
            'text-decoration: none !important; '
            '}}'
            '</style>',
            url,
            _("Удалить"),
        )

    delete_team_button.short_description = _("Действия")
    delete_team_button.allow_tags = True

    def deactivate_selected_teams(self, request, queryset):
        """Массовая приостановка команд"""
        if not request.user.is_superuser:
            self.message_user(request, _("Недостаточно прав для выполнения этого действия"), level=messages.ERROR)
            return
            
        count = 0
        errors = []
        
        for team in queryset.filter(status=TeamStatus.ACTIVE):
            try:
                deactivate_team(team, request.user, "Массовая приостановка через админку")
                count += 1
            except Exception as e:
                errors.append(f"{team.name}: {str(e)}")
        
        if count > 0:
            self.message_user(
                request, 
                ngettext(
                    "Приостановлена %(count)d команда",
                    "Приостановлено %(count)d команд",
                    count
                ) % {'count': count}
            )
        
        if errors:
            self.message_user(
                request, 
                _("Ошибки при приостановке: ") + "; ".join(errors), 
                level=messages.WARNING
            )
    
    deactivate_selected_teams.short_description = _("Приостановить выбранные команды")

    def reactivate_selected_teams(self, request, queryset):
        """Массовое возобновление команд"""
        if not request.user.is_superuser:
            self.message_user(request, _("Недостаточно прав для выполнения этого действия"), level=messages.ERROR)
            return
            
        count = 0
        errors = []
        
        for team in queryset.filter(status=TeamStatus.INACTIVE):
            try:
                reactivate_team(team, request.user, "Массовое возобновление через админку")
                count += 1
            except Exception as e:
                errors.append(f"{team.name}: {str(e)}")
        
        if count > 0:
            self.message_user(
                request, 
                ngettext(
                    "Возобновлена %(count)d команда",
                    "Возобновлено %(count)d команд",
                    count
                ) % {'count': count}
            )
        
        if errors:
            self.message_user(
                request, 
                _("Ошибки при возобновлении: ") + "; ".join(errors), 
                level=messages.WARNING
            )
    
    reactivate_selected_teams.short_description = _("Возобновить выбранные команды")

    def disband_selected_teams(self, request, queryset):
        """Массовый роспуск команд"""
        if not request.user.is_superuser:
            self.message_user(request, _("Недостаточно прав для выполнения этого действия"), level=messages.ERROR)
            return
            
        count = 0
        errors = []
        
        for team in queryset.exclude(status=TeamStatus.DISBANDED):
            try:
                disband_team(team, request.user, "Массовый роспуск через админку")
                count += 1
            except Exception as e:
                errors.append(f"{team.name}: {str(e)}")
        
        if count > 0:
            self.message_user(
                request, 
                ngettext(
                    "Распущена %(count)d команда",
                    "Распущено %(count)d команд",
                    count
                ) % {'count': count}
            )
        
        if errors:
            self.message_user(
                request, 
                _("Ошибки при роспуске: ") + "; ".join(errors), 
                level=messages.WARNING
            )
    
    disband_selected_teams.short_description = _("Распустить выбранные команды")

    def delete_team_confirm_view(self, request, team_id):
        """Страница подтверждения удаления команды"""
        try:
            team = Team.objects.get(pk=team_id)
        except Team.DoesNotExist:
            return HttpResponseRedirect(reverse("admin:teams_team_changelist"))

        if request.method == "POST":
            if "confirm" in request.POST:
                # Получаем информацию о команде для логирования
                team_name = team.name
                creator_name = team.creator.username
                member_count = team.get_active_members_count()

                # Удаляем команду
                team.delete()
                return HttpResponseRedirect(reverse("admin:teams_team_changelist"))
            else:
                # Пользователь отменил удаление
                return HttpResponseRedirect(reverse("admin:teams_team_changelist"))

        # Получаем дополнительную информацию о команде для отображения
        context = {
            "team": team,
            "member_count": team.get_active_members_count(),
            "active_member_count": team.members.filter(teammembership__is_active=True).count(),
            "memberships": TeamMembership.objects.filter(team=team)
            .select_related("user")
            .prefetch_related("roles"),
            "recent_status_changes": team.status_history.select_related('changed_by')[:5],
            "title": _('Подтверждение удаления команды "%(team_name)s"') % {'team_name': team.name},
            "opts": self.model._meta,
            "has_view_permission": self.has_view_permission(request),
        }

        return render(request, "admin/teams/team/delete_confirmation.html", context)

    def delete_selected_teams_with_confirmation(self, request, queryset):
        """Массовое удаление команд с подтверждением"""
        if request.POST.get("post"):
            # Подтверждение получено, удаляем команды
            count = queryset.count()
            team_names = list(queryset.values_list("name", flat=True))
            queryset.delete()
            return HttpResponseRedirect(request.get_full_path())

        # Показываем страницу подтверждения
        context = {
            "teams": queryset,
            "team_count": queryset.count(),
            "total_members": sum(team.get_active_members_count() for team in queryset),
            "title": _("Подтверждение удаления команд"),
            "opts": self.model._meta,
            "action_checkbox_name": admin.ACTION_CHECKBOX_NAME,
            "queryset": queryset,
        }

        return render(
            request, "admin/teams/team/delete_selected_confirmation.html", context
        )

    delete_selected_teams_with_confirmation.short_description = _(
        "Удалить выбранные команды (с подтверждением)"
    )

    def has_delete_permission(self, request, obj=None):
        """Разрешаем удаление только через наши кастомные методы"""
        return request.user.is_superuser


# НЕ используем @admin.register - регистрация в utils/admin_site.py
class TeamMembershipAdmin(admin.ModelAdmin):
    """Улучшенный административный интерфейс для управления участниками команд"""
    
    # Определяет колонки в общем списке всех "членств в командах".
    list_display = ("user", "team", "roles_display", "permission_count_display", "is_active_display", "joined_at")
    # Добавляет боковую панель для фильтрации по команде, активности и ролям.
    list_filter = ("team", "is_active", "joined_at", "roles", "team__status")
    # Включает виджет с поиском для полей 'user' и 'team'.
    # autocomplete_fields = ["user", "team"]  # Временно отключено
    # Добавляем поиск по пользователю и команде
    search_fields = ("user__username", "user__first_name", "user__last_name", "team__name", "roles__name")
    # Сортировка по умолчанию
    ordering = ("-joined_at",)
    # Добавляем filter_horizontal для удобного управления ролями
    filter_horizontal = ('roles',)
    
    # Группировка полей в форме редактирования
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'team', 'is_active')
        }),
        ('Роли и разрешения', {
            'fields': ('roles',),
            'classes': ('wide',),
            'description': 'Выберите роли для участника команды. Разрешения будут объединены от всех назначенных ролей.'
        }),
        ('Метаданные', {
            'fields': ('joined_at', 'effective_permissions_display'),
            'classes': ('collapse',)
        })
    )
    
    # Поля только для чтения
    readonly_fields = ('joined_at', 'effective_permissions_display')
    
    # Массовые действия
    actions = [
        'assign_editor_role', 'assign_translator_role', 
        'assign_cleaner_role', 'assign_typesetter_role',
        'remove_all_roles', 'activate_selected', 'deactivate_selected'
    ]

    def roles_display(self, obj):
        """Красивое отображение ролей участника"""
        roles = obj.roles.all()
        if not roles:
            return format_html('<span style="color: #6c757d; font-style: italic;">Роли не назначены</span>')
        
        role_badges = []
        for role in roles:
            # Разные цвета для разных типов ролей
            if role.name == "Руководитель":
                color = "#dc3545"  # Красный для руководителя
                icon = "👑"
            elif role.name == "Редактор":
                color = "#007cba"  # Синий для редактора
                icon = "✏️"
            elif role.name == "Переводчик":
                color = "#17a2b8"  # Бирюзовый для переводчика
                icon = "🌐"
            elif role.name == "Клинер":
                color = "#28a745"  # Зеленый для клинера
                icon = "🧹"
            elif role.name == "Тайпер":
                color = "#ffc107"  # Желтый для тайпера
                icon = "⌨️"
            elif role.is_default:
                color = "#6f42c1"  # Фиолетовый для других стандартных ролей
                icon = "⭐"
            else:
                color = "#6c757d"  # Серый для кастомных ролей
                icon = "🔧"
                
            role_badges.append(
                f'<span style="background-color: {color}; color: white; '
                f'padding: 3px 8px; border-radius: 12px; font-size: 11px; '
                f'margin-right: 4px; margin-bottom: 2px; display: inline-block; '
                f'font-weight: 500; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">'
                f'{icon} {role.name}</span>'
            )
        
        return format_html(''.join(role_badges))
    roles_display.short_description = _("Роли")

    def permission_count_display(self, obj):
        """Отображение количества эффективных разрешений"""
        permissions = set()
        for role in obj.roles.all():
            permissions.update(role.get_permission_names())
        
        count = len(permissions)
        if count == 0:
            return format_html('<span style="color: #dc3545; font-size: 11px;">0 разрешений</span>')
        elif count <= 5:
            return format_html('<span style="color: #ffc107; font-weight: bold; font-size: 11px;">{}</span>', count)
        else:
            return format_html('<span style="color: #28a745; font-weight: bold; font-size: 11px;">{}</span>', count)
    permission_count_display.short_description = _("Разрешения")

    def effective_permissions_display(self, obj):
        """Детальное отображение эффективных разрешений для формы редактирования"""
        if not obj.pk:
            return "Сохраните участника для просмотра разрешений"
            
        permissions = set()
        role_permissions = {}
        
        for role in obj.roles.all():
            role_perms = role.get_permission_names()
            role_permissions[role.name] = role_perms
            permissions.update(role_perms)
        
        if not permissions:
            return "У участника нет назначенных разрешений"
        
        result = f"Всего уникальных разрешений: {len(permissions)}\n\n"
        
        for role_name, perms in role_permissions.items():
            result += f"Роль '{role_name}' ({len(perms)} разрешений):\n"
            for perm in sorted(perms):
                result += f"  • {perm}\n"
            result += "\n"
        
        return result
    effective_permissions_display.short_description = _("Эффективные разрешения")

    def is_active_display(self, obj):
        """Отображение статуса активности участника"""
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Активен</span>'
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">✗ Неактивен</span>'
            )
    is_active_display.short_description = _("Статус")
    is_active_display.admin_order_field = 'is_active'
    
    # Массовые действия для назначения конкретных ролей

    def assign_editor_role(self, request, queryset):
        """Массовое назначение роли Редактор"""
        try:
            editor_role = Role.objects.get(name="Редактор")
            count = 0
            for membership in queryset:
                if editor_role not in membership.roles.all():
                    membership.add_role(editor_role, request.user)
                    count += 1
            
            self.message_user(
                request,
                ngettext(
                    "Роль 'Редактор' назначена %(count)d участнику",
                    "Роль 'Редактор' назначена %(count)d участникам",
                    count
                ) % {'count': count}
            )
        except Role.DoesNotExist:
            self.message_user(request, "Роль 'Редактор' не найдена в системе", level=messages.ERROR)
    assign_editor_role.short_description = _("Назначить роль 'Редактор'")
    
    def assign_translator_role(self, request, queryset):
        """Массовое назначение роли Переводчик"""
        try:
            translator_role = Role.objects.get(name="Переводчик")
            count = 0
            for membership in queryset:
                if translator_role not in membership.roles.all():
                    membership.add_role(translator_role, request.user)
                    count += 1
            
            self.message_user(
                request,
                ngettext(
                    "Роль 'Переводчик' назначена %(count)d участнику",
                    "Роль 'Переводчик' назначена %(count)d участникам",
                    count
                ) % {'count': count}
            )
        except Role.DoesNotExist:
            self.message_user(request, "Роль 'Переводчик' не найдена в системе", level=messages.ERROR)
    assign_translator_role.short_description = _("Назначить роль 'Переводчик'")
    
    def assign_cleaner_role(self, request, queryset):
        """Массовое назначение роли Клинер"""
        try:
            cleaner_role = Role.objects.get(name="Клинер")
            count = 0
            for membership in queryset:
                if cleaner_role not in membership.roles.all():
                    membership.add_role(cleaner_role, request.user)
                    count += 1
            
            self.message_user(
                request,
                ngettext(
                    "Роль 'Клинер' назначена %(count)d участнику",
                    "Роль 'Клинер' назначена %(count)d участникам",
                    count
                ) % {'count': count}
            )
        except Role.DoesNotExist:
            self.message_user(request, "Роль 'Клинер' не найдена в системе", level=messages.ERROR)
    assign_cleaner_role.short_description = _("Назначить роль 'Клинер'")
    
    def assign_typesetter_role(self, request, queryset):
        """Массовое назначение роли Тайпер"""
        try:
            typesetter_role = Role.objects.get(name="Тайпер")
            count = 0
            for membership in queryset:
                if typesetter_role not in membership.roles.all():
                    membership.add_role(typesetter_role, request.user)
                    count += 1
            
            self.message_user(
                request,
                ngettext(
                    "Роль 'Тайпер' назначена %(count)d участнику",
                    "Роль 'Тайпер' назначена %(count)d участникам",
                    count
                ) % {'count': count}
            )
        except Role.DoesNotExist:
            self.message_user(request, "Роль 'Тайпер' не найдена в системе", level=messages.ERROR)
    assign_typesetter_role.short_description = _("Назначить роль 'Тайпер'")
    
    def remove_all_roles(self, request, queryset):
        """Массовое удаление всех ролей у участников"""
        count = 0
        for membership in queryset:
            roles_count = membership.roles.count()
            if roles_count > 0:
                membership.roles.clear()
                count += 1
        
        self.message_user(
            request,
            ngettext(
                "Все роли удалены у %(count)d участника",
                "Все роли удалены у %(count)d участников",
                count
            ) % {'count': count}
        )
    remove_all_roles.short_description = _("Удалить все роли у выбранных участников")
    
    def activate_selected(self, request, queryset):
        """Активация выбранных участников"""
        count = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(
            request,
            ngettext(
                "Активирован %(count)d участник",
                "Активировано %(count)d участников",
                count
            ) % {'count': count}
        )
    activate_selected.short_description = _("Активировать выбранных участников")
    
    def deactivate_selected(self, request, queryset):
        """Деактивация выбранных участников"""
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(
            request,
            ngettext(
                "Деактивирован %(count)d участник",
                "Деактивировано %(count)d участников",
                count
            ) % {'count': count}
        )
    deactivate_selected.short_description = _("Деактивировать выбранных участников")
    
    def get_queryset(self, request):
        """Оптимизируем запросы для списка участников"""
        return super().get_queryset(request).select_related('user', 'team').prefetch_related('roles', 'roles__permissions')
    
    def save_model(self, request, obj, form, change):
        """Дополнительная логика при сохранении участника команды"""
        super().save_model(request, obj, form, change)