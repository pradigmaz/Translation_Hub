"""CRUD операции для глав."""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView
from django.urls import reverse
import os
import re

from ..models import Project, Chapter
from ..forms import ChapterForm



class ProjectAccessMixin:
    """Миксин для проверки доступа к проекту через команду."""
    
    def dispatch(self, request, *args, **kwargs):
        """Проверяем доступ к проекту перед обработкой запроса"""
        # Получаем project_id из kwargs или через chapter
        project_id = kwargs.get('project_id')
        
        if project_id:
            # Оптимизированный запрос с select_related для избежания N+1
            self.project = get_object_or_404(
                Project.objects.select_related('team', 'team__creator'),
                pk=project_id
            )
        elif hasattr(self, 'get_object'):
            # Для DetailView - получаем через объект
            chapter = self.get_object()
            self.project = chapter.project
        
        # Проверяем доступ через команду
        if not self.project.user_has_access(request.user):
            raise PermissionDenied("У вас нет доступа к этому проекту")
        
        return super().dispatch(request, *args, **kwargs)


# ============================================================================
# DECORATORS
# ============================================================================

def require_project_access(view_func):
    """Декоратор для проверки доступа к проекту через команду."""
    from functools import wraps
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        project_id = kwargs.get('project_id')
        
        if not project_id:
            raise ValueError("require_project_access decorator requires 'project_id' in URL kwargs")
        
        # Оптимизированный запрос с select_related для избежания N+1
        project = get_object_or_404(
            Project.objects.select_related('team', 'team__creator'),
            pk=project_id
        )
        
        # Проверяем доступ через команду
        if not project.user_has_access(request.user):
            raise PermissionDenied("У вас нет доступа к этому проекту")
        
        # Добавляем проект в request для использования в view
        request.project = project
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def natural_sort_key(filename):
    """Преобразует строку в список для естественной сортировки"""
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', filename)]


def load_chapter_files(project, chapter):
    """Загружает список файлов главы, сгруппированных по папкам."""
    from utils.file_system import FilePathManager
    
    try:
        chapter_path = FilePathManager.get_chapter_path(
            project.team.id,
            project.content_folder,
            chapter.id
        )
        
        files_by_folder = {}
        folders = ['raw', 'translation', 'cleaning', 'typesetting', 'editing']
        
        for folder in folders:
            folder_path = os.path.join(chapter_path, folder)
            if not os.path.exists(folder_path):
                files_by_folder[folder] = []
                continue
            
            files = []
            filenames = sorted(os.listdir(folder_path), key=natural_sort_key)
            
            for filename in filenames:
                file_path = os.path.join(folder_path, filename)
                if os.path.isfile(file_path):
                    files.append({
                        'name': filename,
                        'path': f'{folder}/{filename}',
                        'size': os.path.getsize(file_path)
                    })
            
            files_by_folder[folder] = files
        
        return files_by_folder
        
    except Exception as e:
        return {}


def validate_comment_data(comment_text, file_path):
    """Валидирует данные комментария."""
    if not comment_text:
        return False, 'Комментарий не может быть пустым'
    
    if len(comment_text) > 1000:
        return False, 'Комментарий слишком длинный (максимум 1000 символов)'
    
    return True, None


class ChapterCreateView(LoginRequiredMixin, ProjectAccessMixin, CreateView):
    """CBV для создания новых глав"""
    model = Chapter
    form_class = ChapterForm
    template_name = 'projects/create_chapter.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.project
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        return context
    
    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception as e:
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('projects:project_detail', kwargs={'pk': self.project.pk})


class ChapterWorkspaceView(LoginRequiredMixin, ProjectAccessMixin, DetailView):
    """Workspace для работы над главой"""
    model = Chapter
    template_name = 'projects/chapter_workspace.html'
    context_object_name = 'chapter'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        
        # Загружаем файлы главы
        context['files_by_folder'] = load_chapter_files(self.project, self.object)
        context['current_file'] = None  # Будет установлен через JS
        
        # Права доступа к папкам
        context['folder_permissions'] = {
            'raw': {'upload': True, 'download': True, 'delete': True},
            'translation': {'upload': False, 'download': True, 'delete': False},
            'cleaning': {'upload': True, 'download': True, 'delete': True},
            'editing': {'upload': False, 'download': True, 'delete': False},
            'typesetting': {'upload': True, 'download': True, 'delete': True},
        }
        
        # Добавляем список разрешённых статусов для текущего пользователя
        context['allowed_statuses'] = self.object.get_allowed_transitions(self.request.user)
        
        # Добавляем комментарии к главе
        context['comments'] = self.object.comments.select_related('user').all()
        
        # Добавляем список участников команды для назначения исполнителя
        # Фильтруем ТОЛЬКО по роли текущего статуса (без Руководителя)
        required_role = self.object.STATUS_ROLE_MAP.get(self.object.status)
        
        if required_role:
            # Показываем только пользователей с нужной ролью
            # Руководитель может управлять, но не выполнять работу без соответствующей роли
            context['team_members'] = self.project.team.members.filter(
                teammembership__is_active=True,
                teammembership__roles__name=required_role
            ).distinct()
        else:
            # Если роль не требуется (raw, done), показываем всех
            context['team_members'] = self.project.team.members.filter(
                teammembership__is_active=True
            ).distinct()
        
        return context


@login_required
@require_project_access
@require_POST
def delete_chapter(request, project_id, chapter_id):
    """Удаление главы с полной очисткой файлов"""
    project = request.project
    chapter = get_object_or_404(Chapter, pk=chapter_id, project=project)
    
    try:
        chapter_id_for_log = chapter.id
        
        # Сохраняем информацию о пользователе для сигнала очистки файлов
        chapter._deleting_user_id = request.user.id
        
        # Удаляем главу из базы данных (сигнал автоматически очистит файлы)
        chapter.delete()
        
    except Exception as e:
        from utils.file_system import FileOperationLogger
    
    return redirect('projects:project_detail', pk=project_id)


@login_required
@require_project_access
@require_POST
def add_comment(request, project_id, chapter_id):
    project = request.project
    chapter = get_object_or_404(Chapter, pk=chapter_id, project=project)
    
    # Получаем текст комментария и путь к файлу
    comment_text = request.POST.get('comment_text', '').strip()
    file_path = request.POST.get('file_path', '').strip()
    
    # Валидация
    is_valid, error_message = validate_comment_data(comment_text, file_path)
    if not is_valid:
        return redirect('projects:chapter_workspace', project_id=project_id, pk=chapter_id)
    
    # Создание комментария
    try:
        from ..models import Comment
        Comment.objects.create(
            chapter=chapter,
            user=request.user,
            text=comment_text,
            file_path=file_path if file_path else None
        )
    except Exception:

        pass
    return redirect('projects:chapter_workspace', project_id=project_id, pk=chapter_id)


@login_required
@require_project_access
@require_POST
def delete_comment(request, project_id, chapter_id, comment_id):
    project = request.project
    chapter = get_object_or_404(Chapter, pk=chapter_id, project=project)
    
    from ..models import Comment
    comment = get_object_or_404(Comment, pk=comment_id, chapter=chapter)
    
    # Проверяем права на удаление (автор или Leader)
    if not comment.can_be_deleted_by(request.user):
        return redirect('projects:chapter_workspace', project_id=project_id, pk=chapter_id)
    
    try:
        comment.delete()
    except Exception:

        pass
    return redirect('projects:chapter_workspace', project_id=project_id, pk=chapter_id)
