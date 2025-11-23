"""Файловые операции для глав."""
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
import os
import json
import zipfile
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Dict, Any

from ..models import Project, Chapter
from .chapter_crud import require_project_access

def _validate_upload_request(folder: str, uploaded_files: List) -> Tuple[bool, str]:
    """Валидирует параметры запроса на загрузку файлов."""
    if not folder:
        return False, 'Folder parameter is required'
    
    if not uploaded_files:
        return False, 'No files uploaded'
    
    return True, ''


def _process_single_file(uploaded_file, folder_path: Path, user_id: int, 
                        project, chapter) -> Tuple[str, str]:
    # Обрабатывает загрузку одного файла.
    from utils.file_system import (
        FileUploadHandler, 
        FileValidationError,
        FileOperationLogger
    )
    
    try:
        # Валидация файла
        FileUploadHandler.validate_file(uploaded_file)
        
        file_path = folder_path / uploaded_file.name
        
        # Проверяем, что файл с таким именем не существует
        if file_path.exists():
            return 'skipped', uploaded_file.name
        
        # Сохраняем файл
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Логируем операцию
        
        return 'success', ''
        
    except FileValidationError as e:
        return 'error', f"{uploaded_file.name}: {str(e)}"
    except Exception as e:
        return 'error', f"{uploaded_file.name}: Ошибка сохранения"


def _handle_raw_folder_upload(folder: str, uploaded_count: int, 
                              chapter_path: Path, user_id: int) -> int:
    # Обрабатывает автогенерацию файлов для переводчика после загрузки RAW.
    from utils.file_system import FilePathManager, FileOperationLogger
    
    if folder != 'raw' or uploaded_count == 0:
        return 0
    
    try:
        return FilePathManager.generate_translation_files(chapter_path)
    except Exception as e:
        return 0


def _build_upload_response(uploaded_count: int, skipped_files: List[str], 
                          errors: List[str], translation_files_created: int,
                          folder: str, file_count: int) -> Dict[str, Any]:
    # Формирует JSON ответ для загрузки файлов.
    message_parts = []
    
    if uploaded_count > 0:
        message_parts.append(f'Загружено файлов: {uploaded_count}')
    if translation_files_created > 0:
        message_parts.append(f'Создано файлов для перевода: {translation_files_created}')
    if skipped_files:
        message_parts.append(f'Пропущено (уже существуют): {len(skipped_files)}')
    if errors:
        message_parts.append(f'Ошибок: {len(errors)}')
    
    return {
        'success': uploaded_count > 0,
        'message': ' | '.join(message_parts),
        'uploaded_count': uploaded_count,
        'translation_files_created': translation_files_created,
        'skipped_files': skipped_files,
        'errors': errors,
        'folder': folder,
        'file_count': file_count
    }


@login_required
@require_project_access
def upload_file(request, project_id, chapter_id):
    """API для загрузки файлов в папки главы (поддержка множественной загрузки)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    project = request.project
    chapter = get_object_or_404(Chapter, id=chapter_id, project=project)
    
    # Валидация запроса
    folder = request.POST.get('folder')
    uploaded_files = request.FILES.getlist('file')
    
    is_valid, error_message = _validate_upload_request(folder, uploaded_files)
    if not is_valid:
        return JsonResponse({'error': error_message}, status=400)
    
    try:
        from utils.file_system import (
            FilePathManager, 
            DirectoryManager, 
            FileOperationLogger
        )
        
        # Получаем путь к папке главы
        chapter_path = FilePathManager.get_chapter_path(
            project.team.id, 
            project.content_folder, 
            chapter.id
        )
        
        folder_path = chapter_path / folder
        
        # Создаем папку если не существует
        DirectoryManager.ensure_directory_exists(folder_path, request.user.id)
        
        # Обрабатываем каждый файл
        uploaded_count = 0
        skipped_files = []
        errors = []
        
        for uploaded_file in uploaded_files:
            status, message = _process_single_file(
                uploaded_file, folder_path, request.user.id, project, chapter
            )
            
            if status == 'success':
                uploaded_count += 1
            elif status == 'skipped':
                skipped_files.append(message)
            elif status == 'error':
                errors.append(message)
        
        # Получаем обновленный счетчик файлов в папке
        file_count = len([f for f in folder_path.iterdir() if f.is_file()])
        
        # Автогенерация файлов для переводчика после загрузки RAW
        translation_files_created = _handle_raw_folder_upload(
            folder, uploaded_count, chapter_path, request.user.id
        )
        
        # Формируем ответ
        return JsonResponse(_build_upload_response(
            uploaded_count, skipped_files, errors, 
            translation_files_created, folder, file_count
        ))
        
    except Exception as e:
        from utils.file_system import FileOperationLogger
        return JsonResponse({
            'error': 'Upload failed',
            'details': [f'Ошибка при загрузке файла: {str(e)}']
        }, status=500)

def _validate_folder(folder: str) -> bool:
    """Валидирует название папки."""
    valid_folders = ['raw', 'translation', 'cleaning', 'typesetting', 'editing']
    if folder not in valid_folders:
        raise PermissionDenied("Invalid folder")
    return True


def _get_file_path(project, chapter, folder: str, filename: str) -> Path:
    """Получает путь к файлу и проверяет его существование."""
    from utils.file_system import FilePathManager
    
    chapter_path = FilePathManager.get_chapter_path(
        project.team.id, 
        project.content_folder, 
        chapter.id
    )
    
    file_path = chapter_path / folder / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError("File not found")
    
    return file_path


def _delete_file_with_translation(file_path: Path, folder: str, filename: str,
                                  chapter_path: Path, user_id: int, 
                                  project, chapter) -> Tuple[bool, int]:
    # Удаляет файл и связанный файл перевода (если это RAW).
    from utils.file_system import FilePathManager, FileOperationLogger
    
    os.remove(file_path)
    
    # Логируем удаление
    
    # Синхронное удаление файла перевода при удалении RAW
    translation_deleted = False
    if folder == 'raw':
        try:
            translation_deleted = FilePathManager.delete_translation_file(chapter_path, filename)
        except Exception:

            pass
    # Получаем обновленный счетчик файлов в папке
    folder_path = chapter_path / folder
    file_count = len([f for f in folder_path.iterdir() if f.is_file()])
    
    return translation_deleted, file_count

@login_required
@require_project_access
@require_http_methods(["GET", "DELETE"])
def download_file(request, project_id, chapter_id, folder, filename):
    # API для скачивания и удаления файлов из папок главы
    project = request.project
    chapter = get_object_or_404(Chapter, id=chapter_id, project=project)
    
    # DELETE запрос - удаление файла
    if request.method == 'DELETE':
        return delete_file(request, project_id, chapter_id, folder, filename)
    
    # GET запрос - скачивание файла
    try:
        _validate_folder(folder)
        file_path = _get_file_path(project, chapter, folder, filename)
        
        # Скачивание файла
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except FileNotFoundError:
        return JsonResponse({'error': 'File not found'}, status=404)
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
    except Exception as e:
        from utils.file_system import FileOperationLogger
        return JsonResponse({'error': 'Download failed'}, status=500)


def delete_file(request, project_id, chapter_id, folder, filename):
    # API для удаления файлов из папок главы
    project = request.project
    chapter = get_object_or_404(Chapter, id=chapter_id, project=project)
    
    try:
        from utils.file_system import FilePathManager, FileOperationLogger
        
        _validate_folder(folder)
        file_path = _get_file_path(project, chapter, folder, filename)
        
        chapter_path = FilePathManager.get_chapter_path(
            project.team.id, 
            project.content_folder, 
            chapter.id
        )
        
        # Удаление файла
        translation_deleted, file_count = _delete_file_with_translation(
            file_path, folder, filename, chapter_path, 
            request.user.id, project, chapter
        )
        
        message = f'Файл "{filename}" успешно удалён'
        if translation_deleted:
            message += ' (включая файл перевода)'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'file_count': file_count,
            'translation_deleted': translation_deleted
        })
        
    except FileNotFoundError:
        return JsonResponse({'error': 'File not found'}, status=404)
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
    except Exception as e:
        from utils.file_system import FileOperationLogger
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при удалении файла: {str(e)}'
        }, status=500)


@login_required
@require_project_access
@require_http_methods(["GET"])
def download_chapter_archive(request, project_id, chapter_id):
    # Скачивание архива главы со всеми файлами
    project = request.project
    chapter = get_object_or_404(Chapter, id=chapter_id, project=project)
    
    try:
        from utils.file_system import FilePathManager
        
        chapter_path = FilePathManager.get_chapter_path(
            project.team.id,
            project.content_folder,
            chapter.id
        )
        
        if not chapter_path.exists():
            return JsonResponse({'error': 'Chapter folder not found'}, status=404)
        
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            chapter_info = {
                'project': project.title,
                'chapter': chapter.title,
                'status': chapter.get_status_display(),
                'assignee': chapter.assignee.username if chapter.assignee else None,
                'created_at': chapter.created_at.isoformat(),
                'team': project.team.name,
            }
            
            zip_file.writestr('chapter_info.json', json.dumps(chapter_info, ensure_ascii=False, indent=2))
            
            folders = ['raw', 'translation', 'cleaning', 'typesetting', 'editing']
            
            for folder in folders:
                folder_path = chapter_path / folder
                if folder_path.exists() and folder_path.is_dir():
                    for file_path in folder_path.iterdir():
                        if file_path.is_file():
                            arcname = f'{folder}/{file_path.name}'
                            zip_file.write(file_path, arcname)
        
        zip_buffer.seek(0)
        
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        safe_chapter_title = chapter.title.replace(' ', '_').replace('/', '_')
        filename = f"chapter_{chapter.id}_{safe_chapter_title}.zip"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': f'Archive creation failed: {str(e)}'}, status=500)
