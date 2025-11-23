from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View
from django.urls import reverse
from django.db.models import Q
import json
import os
import zipfile
from io import BytesIO

from ..models import Project, Chapter, ProjectMaterial
from ..forms import ProjectForm, ProjectEditForm, MaterialForm
from .chapter_crud import ProjectAccessMixin



# MIXINS

class ProjectPermissionMixin:
    """Миксин для проверки доступа к проекту"""
    
    def dispatch(self, request, *args, **kwargs):
        """Проверяем доступ к проекту перед обработкой запроса"""
        # Получаем pk проекта из kwargs
        project_pk = kwargs.get('pk')
        
        if not project_pk:
            raise ValueError("ProjectPermissionMixin requires 'pk' in URL kwargs")
        
        # Оптимизированный запрос с select_related для избежания N+1
        self.project = get_object_or_404(
            Project.objects.select_related('team', 'team__creator'),
            pk=project_pk
        )
        
        # Проверяем доступ через команду
        if not self.project.user_has_access(request.user):
            raise PermissionDenied("У вас нет доступа к этому проекту")
        
        return super().dispatch(request, *args, **kwargs)


class TeamAccessMixin:
    # Миксин для проверки доступа к команде при создании проекта
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем доступ к команде перед созданием проекта
        team_id = request.GET.get('team')
        
        if not team_id:
            return redirect('teams:team_list')
        
        # Проверяем доступ к команде
        try:
            from teams.models import Team
            self.selected_team = Team.objects.select_related('creator').get(
                id=team_id,
                status='active',
                members=request.user
            )
        except Team.DoesNotExist:
            return redirect('teams:team_list')
        
        return super().dispatch(request, *args, **kwargs)

class ProjectCreateView(LoginRequiredMixin, TeamAccessMixin, CreateView):
    # Создание нового проекта (только из команды)
    model = Project
    form_class = ProjectForm
    template_name = 'projects/create_project.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['selected_team'] = self.selected_team
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['selected_team'] = self.selected_team
        return context
    
    def form_valid(self, form):
        try:
            self.object = form.save()
            return redirect('teams:team_detail', pk=self.object.team.id)
        except Exception as e:
            return self.form_invalid(form)


class ProjectDetailView(LoginRequiredMixin, ProjectPermissionMixin, DetailView):
    # Детальная страница проекта
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    
    def get_queryset(self):
        return Project.objects.select_related('team', 'team__creator')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        
        # Получаем главы проекта с оптимизацией
        chapters = project.chapters.select_related('assignee').all().order_by('id')
        context['chapters'] = chapters
        
        # Подсчитываем статистику глав
        context['completed_count'] = chapters.filter(status='done').count()
        context['in_progress_count'] = chapters.exclude(status__in=['raw', 'done']).count()
        
        # Проверяем является ли пользователь руководителем команды
        context['is_leader'] = project.team.members.filter(
            id=self.request.user.id,
            teammembership__roles__name='Руководитель',
            teammembership__is_active=True
        ).exists()
        
        # Получаем доступные статьи базы знаний
        from glossary.models import GlossaryTerm
        context['available_articles'] = GlossaryTerm.objects.filter(
            Q(category__content_type=project.project_type) | Q(category__content_type='general'),
            is_active=True
        ).filter(
            Q(category__scope='global') |
            Q(category__scope='user', created_by=self.request.user) |
            Q(category__scope='project', project=project)
        ).select_related('category', 'created_by').order_by('term')
        
        # Получаем материалы проекта
        context['materials'] = project.materials.select_related('created_by').all()
        
        return context


class ProjectListView(LoginRequiredMixin, ListView):
    """Список проектов пользователя"""
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    
    def get_queryset(self):
        return Project.objects.filter(
            team__members=self.request.user,
            team__status='active'
        ).select_related('team').order_by('-created_at')


class ProjectUpdateView(LoginRequiredMixin, ProjectPermissionMixin, UpdateView):
    """Редактирование проекта (только руководитель команды)"""
    model = Project
    form_class = ProjectEditForm
    template_name = 'projects/edit_project.html'
    context_object_name = 'project'
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        # Проверяем что пользователь - руководитель команды
        is_leader = self.project.team.members.filter(
            id=request.user.id,
            teammembership__roles__name='Руководитель',
            teammembership__is_active=True
        ).exists()
        
        if not is_leader:
            raise PermissionDenied("Только руководитель команды может редактировать проект")
        
        return response
    
    def get_queryset(self):
        return Project.objects.select_related('team', 'team__creator')
    
    def form_valid(self, form):
        try:
            self.object = form.save()
            return redirect('projects:project_detail', pk=self.object.pk)
        except Exception as e:
            return self.form_invalid(form)


class ProjectDeleteView(LoginRequiredMixin, ProjectPermissionMixin, View):
    """Удаление проекта с полной очисткой данных (AJAX, только руководитель)"""
    
    def get_queryset(self):
        return Project.objects.select_related('team', 'team__creator')
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        # Проверяем что пользователь - руководитель команды
        is_leader = self.project.team.members.filter(
            id=request.user.id,
            teammembership__roles__name='Руководитель',
            teammembership__is_active=True
        ).exists()
        
        if not is_leader:
            raise PermissionDenied("Только руководитель команды может удалять проект")
        
        return response
    
    def post(self, request, *args, **kwargs):
        from utils.file_system import FileCleanupManager, FileCleanupError
        
        project = get_object_or_404(
            self.get_queryset(),
            pk=kwargs.get('pk')
        )
        

        
        try:
            project_title = project.title
            team_id = project.team.id
            content_folder = project.content_folder
            
            # Используем систему очистки файлов
            if content_folder:
                try:
                    FileCleanupManager.cleanup_project_files(team_id, content_folder)
                except Exception:

                    pass
            # Удаляем проект из БД
            project.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Проект "{project_title}" успешно удален',
                'redirect_url': f'/teams/{team_id}/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Ошибка при удалении проекта: {str(e)}'
            }, status=500)


class ProjectDownloadView(LoginRequiredMixin, ProjectPermissionMixin, View):
    """Скачивание архива с данными проекта"""
    
    def get(self, request, *args, **kwargs):
        # Используем self.project из миксина
        project = self.project
        
        try:
            # Создаем архив в памяти
            zip_buffer = BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Информация о проекте
                project_info = {
                    'title': project.title,
                    'description': project.description,
                    'team': project.team.name,
                    'project_type': project.get_project_type_display(),
                    'age_rating': project.get_age_rating_display(),
                    'status': project.get_status_display(),
                    'created_at': project.created_at.isoformat(),
                    'content_folder': project.content_folder,
                }
                
                # Информация о главах
                chapters_data = []
                for chapter in project.chapters.select_related('assignee').all():
                    chapter_info = {
                        'title': chapter.title,
                        'status': chapter.get_status_display(),
                        'assignee': chapter.assignee.username if chapter.assignee else None,
                        'created_at': chapter.created_at.isoformat(),
                    }
                    chapters_data.append(chapter_info)
                
                project_info['chapters'] = chapters_data
                
                # Сохраняем JSON
                zip_file.writestr('project_info.json', json.dumps(project_info, ensure_ascii=False, indent=2))
                
                # Добавляем файлы контента
                if project.content_folder:
                    from django.conf import settings
                    content_path = os.path.join(settings.BASE_DIR, 'content', 'projects', str(project.team.id), project.content_folder)
                    
                    if os.path.exists(content_path):
                        for root, dirs, files in os.walk(content_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, content_path)
                                zip_file.write(file_path, f'content/{arcname}')
            
            zip_buffer.seek(0)
            
            # HTTP ответ с архивом
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            filename = f"project_{project.id}_{project.title.replace(' ', '_')}.zip"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return redirect('projects:edit_project', pk=project.pk)

class MaterialCreateView(LoginRequiredMixin, ProjectPermissionMixin, CreateView):
    """Создание материала для проекта"""
    model = ProjectMaterial
    form_class = MaterialForm
    template_name = 'projects/material_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['action'] = 'create'
        return context
    
    def form_valid(self, form):
        try:
            material = form.save(commit=False)
            material.project = self.project
            material.created_by = self.request.user
            material.save()
            return redirect('projects:project_detail', pk=self.project.pk)
        except Exception as e:
            return self.form_invalid(form)


class MaterialUpdateView(LoginRequiredMixin, ProjectPermissionMixin, UpdateView):
    """Редактирование материала"""
    model = ProjectMaterial
    form_class = MaterialForm
    template_name = 'projects/material_form.html'
    pk_url_kwarg = 'material_id'
    
    def get_queryset(self):
        return ProjectMaterial.objects.filter(project=self.project)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.project
        context['material'] = self.object
        context['action'] = 'edit'
        return context
    
    def form_valid(self, form):
        try:
            self.object = form.save()
            return redirect('projects:project_detail', pk=self.project.pk)
        except Exception as e:
            return self.form_invalid(form)


class MaterialDeleteView(LoginRequiredMixin, ProjectPermissionMixin, View):
    """Удаление материала (AJAX)"""
    
    def post(self, request, *args, **kwargs):
        material = get_object_or_404(
            ProjectMaterial,
            pk=kwargs.get('material_id'),
            project=self.project
        )
        
        try:
            material_title = material.title
            material.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Материал "{material_title}" успешно удален'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Ошибка при удалении материала: {str(e)}'
            }, status=500)
