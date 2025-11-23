# Мониторинг файловой системы и очистка осиротевших файлов.

import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import mail_admins
from django.utils import timezone
from django.db import models
from django.contrib.auth import get_user_model

# Модели будут импортированы лениво при необходимости
Team = None
Project = None
ImageContent = None
User = None

def _get_models():
    #  Ленивый импорт моделей.
    global Team, Project, ImageContent, User
    
    if User is None:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
        except Exception:
            User = None
    
    if Team is None:
        try:
            from teams.models import Team as TeamModel
            Team = TeamModel
        except ImportError:
            Team = None
    
    if Project is None:
        try:
            from projects.models import Project as ProjectModel
            Project = ProjectModel
        except ImportError:
            Project = None
    
    if ImageContent is None:
        try:
            # ImageContent удалена в миграции 0003
            ImageContent = None
        except ImportError:
            ImageContent = None
    
    return User, Team, Project, ImageContent

# Настройка логирования


class FileSystemMetrics:
    # Сбор и анализ метрик файловой системы.
    
    def __init__(self):
        self.media_root = Path(settings.MEDIA_ROOT)
        self.metrics_cache = {}
        self.cache_timeout = 300  # 5 минут
        self.last_cache_update = None
    
    def get_disk_usage(self, path: Optional[Path] = None) -> Dict[str, int]:
        """Использование дискового пространства."""
        try:
            if path is None:
                path = self.media_root
            
            if not path.exists():
                return {
                    'total': 0,
                    'used': 0,
                    'free': 0,
                    'percent_used': 0
                }
            
            # Получаем статистику диска
            disk_usage = shutil.disk_usage(path)
            
            total = disk_usage.total
            free = disk_usage.free
            used = total - free
            percent_used = (used / total * 100) if total > 0 else 0
            
            return {
                'total': total,
                'used': used,
                'free': free,
                'percent_used': round(percent_used, 2)
            }
            
        except Exception as e:
            return {
                'total': 0,
                'used': 0,
                'free': 0,
                'percent_used': 0,
                'error': str(e)
            }
    
    def _calculate_directory_stats(self, path: Path) -> Tuple[int, int, int]:
        # Статистика директории.
        total_size = 0
        file_count = 0
        subdirectory_count = 0
        
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                        file_count += 1
                    except (OSError, IOError):
                        continue
                elif item.is_dir() and item != path:
                    subdirectory_count += 1
        except Exception:
            pass
        
        return total_size, file_count, subdirectory_count
    
    def get_directory_size(self, path: Path) -> Dict[str, Any]:
        # Размер директории и количество файлов.
        try:
            if not path.exists() or not path.is_dir():
                return {
                    'size_bytes': 0,
                    'file_count': 0,
                    'subdirectory_count': 0,
                    'error': 'Directory does not exist or is not a directory'
                }
            
            total_size, file_count, subdirectory_count = self._calculate_directory_stats(path)
            
            return {
                'size_bytes': total_size,
                'size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'subdirectory_count': subdirectory_count
            }
            
        except Exception as e:
            return {
                'size_bytes': 0,
                'file_count': 0,
                'subdirectory_count': 0,
                'error': str(e)
            }
    
    def get_media_usage_breakdown(self) -> Dict[str, Dict[str, Any]]:
        # Разбивка использования медиа-папки.
        try:
            breakdown = {}
            
            # Основные категории
            categories = {
                'users': self.media_root / 'users',
                'teams': self.media_root / 'teams',
                'temp': self.media_root / 'temp',
                'backups': self.media_root / 'backups'
            }
            
            for category, path in categories.items():
                breakdown[category] = self.get_directory_size(path)
            
            # Общая статистика
            breakdown['total'] = self.get_directory_size(self.media_root)
            breakdown['disk_usage'] = self.get_disk_usage()
            
            return breakdown
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_user_storage_usage(self, user_id: int) -> Dict[str, Any]:
        # Использование хранилища пользователем.
        try:
            user_path = self.media_root / 'users' / str(user_id)
            user_stats = self.get_directory_size(user_path)
            
            # Дополнительная информация о файлах пользователя
            file_types = {}
            if user_path.exists():
                for file_path in user_path.rglob('*'):
                    if file_path.is_file():
                        suffix = file_path.suffix.lower()
                        if suffix not in file_types:
                            file_types[suffix] = {'count': 0, 'size': 0}
                        
                        try:
                            file_size = file_path.stat().st_size
                            file_types[suffix]['count'] += 1
                            file_types[suffix]['size'] += file_size
                        except (OSError, IOError):
                            continue
            
            return {
                **user_stats,
                'file_types': file_types,
                'user_id': user_id
            }
            
        except Exception as e:
            return {'error': str(e), 'user_id': user_id}
    
    def get_team_storage_usage(self, team_id: int) -> Dict[str, Any]:
        # Использование хранилища командой.
        try:
            team_path = self.media_root / 'teams' / str(team_id)
            team_stats = self.get_directory_size(team_path)
            
            # Разбивка по проектам
            projects_breakdown = {}
            projects_path = team_path / 'projects'
            
            if projects_path.exists():
                for project_dir in projects_path.iterdir():
                    if project_dir.is_dir():
                        project_stats = self.get_directory_size(project_dir)
                        projects_breakdown[project_dir.name] = project_stats
            
            return {
                **team_stats,
                'projects': projects_breakdown,
                'team_id': team_id
            }
            
        except Exception as e:
            return {'error': str(e), 'team_id': team_id}
    
    def get_cached_metrics(self) -> Dict[str, Any]:
        """Кэшированные метрики."""
        now = timezone.now()
        
        # Проверяем, нужно ли обновить кэш
        if (self.last_cache_update is None or 
            (now - self.last_cache_update).total_seconds() > self.cache_timeout):
            
            self.metrics_cache = {
                'timestamp': now.isoformat(),
                'media_breakdown': self.get_media_usage_breakdown(),
                'disk_usage': self.get_disk_usage(),
            }
            self.last_cache_update = now
        
        return self.metrics_cache


# Глобальный экземпляр для использования в приложении
file_metrics = FileSystemMetrics()


class OrphanedFileCleanup:
    # Поиск и очистка осиротевших файлов.
    
    def __init__(self):
        self.media_root = Path(settings.MEDIA_ROOT)
        self.cleanup_stats = {
            'files_checked': 0,
            'orphaned_files_found': 0,
            'files_deleted': 0,
            'space_freed': 0,
            'errors': []
        }
    
    def find_orphaned_user_files(self) -> List[Dict[str, Any]]:
        # Осиротевшие файлы пользователей.
        orphaned_files = []
        
        try:
            users_path = self.media_root / 'users'
            if not users_path.exists():
                return orphaned_files
            
            # Получаем список всех активных пользователей
            User, _, _, _ = _get_models()
            if User:
                active_user_ids = set(User.objects.values_list('id', flat=True))
            else:
                return orphaned_files
            
            # Проверяем каждую папку пользователя
            for user_dir in users_path.iterdir():
                if not user_dir.is_dir():
                    continue
                
                try:
                    user_id = int(user_dir.name)
                    
                    # Если пользователь не существует, помечаем папку как осиротевшую
                    if user_id not in active_user_ids:
                        orphaned_files.append({
                            'type': 'user_directory',
                            'path': user_dir,
                            'user_id': user_id,
                            'size': self._get_directory_size(user_dir),
                            'reason': 'User no longer exists'
                        })
                    else:
                        # Проверяем файлы внутри папки пользователя
                        user_orphaned = self._check_user_directory_files(user_dir, user_id)
                        orphaned_files.extend(user_orphaned)
                        
                except (ValueError, OSError) as e:
                    continue
            
        except Exception as e:
            self.cleanup_stats['errors'].append(f"User files scan error: {e}")
        
        return orphaned_files
    
    def find_orphaned_team_files(self) -> List[Dict[str, Any]]:
        """Осиротевшие файлы команд."""
        orphaned_files = []
        
        try:
            teams_path = self.media_root / 'teams'
            if not teams_path.exists():
                return orphaned_files
            
            # Получаем список всех активных команд
            _, Team, _, _ = _get_models()
            if Team:
                active_team_ids = set(Team.objects.values_list('id', flat=True))
            else:
                return orphaned_files
            
            # Проверяем каждую папку команды
            for team_dir in teams_path.iterdir():
                if not team_dir.is_dir():
                    continue
                
                try:
                    team_id = int(team_dir.name)
                    
                    # Если команда не существует, помечаем папку как осиротевшую
                    if team_id not in active_team_ids:
                        orphaned_files.append({
                            'type': 'team_directory',
                            'path': team_dir,
                            'team_id': team_id,
                            'size': self._get_directory_size(team_dir),
                            'reason': 'Team no longer exists'
                        })
                    else:
                        # Проверяем проекты внутри папки команды
                        team_orphaned = self._check_team_directory_files(team_dir, team_id)
                        orphaned_files.extend(team_orphaned)
                        
                except (ValueError, OSError) as e:
                    continue
            
        except Exception as e:
            self.cleanup_stats['errors'].append(f"Team files scan error: {e}")
        
        return orphaned_files
    
    def find_orphaned_project_files(self) -> List[Dict[str, Any]]:
        """Осиротевшие файлы проектов."""
        orphaned_files = []
        
        try:
            _, _, Project, _ = _get_models()
            if not Project:
                return orphaned_files
            
            # Получаем список всех активных проектов с их папками
            active_projects = {}
            for project in Project.objects.select_related('team').all():
                team_id = project.team.id
                content_folder = project.content_folder
                
                if team_id not in active_projects:
                    active_projects[team_id] = set()
                active_projects[team_id].add(content_folder)
            
            # Проверяем папки проектов
            teams_path = self.media_root / 'teams'
            if not teams_path.exists():
                return orphaned_files
            
            for team_dir in teams_path.iterdir():
                if not team_dir.is_dir():
                    continue
                
                try:
                    team_id = int(team_dir.name)
                    projects_path = team_dir / 'projects'
                    
                    if not projects_path.exists():
                        continue
                    
                    # Проверяем каждую папку проекта
                    for project_dir in projects_path.iterdir():
                        if not project_dir.is_dir():
                            continue
                        
                        project_folder = project_dir.name
                        
                        # Если проект не существует, помечаем папку как осиротевшую
                        if (team_id not in active_projects or 
                            project_folder not in active_projects[team_id]):
                            
                            orphaned_files.append({
                                'type': 'project_directory',
                                'path': project_dir,
                                'team_id': team_id,
                                'project_folder': project_folder,
                                'size': self._get_directory_size(project_dir),
                                'reason': 'Project no longer exists'
                            })
                        
                except (ValueError, OSError) as e:
                    continue
            
        except Exception as e:
            self.cleanup_stats['errors'].append(f"Project files scan error: {e}")
        
        return orphaned_files
    
    def find_orphaned_image_files(self) -> List[Dict[str, Any]]:
        """Осиротевшие файлы изображений."""
        orphaned_files = []
        
        try:
            _, _, _, ImageContent = _get_models()
            if not ImageContent:
                return orphaned_files
            
            # Получаем список всех активных изображений
            active_image_paths = set()
            for image_content in ImageContent.objects.all():
                if image_content.image:
                    # Нормализуем путь
                    image_path = str(image_content.image).replace('\\', '/')
                    active_image_paths.add(image_path)
            
            # Проверяем файлы изображений в папках проектов
            teams_path = self.media_root / 'teams'
            if not teams_path.exists():
                return orphaned_files
            
            for team_dir in teams_path.iterdir():
                if not team_dir.is_dir():
                    continue
                
                projects_path = team_dir / 'projects'
                if not projects_path.exists():
                    continue
                
                for project_dir in projects_path.iterdir():
                    if not project_dir.is_dir():
                        continue
                    
                    images_path = project_dir / 'images'
                    if not images_path.exists():
                        continue
                    
                    # Проверяем каждый файл изображения
                    for image_file in images_path.rglob('*'):
                        if not image_file.is_file():
                            continue
                        
                        # Получаем относительный путь от MEDIA_ROOT
                        try:
                            relative_path = str(image_file.relative_to(self.media_root)).replace('\\', '/')
                            
                            if relative_path not in active_image_paths:
                                orphaned_files.append({
                                    'type': 'orphaned_image',
                                    'path': image_file,
                                    'relative_path': relative_path,
                                    'size': image_file.stat().st_size,
                                    'reason': 'Image not referenced in database'
                                })
                                
                        except (ValueError, OSError) as e:
                            continue
            
        except Exception as e:
            self.cleanup_stats['errors'].append(f"Image files scan error: {e}")
        
        return orphaned_files
    
    def find_temporary_files(self, max_age_hours: int = 24) -> List[Dict[str, Any]]:
        """Временные файлы старше указанного возраста."""
        temp_files = []
        
        try:
            temp_path = self.media_root / 'temp'
            if not temp_path.exists():
                return temp_files
            
            cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
            
            for temp_file in temp_path.rglob('*'):
                if not temp_file.is_file():
                    continue
                
                try:
                    # Получаем время модификации файла
                    mtime = datetime.fromtimestamp(temp_file.stat().st_mtime, tz=timezone.utc)
                    
                    if mtime < cutoff_time:
                        temp_files.append({
                            'type': 'temporary_file',
                            'path': temp_file,
                            'size': temp_file.stat().st_size,
                            'age_hours': (timezone.now() - mtime).total_seconds() / 3600,
                            'reason': f'Temporary file older than {max_age_hours} hours'
                        })
                        
                except (OSError, IOError) as e:
                    continue
            
        except Exception as e:
            self.cleanup_stats['errors'].append(f"Temporary files scan error: {e}")
        
        return temp_files
    
    def _check_user_directory_files(self, user_dir: Path, user_id: int) -> List[Dict[str, Any]]:
        """Проверка файлов пользователя."""
        orphaned_files = []
        
        try:
            User, _, _, _ = _get_models()
            if not User:
                return orphaned_files
            
            # Получаем пользователя
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return orphaned_files
            
            # Проверяем аватарку
            avatar_path = user_dir / 'avatar.jpg'
            if avatar_path.exists() and not user.avatar:
                orphaned_files.append({
                    'type': 'orphaned_avatar',
                    'path': avatar_path,
                    'user_id': user_id,
                    'size': avatar_path.stat().st_size,
                    'reason': 'Avatar file exists but not referenced in user model'
                })
            
            # Проверяем другие файлы в папке пользователя
            for file_path in user_dir.rglob('*'):
                if file_path.is_file() and file_path != avatar_path:
                    # Дополнительная логика проверки других файлов пользователя
                    # может быть добавлена здесь при необходимости
                    pass
            
        except Exception:
            pass
        
        return orphaned_files
    
    def _check_team_directory_files(self, team_dir: Path, team_id: int) -> List[Dict[str, Any]]:
        """Проверка файлов команды."""
        orphaned_files = []
        
        try:
            # Проверяем документы команды
            documents_path = team_dir / 'documents'
            if documents_path.exists():
                for doc_file in documents_path.rglob('*'):
                    if doc_file.is_file():
                        # Логика проверки документов команды
                        # может быть добавлена здесь при необходимости
                        pass
            
        except Exception:
            pass
        
        return orphaned_files
    
    def _get_directory_size(self, path: Path) -> int:
        """Размер директории в байтах."""
        try:
            total_size = 0
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, IOError):
                        continue
            return total_size
        except Exception:
            return 0
    
    def find_orphaned_chapter_files(self) -> List[Dict[str, Any]]:
        """Осиротевшие файлы глав."""
        orphaned_files = []
        
        try:
            _, _, Project, _ = _get_models()
            if not Project:
                return orphaned_files
            
            # Получаем модель Chapter через импорт
            try:
                from projects.models import Chapter
            except ImportError:
                return orphaned_files
            
            # Получаем список всех активных глав с их проектами
            active_chapters = {}
            for chapter in Chapter.objects.select_related('project__team').all():
                team_id = chapter.project.team.id
                content_folder = chapter.project.content_folder
                chapter_id = chapter.id
                
                if team_id not in active_chapters:
                    active_chapters[team_id] = {}
                if content_folder not in active_chapters[team_id]:
                    active_chapters[team_id][content_folder] = set()
                
                active_chapters[team_id][content_folder].add(chapter_id)
            
            # Проверяем папки глав
            teams_path = self.media_root / 'teams'
            if not teams_path.exists():
                return orphaned_files
            
            for team_dir in teams_path.iterdir():
                if not team_dir.is_dir():
                    continue
                
                try:
                    team_id = int(team_dir.name)
                    projects_path = team_dir / 'projects'
                    
                    if not projects_path.exists():
                        continue
                    
                    # Проверяем каждую папку проекта
                    for project_dir in projects_path.iterdir():
                        if not project_dir.is_dir():
                            continue
                        
                        project_folder = project_dir.name
                        chapters_path = project_dir / 'chapters'
                        
                        if not chapters_path.exists():
                            continue
                        
                        # Проверяем каждую папку главы
                        for chapter_dir in chapters_path.iterdir():
                            if not chapter_dir.is_dir():
                                continue
                            
                            try:
                                chapter_id = int(chapter_dir.name)
                                
                                # Если глава не существует, помечаем папку как осиротевшую
                                if (team_id not in active_chapters or 
                                    project_folder not in active_chapters[team_id] or
                                    chapter_id not in active_chapters[team_id][project_folder]):
                                    
                                    orphaned_files.append({
                                        'type': 'chapter_directory',
                                        'path': chapter_dir,
                                        'team_id': team_id,
                                        'project_folder': project_folder,
                                        'chapter_id': chapter_id,
                                        'size': self._get_directory_size(chapter_dir),
                                        'reason': 'Chapter no longer exists'
                                    })
                                    
                            except (ValueError, OSError) as e:
                                continue
                        
                except (ValueError, OSError) as e:
                    continue
            
        except Exception as e:
            self.cleanup_stats['errors'].append(f"Chapter files scan error: {e}")
        
        return orphaned_files
    
    def cleanup_orphaned_files(self, dry_run: bool = True, 
                              file_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Очистить осиротевшие файлы.
        
        Args:
            dry_run: Если True, только показать что будет удалено
            file_types: Типы файлов для очистки (по умолчанию все)
            
        Returns:
            Dict[str, Any]: Результаты очистки
        """
        # Сброс статистики
        self.cleanup_stats = {
            'files_checked': 0,
            'orphaned_files_found': 0,
            'files_deleted': 0,
            'space_freed': 0,
            'errors': [],
            'dry_run': dry_run
        }
        
        try:
            all_orphaned_files = []
            
            # Определяем какие типы файлов проверять
            if file_types is None:
                file_types = ['user', 'team', 'project', 'chapter', 'image', 'temporary']
            
            # Поиск осиротевших файлов по типам
            if 'user' in file_types:
                all_orphaned_files.extend(self.find_orphaned_user_files())
            
            if 'team' in file_types:
                all_orphaned_files.extend(self.find_orphaned_team_files())
            
            if 'project' in file_types:
                all_orphaned_files.extend(self.find_orphaned_project_files())
            
            if 'chapter' in file_types:
                all_orphaned_files.extend(self.find_orphaned_chapter_files())
            
            if 'image' in file_types:
                all_orphaned_files.extend(self.find_orphaned_image_files())
            
            if 'temporary' in file_types:
                all_orphaned_files.extend(self.find_temporary_files())
            
            self.cleanup_stats['orphaned_files_found'] = len(all_orphaned_files)
            
            # Удаление файлов
            deleted_files = []
            for file_info in all_orphaned_files:
                try:
                    file_path = file_info['path']
                    file_size = file_info['size']
                    
                    if not dry_run:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                        
                        self.cleanup_stats['files_deleted'] += 1
                        self.cleanup_stats['space_freed'] += file_size
                    
                    deleted_files.append({
                        'path': str(file_path),
                        'type': file_info['type'],
                        'size': file_size,
                        'reason': file_info['reason'],
                        'deleted': not dry_run
                    })
                    
                except Exception as e:
                    error_msg = f"Error deleting {file_path}: {e}"
                    self.cleanup_stats['errors'].append(error_msg)
            
            # Логирование результатов
            if dry_run:
                pass
            
            return {
                'success': True,
                'statistics': self.cleanup_stats,
                'deleted_files': deleted_files,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"Error during orphaned file cleanup: {e}"
            self.cleanup_stats['errors'].append(error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'statistics': self.cleanup_stats,
                'timestamp': timezone.now().isoformat()
            }


# Глобальный экземпляр для использования в приложении
orphaned_cleanup = OrphanedFileCleanup()