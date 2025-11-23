"""
API views for projects and chapters
"""
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import os

from ..models import Project, Chapter, ChapterStatus
from .chapter_crud import require_project_access



@login_required
@require_project_access
def chapter_file_counts(request, project_id, chapter_id):
    """API для получения счетчиков файлов главы"""
    project = request.project
    chapter = get_object_or_404(Chapter, id=chapter_id, project=project)
    
    try:
        from utils.file_system import FilePathManager
        
        # Получаем путь к папке главы
        chapter_path = FilePathManager.get_chapter_path(
            project.team.id, 
            project.content_folder, 
            chapter.id
        )
        
        # Подсчитываем файлы в каждой папке
        folders = ['raw', 'translation', 'cleaning', 'typesetting', 'editing']
        counts = {}
        
        for folder in folders:
            folder_path = chapter_path / folder
            if folder_path.exists() and folder_path.is_dir():
                # Подсчитываем только файлы (не папки)
                file_count = len([f for f in folder_path.iterdir() if f.is_file()])
                counts[folder] = file_count
            else:
                counts[folder] = 0
        
        return JsonResponse({
            'success': True,
            'counts': counts,
            'chapter': chapter.title
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при получении счетчиков файлов: {str(e)}'
        }, status=500)


@login_required
@require_project_access
def chapter_files(request, project_id, chapter_id):
    """API для получения списка файлов главы"""
    project = request.project
    chapter = get_object_or_404(Chapter, id=chapter_id, project=project)
    
    folder = request.GET.get('folder', 'raw')
    
    # Валидируем папку
    valid_folders = ['raw', 'translation', 'cleaning', 'typesetting', 'editing']
    if folder not in valid_folders:
        return JsonResponse({'success': False, 'error': 'Invalid folder'}, status=400)
    
    try:
        from utils.file_system import FilePathManager
        
        # Получаем путь к папке главы
        chapter_path = FilePathManager.get_chapter_path(
            project.team.id, 
            project.content_folder, 
            chapter.id
        )
        
        folder_path = chapter_path / folder
        files = []
        
        if folder_path.exists() and folder_path.is_dir():
            for file_path in folder_path.iterdir():
                if file_path.is_file():
                    # Получаем информацию о файле
                    stat = file_path.stat()
                    files.append({
                        'name': file_path.name,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'url': f'/projects/{project_id}/chapters/{chapter_id}/download/{folder}/{file_path.name}/'
                    })
        
        # Сортируем файлы по имени
        files.sort(key=lambda x: x['name'])
        
        return JsonResponse({
            'success': True,
            'files': files,
            'folder': folder,
            'chapter': chapter.title
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при получении списка файлов: {str(e)}'
        }, status=500)


@login_required
@require_project_access
@require_POST
def save_translation(request, project_id, chapter_id):
    """Сохранение текста перевода"""
    project = request.project
    chapter = get_object_or_404(Chapter, pk=chapter_id, project=project)
    
    try:
        data = json.loads(request.body)
        file_path = data.get('file_path')
        content = data.get('content', '')
        
        if not file_path:
            return JsonResponse({'success': False, 'error': 'Не указан файл'}, status=400)
        
        # Формируем полный путь к файлу
        from utils.file_system import FilePathManager
        chapter_path = FilePathManager.get_chapter_path(
            project.team.id,
            project.content_folder,
            chapter.id
        )
        full_path = os.path.join(chapter_path, file_path)
        
        # Проверяем, что путь безопасен (не выходит за пределы главы)
        if not os.path.abspath(full_path).startswith(os.path.abspath(chapter_path)):
            return JsonResponse({'success': False, 'error': 'Недопустимый путь'}, status=400)
        
        # Создаём директорию если не существует
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Сохраняем файл
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return JsonResponse({'success': True, 'message': 'Перевод сохранён'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_project_access
@require_POST
def update_chapter_status(request, project_id, chapter_id):
    """Смена статуса главы или назначение исполнителя"""
    project = request.project
    chapter = get_object_or_404(Chapter, pk=chapter_id, project=project)
    
    try:
        data = json.loads(request.body)
        
        # Обработка назначения исполнителя
        if 'assignee_id' in data:
            assignee_id = data.get('assignee_id')
            
            if assignee_id:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                assignee = get_object_or_404(User, pk=assignee_id)
                
                # Проверяем что пользователь в команде
                if not project.team.members.filter(id=assignee.id, teammembership__is_active=True).exists():
                    return JsonResponse({'success': False, 'error': 'Пользователь не в команде'}, status=403)
                
                chapter.assignee = assignee
            else:
                chapter.assignee = None
            
            chapter.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Исполнитель назначен'
            })
        
        # Обработка смены статуса
        new_status = data.get('status')
        
        # Проверяем валидность статуса
        valid_statuses = [choice[0] for choice in ChapterStatus.choices]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Недопустимый статус'}, status=400)
        
        # Проверяем возможность перехода (workflow enforcement)
        can_transition, error_message = chapter.can_transition_to(new_status, request.user)
        if not can_transition:
            return JsonResponse({'success': False, 'error': error_message}, status=403)
        
        # Автоназначение исполнителя, если не назначен
        if chapter.assignee is None:
            chapter.assignee = request.user
        
        # Сбрасываем исполнителя в двух случаях:
        # 1. При возврате на предыдущий этап
        # 2. При переходе в статус "done" (задача завершена)
        old_status = chapter.status
        if old_status != new_status:
            # Если переходим в done - сбрасываем assignee
            if new_status == 'done':
                chapter.assignee = None
            else:
                # Если возвращаем назад (например, с editing на translating)
                status_order = ['raw', 'translating', 'cleaning', 'editing', 'typesetting', 'done']
                try:
                    old_idx = status_order.index(old_status)
                    new_idx = status_order.index(new_status)
                    if new_idx < old_idx:  # Возврат назад
                        chapter.assignee = None
                except ValueError:
                    pass
        
        # Обновляем статус
        chapter.status = new_status
        chapter.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Статус изменён на "{chapter.get_status_display()}"',
            'status': new_status,
            'status_display': chapter.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
