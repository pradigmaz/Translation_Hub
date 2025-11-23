from django.conf import settings
from django.db import models, transaction

class TeamStatus(models.TextChoices):
    """Возможные статусы команды"""
    ACTIVE = 'active', 'Активная'
    INACTIVE = 'inactive', 'Неактивная' 
    DISBANDED = 'disbanded', 'Распущена'


class TeamStatusChangeType(models.TextChoices):
    """Типы изменений статуса команды"""
    CREATED = 'created', 'Создана'
    DEACTIVATED = 'deactivated', 'Приостановлена'
    REACTIVATED = 'reactivated', 'Возобновлена'
    DISBANDED = 'disbanded', 'Распущена'


class Role(models.Model):
    """Модель для хранения возможных ролей (Переводчик, Клинер и т.д.)."""

    name = models.CharField(max_length=50, unique=True, verbose_name="Название роли")
    description = models.TextField(blank=True, verbose_name="Описание роли")
    permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='roles',
        verbose_name="Разрешения",
        help_text="Разрешения, назначенные этой роли"
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name="Стандартная роль",
        help_text="Является ли роль стандартной (создается автоматически)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создана")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлена")

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        ordering = ['name']
        permissions = [
            # Разрешения для команд
            ("can_manage_team", "Может управлять командой"),
            ("can_invite_members", "Может приглашать участников"),
            ("can_remove_members", "Может удалять участников"),
            ("can_assign_roles", "Может назначать роли"),
            ("can_change_team_status", "Может изменять статус команды"),
            
            # Разрешения для проектов
            ("can_create_project", "Может создавать проекты"),
            ("can_manage_project", "Может управлять проектами"),
            ("can_delete_project", "Может удалять проекты"),
            ("can_assign_chapters", "Может назначать главы"),
            
            # Разрешения для контента
            ("can_edit_content", "Может редактировать контент"),
            ("can_review_content", "Может рецензировать контент"),
            ("can_publish_content", "Может публиковать контент"),
        ]

    def get_permission_names(self):
        """Возвращает список названий разрешений"""
        return list(self.permissions.values_list('codename', flat=True))
        
    def has_permission(self, permission_codename):
        """Проверяет наличие конкретного разрешения"""
        return self.permissions.filter(codename=permission_codename).exists()
    
    def add_permission(self, permission_codename):
        """Добавляет разрешение к роли"""
        from django.contrib.auth.models import Permission
        try:
            permission = Permission.objects.get(codename=permission_codename)
            self.permissions.add(permission)
            return True
        except Permission.DoesNotExist:
            return False
    
    def remove_permission(self, permission_codename):
        """Удаляет разрешение из роли"""
        from django.contrib.auth.models import Permission
        try:
            permission = Permission.objects.get(codename=permission_codename)
            self.permissions.remove(permission)
            return True
        except Permission.DoesNotExist:
            return False
    
    def get_permission_count(self):
        """Возвращает количество разрешений у роли"""
        return self.permissions.count()
    
    def get_usage_count(self):
        """Возвращает количество использований роли (участников с этой ролью)"""
        return self.teammembership_set.filter(is_active=True).count()
    
    def _get_field_changes(self, old_instance):
        """Определяет изменения в полях роли"""
        changes = {}
        
        if old_instance.name != self.name:
            changes['name'] = (old_instance.name, self.name)
        
        if old_instance.description != self.description:
            changes['description'] = (old_instance.description, self.description)
        
        if old_instance.is_default != self.is_default:
            changes['is_default'] = (old_instance.is_default, self.is_default)
        
        return changes
    
    def _get_permission_changes(self, old_instance):
        """Определяет изменения в разрешениях роли"""
        old_permissions = set(old_instance.permissions.values_list('codename', flat=True))
        new_permissions = set(self.permissions.values_list('codename', flat=True))
        
        if old_permissions != new_permissions:
            return (list(old_permissions), list(new_permissions))
        return None
    
    def save(self, *args, **kwargs):
        """Переопределяем save для логирования изменений"""
        is_new = self.pk is None
        old_instance = None
        
        if not is_new:
            try:
                old_instance = Role.objects.get(pk=self.pk)
            except Role.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Переопределяем delete для логирования удаления"""
        super().delete(*args, **kwargs)
    
    @classmethod
    def ensure_default_roles_exist(cls):
        """
        Создает стандартные роли если они не существуют.
        
        Использует DefaultRoleManager для создания стандартных ролей системы.
        
        Returns:
            dict: Результаты создания ролей
        """
        from .role_manager import DefaultRoleManager
        return DefaultRoleManager.ensure_default_roles_exist()

    def __str__(self):
        return self.name


class UserRole(models.Model):
    """
    Модель для хранения глобальных ролей пользователей (не привязанных к командам).
    
    Используется для:
    - Назначения дефолтной роли новым пользователям
    - Отслеживания глобального статуса пользователя в системе
    - Управления базовыми разрешениями пользователя
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='global_roles',
        verbose_name="Пользователь"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='global_users',
        verbose_name="Роль"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активна",
        help_text="Активна ли роль для пользователя"
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Назначена"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_global_roles',
        verbose_name="Назначена пользователем"
    )
    
    class Meta:
        unique_together = ('user', 'role')
        verbose_name = "Глобальная роль пользователя"
        verbose_name_plural = "Глобальные роли пользователей"
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['role', 'is_active']),
        ]
    
    def deactivate(self, deactivated_by=None):
        """Деактивирует роль пользователя"""
        self.is_active = False
        if deactivated_by:
            self.assigned_by = deactivated_by
        self.save()
    
    def reactivate(self, reactivated_by=None):
        """Реактивирует роль пользователя"""
        self.is_active = True
        if reactivated_by:
            self.assigned_by = reactivated_by
        self.save()
    
    def __str__(self):
        status = "активна" if self.is_active else "неактивна"
        return f"{self.user.username} - {self.role.name} ({status})"


class Team(models.Model):
    """Модель команды переводчиков"""

    name = models.CharField(max_length=100)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_teams"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="TeamMembership", related_name="teams"
    )
    
    # Новые поля для управления жизненным циклом
    status = models.CharField(
        max_length=20,
        choices=TeamStatus.choices,
        default=TeamStatus.ACTIVE,
        help_text="Текущий статус команды"
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['creator', 'status']),
        ]
    
    def can_be_managed_by(self, user):
        """Проверяет, может ли пользователь управлять командой"""
        return self.creator == user or user.is_superuser
    
    def is_active(self):
        """Проверяет, активна ли команда"""
        return self.status == TeamStatus.ACTIVE
    
    def can_be_reactivated(self):
        """Проверяет, может ли команда быть возобновлена"""
        return self.status == TeamStatus.INACTIVE
    
    def can_be_disbanded(self):
        """Проверяет, может ли команда быть распущена"""
        return self.status in [TeamStatus.ACTIVE, TeamStatus.INACTIVE]
    
    def get_active_members_count(self):
        """Возвращает количество активных участников команды"""
        return self.teammembership_set.filter(is_active=True).count()
    
    def get_active_members(self):
        """Возвращает QuerySet активных участников команды"""
        return self.members.filter(teammembership__is_active=True)
    
    def _validate_leadership_transfer(self, new_leader, current_leader):
        """Валидация возможности передачи прав руководства"""
        if not self.can_be_managed_by(current_leader):
            raise PermissionDenied("Только создатель команды может передать права руководства")
        
        try:
            return TeamMembership.objects.get(team=self, user=new_leader, is_active=True)
        except TeamMembership.DoesNotExist:
            raise ValueError("Новый руководитель должен быть активным участником команды")
    
    def _remove_current_leader_role(self, current_leader, leader_role):
        """Убирает роль руководителя у текущего лидера"""
        try:
            membership = TeamMembership.objects.get(team=self, user=current_leader, is_active=True)
            membership.remove_role(leader_role, admin_user=current_leader)
        except TeamMembership.DoesNotExist:
            pass  # Создатель может не быть в списке участников
    
    def transfer_leadership(self, new_leader, current_leader):
        """
        Передает права руководства команды другому участнику.
        
        Args:
            new_leader: Пользователь, которому передаются права
            current_leader: Текущий руководитель команды
            
        Returns:
            bool: True если передача прошла успешно
            
        Raises:
            PermissionDenied: Если current_leader не является создателем команды
            ValueError: Если new_leader не является участником команды
        """
        new_leader_membership = self._validate_leadership_transfer(new_leader, current_leader)
        leader_role = ensure_leader_role_exists()
        
        with transaction.atomic():
            self._remove_current_leader_role(current_leader, leader_role)
            new_leader_membership.add_role(leader_role, admin_user=current_leader)
            
            old_creator = self.creator
            self.creator = new_leader
            self.save()
            
        return True
    
    def get_leader_membership(self):
        """
        Возвращает участника команды с ролью руководителя.
        
        Returns:
            TeamMembership или None: Участник с ролью руководителя
        """
        try:
            leader_role = ensure_leader_role_exists()
            return TeamMembership.objects.select_related('user')\
                .prefetch_related('roles')\
                .filter(
                    team=self,
                    roles=leader_role,
                    is_active=True
                ).first()
        except Exception:
            return None
    
    def can_transfer_leadership(self, user):
        """
        Проверяет, может ли пользователь передать права руководства.
        
        Args:
            user: Пользователь для проверки
            
        Returns:
            bool: True если может передать права
        """
        return (self.creator == user and 
                self.status == TeamStatus.ACTIVE and
                TeamMembership.objects.filter(team=self, is_active=True).count() > 1)

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    """
    Промежуточная модель, которая связывает Пользователя и Команду.
    Именно она позволяет нам добавить дополнительные данные к этой связи,
    а именно - РОЛИ.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        db_index=True
    )
    team = models.ForeignKey(
        Team, 
        on_delete=models.CASCADE,
        db_index=True
    )
    roles = models.ManyToManyField(Role)
    
    # Новые поля для отслеживания активности
    joined_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Активен ли участник в команде",
        db_index=True
    )

    class Meta:
        unique_together = ("user", "team")
        indexes = [
            models.Index(fields=['team', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def deactivate(self):
        """Деактивирует участника команды"""
        self.is_active = False
        self.save()
    
    def reactivate(self):
        """Реактивирует участника команды"""
        self.is_active = True
        self.save()
    
    def add_role(self, role, admin_user=None):
        """Добавляет роль участнику"""
        if role not in self.roles.all():
            self.roles.add(role)
    
    def remove_role(self, role, admin_user=None):
        """Удаляет роль у участника"""
        if role in self.roles.all():
            self.roles.remove(role)

    def __str__(self):
        role_names = ", ".join([role.name for role in self.roles.all()])
        return f"{self.user.username} в команде {self.team.name} как {role_names}"


# TeamStatusHistory удалена - используется file-based logging в logs/role_audit.log


def ensure_leader_role_exists():
    """
    Создает роль "Руководитель" если она не существует в системе.

    Returns:
        Role: Объект роли "Руководитель"

    Raises:
        Exception: При ошибке создания или получения роли
    """
    try:
        role, created = Role.objects.get_or_create(
            name="Руководитель",
            defaults={
                "description": "Руководитель команды с полными правами управления"
            },
        )
        return role

    except Exception as e:
        raise Exception(f'Не удалось создать роль "Руководитель": {str(e)}')
