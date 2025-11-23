"""Сигналы для автоматического управления файловой структурой."""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from teams.models import Team
from projects.models import Project
from utils.file_system import (
    DirectoryManager,
    FileCleanupManager,
    FileOperationLogger,
    FileSystemError
)

# Получаем модель пользователя
User = get_user_model()

# Настройка логирования


@receiver(post_save, sender=User)
def create_user_directory(sender, instance, created, **kwargs):
    """Создание папки пользователя при регистрации."""
    if created:
        try:
            # Создаем папку пользователя
            success = DirectoryManager.create_user_directory(instance.id)
            
        except FileSystemError:
            pass
            
        except Exception:
            pass


@receiver(post_save, sender=Team)
def create_team_directory(sender, instance, created, **kwargs):
    """Создание папки команды."""
    if created:
        try:
            # Создаем папку команды
            DirectoryManager.create_team_directory(instance.id)
        except FileSystemError:
            pass
        except Exception:
            pass


@receiver(post_save, sender=Project)
def create_project_directory(sender, instance, created, **kwargs):
    """Создание папки проекта."""
    if created:
        try:
            # Проверяем, что у проекта есть content_folder
            if not instance.content_folder:
                return
            
            # Создаем папку проекта
            success = DirectoryManager.create_project_directory(
                instance.team.id, 
                instance.content_folder
            )
            
        except FileSystemError:
            pass
            
        except Exception:
            pass


@receiver(pre_delete, sender=User)
def cleanup_user_files(sender, instance, **kwargs):
    """Очистка файлов пользователя при удалении."""
    try:
        # Очищаем файлы пользователя
        success = FileCleanupManager.cleanup_user_files(instance.id)
    except Exception:
        pass



@receiver(pre_delete, sender=Project)
def cleanup_project_files(sender, instance, **kwargs):
    """Очистка файлов проекта при удалении."""
    try:
        # Проверяем, что у проекта есть content_folder
        if not instance.content_folder:
            return
        
        # Очищаем файлы проекта
        success = FileCleanupManager.cleanup_project_files(
            instance.team.id,
            instance.content_folder
        )
    except FileSystemError as e:
        pass
    except Exception as e:
        pass


@receiver(pre_delete, sender=Team)
def cleanup_team_files(sender, instance, **kwargs):
    """Очистка файлов команды при удалении."""
    try:
        # Очищаем файлы команды
        success = FileCleanupManager.cleanup_team_files(instance.id)
    except FileSystemError as e:
        pass
    except Exception as e:
        pass


@receiver(pre_delete, sender='projects.Chapter')
def cleanup_chapter_files(sender, instance, **kwargs):
    """Очистка файлов главы при удалении."""
    
    try:
        # Проверяем, что у проекта есть content_folder
        if not instance.project.content_folder:
            return
        
        # Очищаем файлы главы
        success = FileCleanupManager.cleanup_chapter_files(
            instance.project.team.id,
            instance.project.content_folder,
            instance.id,
            user_id=getattr(instance, '_deleting_user_id', None)  # Если передан пользователь
        )
    except FileSystemError as e:
        pass
    except Exception as e:
        pass


# Функция для инициализации базовых папок при запуске системы
def initialize_base_directories():
    """Создание базовых папок при запуске системы."""
    try:
        from pathlib import Path
        from django.conf import settings
        
        # Создаем базовые папки
        base_paths = [
            Path(settings.MEDIA_ROOT) / "users",
            Path(settings.MEDIA_ROOT) / "teams",
            Path(settings.MEDIA_ROOT) / "temp" / "uploads"
        ]
        
        for path in base_paths:
            DirectoryManager.ensure_directory_exists(path)
    except Exception as e:
        pass
