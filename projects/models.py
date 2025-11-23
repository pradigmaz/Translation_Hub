from django.db import models
from teams.models import Team
from django.conf import settings


class ProjectType(models.TextChoices):
    """Типы проектов"""
    MANGA = 'manga', 'Манга'
    MANHWA = 'manhwa', 'Манхва'
    MANHUA = 'manhua', 'Маньхуа'


class AgeRating(models.TextChoices):
    """Возрастные рейтинги"""
    GENERAL = 'general', 'Обычная'
    ADULT = 'adult', '18+'


class ProjectStatus(models.TextChoices):
    """Статусы проекта"""
    TRANSLATING = 'translating', 'Переводим'
    DROPPED = 'dropped', 'Заброшен'
    COMPLETED = 'completed', 'Переведён'
    FROZEN = 'frozen', 'Заморожен'


class StatusDisplayMixin:
    """
    Миксин для единообразного отображения статусов.
    
    Требует:
        pass
    - self.status — поле со статусом
    - self.STATUS_CONFIG — словарь конфигурации статусов
    """
    
    STATUS_CONFIG = {}
    
    def get_status_badge_class(self):
        """Возвращает CSS класс для badge статуса"""
        config = self.STATUS_CONFIG.get(self.status, {})
        badge_class = config.get('badge', 'bg-secondary')
        return f"badge {badge_class}"
    
    def get_status_icon(self):
        """Возвращает иконку для статуса"""
        config = self.STATUS_CONFIG.get(self.status, {})
        return config.get('icon', 'fas fa-question-circle')
    
    def get_status_description(self):
        """Возвращает описание статуса"""
        config = self.STATUS_CONFIG.get(self.status, {})
        return config.get('description', 'Неизвестный статус')


class Project(StatusDisplayMixin, models.Model):
    """Модель проекта перевода (манга, манхва, маньхуа)."""
    
    # Конфигурация статусов для миксина
    STATUS_CONFIG = {
        'translating': {
            'badge': 'bg-primary',
            'icon': 'fas fa-language',
            'description': 'Проект активно переводится командой'
        },
        'dropped': {
            'badge': 'bg-secondary',
            'icon': 'fas fa-stop-circle',
            'description': 'Команда прекратила работу над проектом'
        },
        'completed': {
            'badge': 'bg-success',
            'icon': 'fas fa-check-circle',
            'description': 'Все главы проекта переведены и готовы'
        },
        'frozen': {
            'badge': 'bg-warning',
            'icon': 'fas fa-pause-circle',
            'description': 'Работа временно приостановлена (перерыв, ожидание новых глав)'
        },
    }
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    project_type = models.CharField(
        max_length=10, 
        choices=ProjectType.choices, 
        default=ProjectType.MANGA,
        verbose_name="Тип проекта"
    )
    
    age_rating = models.CharField(
        max_length=10, 
        choices=AgeRating.choices, 
        default=AgeRating.GENERAL,
        verbose_name="Возрастной рейтинг"
    )
    
    content_folder = models.CharField(
        max_length=100, 
        verbose_name="Папка контента",
        blank=True
    )
    
    status = models.CharField(
        max_length=20, 
        choices=ProjectStatus.choices, 
        default=ProjectStatus.TRANSLATING,
        verbose_name="Статус проекта"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['team', 'content_folder']]

    def user_has_access(self, user):
        """Проверяет, имеет ли пользователь доступ к проекту через активное членство в команде"""
        return (
            self.team.members.filter(
                id=user.id,
                teammembership__is_active=True
            ).exists() and 
            self.team.status == 'active'
        )
    
    def get_active_members(self):
        """Возвращает активных участников команды проекта"""
        return self.team.members.filter(
            teammembership__is_active=True
        ).select_related('teammembership')
    
    def can_be_edited_by(self, user):
        """Проверяет, может ли пользователь редактировать проект"""
        return (
            self.user_has_access(user) and 
            (self.team.creator == user or user.is_superuser)
        )

    def create_first_chapter(self):
        """Создать первую главу автоматически при создании проекта"""
        if not self.chapters.exists():
            chapter = Chapter.objects.create(
                project=self,
                title="Глава 1",
                status='raw'
            )
            
            # Создаем структуру папок для главы
            try:
                from utils.file_system import DirectoryManager
                DirectoryManager.create_chapter_directory(
                    self.team.id,
                    self.content_folder,
                    chapter.id
                )
            except Exception:
                pass
            
            return chapter
        return None

    def __str__(self):
        return self.title


class ChapterStatus(models.TextChoices):
    """Статусы главы с workflow"""
    RAW = 'raw', 'RAW'
    TRANSLATING = 'translating', 'Перевод'
    CLEANING = 'cleaning', 'Клининг'
    TYPESETTING = 'typesetting', 'Тайпинг'
    EDITING = 'editing', 'Редактура'
    DONE = 'done', 'Готово'


class Chapter(StatusDisplayMixin, models.Model):
    """Модель главы проекта с workflow статусами."""
    
    # Конфигурация статусов для миксина
    STATUS_CONFIG = {
        'raw': {
            'badge': 'bg-secondary',
            'icon': 'fas fa-file',
            'description': 'Исходные файлы загружены'
        },
        'translating': {
            'badge': 'bg-primary',
            'icon': 'fas fa-language',
            'description': 'Идёт перевод'
        },
        'cleaning': {
            'badge': 'bg-info',
            'icon': 'fas fa-broom',
            'description': 'Идёт клининг'
        },
        'editing': {
            'badge': 'bg-warning text-dark',
            'icon': 'fas fa-edit',
            'description': 'Идёт редактура'
        },
        'typesetting': {
            'badge': 'bg-purple text-white',
            'icon': 'fas fa-font',
            'description': 'Идёт тайпинг'
        },
        'done': {
            'badge': 'bg-success',
            'icon': 'fas fa-check-circle',
            'description': 'Глава готова'
        },
    }
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )
    status = models.CharField(max_length=20, choices=ChapterStatus.choices, default=ChapterStatus.RAW)
    created_at = models.DateTimeField(auto_now_add=True)
    
    WORKFLOW_TRANSITIONS = {
        'raw': ['translating', 'cleaning'],  # RAW → Перевод или Клининг (параллельно)
        'translating': ['editing', 'raw'],   # Перевод → Редактура
        'editing': ['typesetting', 'translating'],  # Редактура → Тайпинг
        'cleaning': ['typesetting', 'raw'],  # Клининг → Тайпинг
        'typesetting': ['done', 'editing'],  # Тайпинг → Готово
        'done': []
    }
    
    STATUS_ROLE_MAP = {
        'raw': None,
        'translating': 'Переводчик',
        'cleaning': 'Клинер',
        'editing': 'Редактор',
        'typesetting': 'Тайпер',
        'done': None  # Любой может завершить
    }

    def __str__(self):
        return f"{self.project.title} - {self.title}"
    
    def get_completion_percentage(self):
        if self.status == 'raw':
            files_count = self.get_files_count()
            return 10 if files_count > 0 else 0
        
        status_progress = {
            'translating': 25,
            'cleaning': 40,
            'editing': 60,
            'typesetting': 80,
            'done': 100,
        }
        return status_progress.get(self.status, 0)
    

    
    def get_files_count(self):
        """Количество уникальных файлов (по базовому имени без расширения)."""
        import os
        from pathlib import Path
        from utils.file_system import FilePathManager
        
        try:
            chapter_path = FilePathManager.get_chapter_path(
                self.project.team.id,
                self.project.content_folder,
                self.id
            )
            
            if not os.path.exists(chapter_path):
                return 0
            
            unique_basenames = set()
            for root, dirs, files in os.walk(chapter_path):
                for filename in files:
                    basename = Path(filename).stem
                    unique_basenames.add(basename)
            
            return len(unique_basenames)
        except Exception:
            return 0
    
    def can_transition_to(self, new_status, user):
        """Проверка возможности перехода в новый статус с учетом роли."""
        allowed_transitions = self.WORKFLOW_TRANSITIONS.get(self.status, [])
        if new_status not in allowed_transitions:
            current_status_display = ChapterStatus(self.status).label
            new_status_display = ChapterStatus(new_status).label
            return False, f"Переход из '{current_status_display}' в '{new_status_display}' запрещён"
        
        # Проверяем роль ТЕКУЩЕГО статуса (откуда переходим)
        # Пользователь должен иметь роль для завершения текущего этапа
        required_role = self.STATUS_ROLE_MAP.get(self.status)
        
        # Если для текущего статуса не требуется роль (None), разрешаем переход
        if not required_role:
            return True, ""
        
        # Проверяем есть ли у пользователя требуемая роль для текущего этапа
        user_has_role = self.project.team.members.filter(
            id=user.id,
            teammembership__roles__name=required_role,
            teammembership__is_active=True
        ).exists()
        
        if not user_has_role:
            return False, f"Требуется роль '{required_role}' для завершения этапа"
        
        return True, ""
    
    def get_allowed_transitions(self, user):
        """Список доступных статусов для перехода с учетом прав пользователя."""
        allowed_statuses = []
        possible_transitions = self.WORKFLOW_TRANSITIONS.get(self.status, [])
        
        for status_code in possible_transitions:
            can_transition, error_msg = self.can_transition_to(status_code, user)
            if can_transition:
                status_name = ChapterStatus(status_code).label
                allowed_statuses.append((status_code, status_name))
            else:
                # Отладка: логируем почему переход запрещён
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"User {user.username} cannot transition from {self.status} to {status_code}: {error_msg}")
        
        return allowed_statuses


class Comment(models.Model):
    """Комментарии к главам для обсуждения работы."""
    chapter = models.ForeignKey(
        Chapter,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Глава'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chapter_comments',
        verbose_name='Автор'
    )
    text = models.TextField(
        max_length=1000,
        verbose_name='Текст комментария'
    )
    file_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Путь к файлу',
        help_text='Относительный путь к файлу (например: raw/page_001.png)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    
    class Meta:
        ordering = ['-created_at']  # Новые комментарии сверху
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
    
    def __str__(self):
        return f"{self.user.username}: {self.text[:50]}"
    
    def can_be_deleted_by(self, user):
        """Проверка прав на удаление: автор или руководитель команды."""
        if self.user == user:
            return True
        
        is_leader = self.chapter.project.team.members.filter(
            id=user.id,
            teammembership__roles__name='Руководитель',
            teammembership__is_active=True
        ).exists()
        
        return is_leader


class MaterialType(models.TextChoices):
    """Типы материалов проекта"""
    CHARACTER = 'character', 'Описание героя'
    TERM = 'term', 'Термин/Словарь'
    PHRASE = 'phrase', 'Фраза/Выражение'
    NOTE = 'note', 'Заметка'


class ProjectMaterial(models.Model):
    """Материалы проекта: описания героев, термины, фразы и т.п."""
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name='Проект'
    )
    title = models.CharField(
        max_length=200,
        verbose_name='Название'
    )
    material_type = models.CharField(
        max_length=20,
        choices=MaterialType.choices,
        default=MaterialType.NOTE,
        verbose_name='Тип материала'
    )
    content = models.TextField(
        verbose_name='Содержимое'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок сортировки'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_materials',
        verbose_name='Создал'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Материал проекта'
        verbose_name_plural = 'Материалы проекта'
    
    def __str__(self):
        return f"{self.project.title} - {self.title}"
    
    def can_be_edited_by(self, user):
        """Проверка прав на редактирование: автор или участник команды."""
        return self.project.team.members.filter(id=user.id).exists()
