from django.db import models
from django.conf import settings
from projects.models import Project

# Иконки для типов контента (используется в admin и шаблонах)
CONTENT_TYPE_ICONS = {
    'manga': '🇯🇵',
    'manhwa': '🇰🇷',
    'manhua': '🇨🇳',
    'general': '🌐'
}


class ContentType(models.TextChoices):
    MANGA = 'manga', 'Манга (японский)'
    MANHWA = 'manhwa', 'Манхва (корейский)'
    MANHUA = 'manhua', 'Маньхуа (китайский)'
    GENERAL = 'general', 'Общие термины'


class CategoryScope(models.TextChoices):
    GLOBAL = 'global', 'Глобальный (для всех)'
    USER = 'user', 'Пользовательский'
    PROJECT = 'project', 'Проектный'


class GlossaryCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    content_type = models.CharField(
        max_length=10, 
        choices=ContentType.choices, 
        verbose_name="Тип контента"
    )
    scope = models.CharField(
        max_length=10,
        choices=CategoryScope.choices,
        default=CategoryScope.GLOBAL,
        verbose_name="Область видимости"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="Создатель"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Категория статей"
        verbose_name_plural = "Категории статей"
        ordering = ['content_type', 'name']
    
    def __str__(self):
        scope_display = CategoryScope(self.scope).label
        content_display = ContentType(self.content_type).label
        return f"{self.name} ({content_display}, {scope_display})"


class GlossaryTerm(models.Model):
    term = models.CharField(max_length=200, verbose_name="Заголовок")
    definition = models.TextField(verbose_name="Содержание статьи")
    category = models.ForeignKey(
        GlossaryCategory, 
        on_delete=models.CASCADE, 
        related_name='terms', 
        verbose_name="Категория",
        null=True,
        blank=True
    )
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='glossary_terms', 
        verbose_name="Проект",
        null=True,
        blank=True,
        help_text="Оставьте пустым для общих терминов"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="Создал"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    class Meta:
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"
        unique_together = ['term', 'category']
        ordering = ['term']
    
    def __str__(self):
        if self.project:
            return f"{self.term} ({self.project.title})"
        if self.category:
            return f"{self.term} ({self.category.name})"
        return self.term
    
    @property
    def content_type(self):
        return self.category.content_type
    
    def is_accessible_by_user(self, user):
        if self.category.scope == 'global':
            return True
        elif self.category.scope == 'user':
            return self.created_by == user
        elif self.category.scope == 'project' and self.project:
            return user.teammembership_set.filter(team=self.project.team, is_active=True).exists()
        return False
