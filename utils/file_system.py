"""
Утилиты для управления файловой структурой TranslationHub.
Упрощенная версия - только необходимый функционал.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Union
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone


class FileSystemError(Exception):
    """Ошибка файловой системы."""
    pass


class DirectoryCreationError(FileSystemError):
    """Ошибка создания папки."""
    pass


class FileUploadError(FileSystemError):
    """Ошибка загрузки файла."""
    pass


class FileCleanupError(FileSystemError):
    """Ошибка очистки файлов."""
    pass


class FileValidationError(FileSystemError):
    """Ошибка валидации файла."""
    pass


class FileSecurityError(FileSystemError):
    """Ошибка безопасности."""
    pass

class FileOperationLogger:
    """Логирование файловых операций."""
    
    @staticmethod
    def log_directory_created(path: Union[str, Path], user_id: Optional[int] = None, 
                            operation_context: Optional[str] = None):
        """Лог создания папки."""
        pass
    
    @staticmethod
    def log_file_uploaded(path: Union[str, Path], user_id: Optional[int], file_size: int,
                         file_type: Optional[str] = None, operation_context: Optional[str] = None):
        """Лог загрузки файла."""
        pass
    
    @staticmethod
    def log_file_deleted(path: Union[str, Path], user_id: Optional[int] = None,
                        operation_context: Optional[str] = None):
        """Лог удаления файла."""
        pass
    
    @staticmethod
    def log_error(operation: str, error: Exception, path: Optional[Union[str, Path]] = None,
                 user_id: Optional[int] = None, notify_admins: bool = False):
        """Лог ошибок."""
        pass
    
    @staticmethod
    def log_security_violation(operation: str, path: Union[str, Path], user_id: Optional[int] = None,
                              ip_address: Optional[str] = None, details: Optional[str] = None):
        """Лог нарушений безопасности."""
        pass

class FilePathManager:
    """Управление путями к файлам и папкам."""
    
    @staticmethod
    def get_user_path(user_id: int) -> Path:
        """Путь к папке пользователя."""
        return Path(settings.MEDIA_ROOT) / "users" / str(user_id)
    
    @staticmethod
    def get_team_path(team_id: int) -> Path:
        """Путь к папке команды."""
        return Path(settings.MEDIA_ROOT) / "teams" / str(team_id)
    
    @staticmethod
    def get_project_path(team_id: int, content_folder: str) -> Path:
        """Путь к папке проекта."""
        return FilePathManager.get_team_path(team_id) / "projects" / content_folder
    
    @staticmethod
    def get_avatar_path(user_id: int) -> str:
        """Путь для аватарки."""
        return f"users/{user_id}/avatar.jpg"
    
    @staticmethod
    def get_project_image_path(team_id: int, content_folder: str, filename: str) -> str:
        """Путь для изображения проекта."""
        return f"teams/{team_id}/projects/{content_folder}/images/{filename}"
    
    @staticmethod
    def get_project_document_path(team_id: int, content_folder: str, filename: str) -> str:
        """Путь для документа проекта."""
        return f"teams/{team_id}/projects/{content_folder}/documents/{filename}"
    
    @staticmethod
    def get_project_glossary_path(team_id: int, content_folder: str, filename: str) -> str:
        """Путь для файла глоссария."""
        return f"teams/{team_id}/projects/{content_folder}/glossary/{filename}"
    
    @staticmethod
    def get_chapter_path(team_id: int, content_folder: str, chapter_id: int) -> Path:
        """Путь к папке главы."""
        return FilePathManager.get_project_path(team_id, content_folder) / "chapters" / str(chapter_id)
    
    @staticmethod
    def get_chapter_file_path(team_id: int, content_folder: str, chapter_id: int, folder: str, filename: str) -> str:
        """Путь для файла главы."""
        return f"teams/{team_id}/projects/{content_folder}/chapters/{chapter_id}/{folder}/{filename}"
    
    @staticmethod
    def generate_translation_files(chapter_path: Path) -> int:
        """Создание пустых .txt для переводчика на основе RAW."""
        raw_folder = chapter_path / "raw"
        translation_folder = chapter_path / "translation"
        
        if not raw_folder.exists():
            return 0
        
        translation_folder.mkdir(parents=True, exist_ok=True)
        
        created_count = 0
        raw_files = [f for f in raw_folder.iterdir() if f.is_file()]
        
        for raw_file in raw_files:
            base_name = raw_file.stem
            txt_file = translation_folder / f"{base_name}.txt"
            
            if not txt_file.exists():
                txt_file.touch()
                created_count += 1
        
        return created_count
    
    @staticmethod
    def delete_translation_file(chapter_path: Path, raw_filename: str) -> bool:
        """Удаление файла перевода при удалении RAW."""
        translation_folder = chapter_path / "translation"
        
        if not translation_folder.exists():
            return False
        
        base_name = Path(raw_filename).stem
        txt_file = translation_folder / f"{base_name}.txt"
        
        if txt_file.exists():
            try:
                os.remove(txt_file)
                return True
            except Exception:
                return False
        
        return False


class DirectoryManager:
    """Создание и управление папками."""
    
    @staticmethod
    def ensure_directory_exists(path: Union[str, Path], user_id: Optional[int] = None) -> bool:
        """Создание папки если не существует."""
        try:
            path = Path(path)
            
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
            
            return True
            
        except PermissionError as e:
            error = DirectoryCreationError(f"Permission denied creating directory: {path}")
            raise error
        except OSError as e:
            error = DirectoryCreationError(f"OS error creating directory: {path}")
            raise error
    
    @staticmethod
    def create_user_directory(user_id: int) -> bool:
        """Структура папок пользователя."""
        try:
            user_path = FilePathManager.get_user_path(user_id)
            DirectoryManager.ensure_directory_exists(user_path, user_id)
            
            documents_path = user_path / "documents"
            DirectoryManager.ensure_directory_exists(documents_path, user_id)
            return True
            
        except Exception as e:
            error = DirectoryCreationError(f"Failed to create user directory for user {user_id}")
            raise error
    
    @staticmethod
    def create_team_directory(team_id: int) -> bool:
        """Структура папок команды."""
        try:
            team_path = FilePathManager.get_team_path(team_id)
            DirectoryManager.ensure_directory_exists(team_path)
            
            documents_path = team_path / "documents"
            projects_path = team_path / "projects"
            
            DirectoryManager.ensure_directory_exists(documents_path)
            DirectoryManager.ensure_directory_exists(projects_path)
            return True
            
        except Exception as e:
            error = DirectoryCreationError(f"Failed to create team directory for team {team_id}")
            raise error
    
    @staticmethod
    def create_project_directory(team_id: int, content_folder: str) -> bool:
        """Структура папок проекта."""
        try:
            project_path = FilePathManager.get_project_path(team_id, content_folder)
            DirectoryManager.ensure_directory_exists(project_path)
            
            subdirs = ["images", "documents", "glossary"]
            for subdir in subdirs:
                subdir_path = project_path / subdir
                DirectoryManager.ensure_directory_exists(subdir_path)
            return True
            
        except Exception as e:
            error = DirectoryCreationError(f"Failed to create project directory for team {team_id}, project {content_folder}")
            raise error
    
    @staticmethod
    def create_chapter_directory(team_id: int, content_folder: str, chapter_id: int, user_id: Optional[int] = None) -> bool:
        """Структура папок главы с этапами перевода."""
        try:
            project_path = FilePathManager.get_project_path(team_id, content_folder)
            chapter_path = project_path / "chapters" / str(chapter_id)
            
            DirectoryManager.ensure_directory_exists(chapter_path, user_id)
            
            chapter_subdirs = ["raw", "translation", "cleaning", "typesetting", "editing", "final"]
            for subdir in chapter_subdirs:
                subdir_path = chapter_path / subdir
                DirectoryManager.ensure_directory_exists(subdir_path, user_id)
            return True
            
        except Exception as e:
            error = DirectoryCreationError(f"Failed to create chapter directory for team {team_id}, project {content_folder}, chapter {chapter_id}")
            raise error
    
    @staticmethod
    def remove_directory_safe(path: Union[str, Path], user_id: Optional[int] = None) -> bool:
        """Безопасное удаление папки."""
        try:
            path = Path(path)
            
            if path.exists() and path.is_dir():
                shutil.rmtree(path)
            
            return True
            
        except PermissionError as e:
            error = FileCleanupError(f"Permission denied deleting directory: {path}")
            return False
        except Exception as e:
            error = FileCleanupError(f"Error deleting directory: {path}")
            return False
    
    @staticmethod
    def remove_chapter_directory(team_id: int, content_folder: str, chapter_id: int, user_id: Optional[int] = None) -> bool:
        """Удаление папки главы."""
        try:
            chapter_path = FilePathManager.get_chapter_path(team_id, content_folder, chapter_id)
            result = DirectoryManager.remove_directory_safe(chapter_path, user_id)
            return result
        except Exception:
            return False



class FileUploadHandler:
    """Обработка загрузки файлов."""
    
    # Опасные расширения файлов
    DANGEROUS_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', 
        '.js', '.jar', '.php', '.asp', '.aspx', '.jsp', '.py', '.pl', '.sh'
    ]
    
    # Максимальный размер файла (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    @staticmethod
    def _validate_file_object(file: UploadedFile) -> None:
        """Проверка объекта файла."""
        if not file:
            raise FileValidationError("Invalid file object")
        
        if not hasattr(file, 'size') or not hasattr(file, 'content_type'):
            raise FileValidationError("Invalid file object")
    
    @staticmethod
    def _validate_file_size(file: UploadedFile) -> None:
        """Проверка размера файла."""
        if file.size <= 0:
            raise FileValidationError("File is empty")
        
        if file.size > FileUploadHandler.MAX_FILE_SIZE:
            raise FileValidationError(
                f"File size {file.size} bytes exceeds maximum allowed size "
                f"{FileUploadHandler.MAX_FILE_SIZE} bytes"
            )
    
    @staticmethod
    def _validate_file_name(file: UploadedFile) -> None:
        """Проверка имени файла."""
        if not hasattr(file, 'name') or not file.name:
            return
        
        # Базовая проверка имени файла
        import re
        if not re.match(r'^[a-zA-Z0-9._\-\s()]+$', file.name):
            raise FileValidationError(f"Invalid filename: {file.name}")
    
    @staticmethod
    def _validate_file_security(file: UploadedFile) -> None:
        """Проверка на опасные расширения."""
        if not hasattr(file, 'name') or not file.name:
            return
        
        name_lower = file.name.lower()
        
        for ext in FileUploadHandler.DANGEROUS_EXTENSIONS:
            if name_lower.endswith(ext):
                raise FileSecurityError(f"Dangerous file extension detected: {file.name}")
    
    @staticmethod
    def validate_file(file: UploadedFile, user_id: Optional[int] = None) -> bool:
        """Валидация файла для загрузки."""
        try:
            FileUploadHandler._validate_file_object(file)
            FileUploadHandler._validate_file_size(file)
            FileUploadHandler._validate_file_name(file)
            FileUploadHandler._validate_file_security(file)
            return True
            
        except (FileValidationError, FileSecurityError):
            raise
        except Exception as e:
            error = FileValidationError(f"Unexpected error during file validation: {e}")
            raise error
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        """Очистка имени файла."""
        import re
        # Удаляем опасные символы
        filename = re.sub(r'[^\w\s\-\.]', '', filename)
        # Заменяем пробелы на подчеркивания
        filename = filename.replace(' ', '_')
        return filename

class FileCleanupManager:
    """Очистка файлов."""
    
    @staticmethod
    def cleanup_user_files(user_id: int) -> bool:
        """Очистка файлов пользователя."""
        try:
            user_path = FilePathManager.get_user_path(user_id)
            
            if not user_path.exists():
                return True
            
            success = DirectoryManager.remove_directory_safe(user_path, user_id)
            return success
            
        except Exception:
            return False
    
    @staticmethod
    def cleanup_project_files(team_id: int, content_folder: str) -> bool:
        """Очистка файлов проекта."""
        try:
            project_path = FilePathManager.get_project_path(team_id, content_folder)
            
            if not project_path.exists():
                return True
            
            success = DirectoryManager.remove_directory_safe(project_path)
            return success
            
        except Exception:
            return False
    
    @staticmethod
    def cleanup_team_files(team_id: int) -> bool:
        """Очистить файлы команды"""
        try:
            team_path = FilePathManager.get_team_path(team_id)
            
            if not team_path.exists():
                return True
            
            success = DirectoryManager.remove_directory_safe(team_path)
            return success
            
        except Exception:
            return False
    
    @staticmethod
    def cleanup_chapter_files(team_id: int, content_folder: str, chapter_id: int, user_id: Optional[int] = None) -> bool:
        """Очистить файлы главы"""
        try:
            chapter_path = FilePathManager.get_chapter_path(team_id, content_folder, chapter_id)
            
            if not chapter_path.exists():
                return True
            
            success = DirectoryManager.remove_chapter_directory(team_id, content_folder, chapter_id, user_id)
            return success
            
        except Exception:
            return False

def user_avatar_upload_path(instance, filename):
    """Функция upload_to для аватарок пользователей"""
    try:
        DirectoryManager.create_user_directory(instance.id)
        return FilePathManager.get_avatar_path(instance.id)
    except Exception:
        return f"users/{instance.id}/avatar.jpg"


def project_image_upload_path(instance, filename):
    """Функция upload_to для изображений проектов"""
    try:
        clean_name = FilePathValidator.sanitize_filename(filename)
        project = instance.project
        team_id = project.team.id
        content_folder = project.content_folder
        
        DirectoryManager.create_project_directory(team_id, content_folder)
        return FilePathManager.get_project_image_path(team_id, content_folder, clean_name)
    except Exception:
        clean_name = FilePathValidator.sanitize_filename(filename)
        return f"teams/{instance.project.team.id}/projects/{instance.project.content_folder}/images/{clean_name}"


def project_document_upload_path(instance, filename):
    """Функция upload_to для документов проектов"""
    try:
        clean_name = FilePathValidator.sanitize_filename(filename)
        project = instance.project
        team_id = project.team.id
        content_folder = project.content_folder
        
        DirectoryManager.create_project_directory(team_id, content_folder)
        
        document_type = getattr(instance, 'document_type', 'documents')
        
        if document_type == 'glossary':
            return FilePathManager.get_project_glossary_path(team_id, content_folder, clean_name)
        else:
            return FilePathManager.get_project_document_path(team_id, content_folder, clean_name)
    except Exception:
        clean_name = FilePathValidator.sanitize_filename(filename)
        if getattr(instance, 'document_type', 'documents') == 'glossary':
            return f"teams/{instance.project.team.id}/projects/{instance.project.content_folder}/glossary/{clean_name}"
        else:
            return f"teams/{instance.project.team.id}/projects/{instance.project.content_folder}/documents/{clean_name}"
