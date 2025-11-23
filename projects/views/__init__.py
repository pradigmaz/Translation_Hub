"""
Projects views package - модульная структура для лучшей организации кода
"""

# Project CRUD
from .project_crud import (
    ProjectCreateView,
    ProjectDetailView,
    ProjectListView,
    ProjectUpdateView,
    ProjectDeleteView,
    ProjectDownloadView,
    MaterialCreateView,
    MaterialUpdateView,
    MaterialDeleteView,
)

# Chapter CRUD
from .chapter_crud import (
    ChapterCreateView,
    ChapterWorkspaceView,
    delete_chapter,
    add_comment,
    delete_comment,
)

# File Operations
from .file_operations import (
    upload_file,
    download_file,
    delete_file,
    download_chapter_archive,
)

# API Views
from .api_views import (
    chapter_file_counts,
    chapter_files,
    save_translation,
    update_chapter_status,
)

__all__ = [
    # Project CRUD
    'ProjectCreateView',
    'ProjectDetailView',
    'ProjectListView',
    'ProjectUpdateView',
    'ProjectDeleteView',
    'ProjectDownloadView',
    'MaterialCreateView',
    'MaterialUpdateView',
    'MaterialDeleteView',
    # Chapter CRUD
    'ChapterCreateView',
    'ChapterWorkspaceView',
    'delete_chapter',
    'add_comment',
    'delete_comment',
    # File Operations
    'upload_file',
    'download_file',
    'delete_file',
    'download_chapter_archive',
    # API Views
    'chapter_file_counts',
    'chapter_files',
    'save_translation',
    'update_chapter_status',
]
