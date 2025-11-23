# projects/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from .models import Project, Chapter, ProjectMaterial, ProjectStatus
from .utils import generate_content_folder


class ProjectForm(forms.ModelForm):
    """Форма для создания/редактирования проектов манги/манхвы"""
    
    class Meta:
        model = Project
        fields = ['title', 'description', 'team', 'project_type', 'age_rating', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название проекта'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание проекта (необязательно)'
            }),
            'team': forms.Select(attrs={
                'class': 'form-select'
            }),
            'project_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'age_rating': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, user=None, selected_team=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.selected_team = selected_team
        
        # Если команда предопределена, скрываем поле выбора команды
        if selected_team:
            self.fields['team'].widget = forms.HiddenInput()
            self.fields['team'].initial = selected_team
        else:
            # Ограничиваем команды только активными командами пользователя
            if user:
                from teams.models import Team
                self.fields['team'].queryset = Team.objects.filter(
                    members=user,
                    status='active'
                ).distinct()
        
        # Делаем поля обязательными
        self.fields['title'].required = True
        self.fields['project_type'].required = True
        self.fields['age_rating'].required = True
        
        # Команда обязательна только если не предопределена
        self.fields['team'].required = not bool(selected_team)
        
        # Добавляем help_text для статуса проекта
        self.fields['status'].help_text = (
            '<strong>Переводим</strong> - активная работа над проектом, '
            '<strong>Переведён</strong> - все главы готовы, '
            '<strong>Заморожен</strong> - временная приостановка, '
            '<strong>Заброшен</strong> - работа прекращена'
        )
    
    def clean_title(self):
        """Валидация названия проекта - минимум 3 символа"""
        title = self.cleaned_data.get('title')
        if not title or len(title.strip()) < 3:
            raise ValidationError('Название должно содержать минимум 3 символа')
        return title.strip()
    
    def clean_status(self):
        """Валидация статуса проекта"""
        status = self.cleaned_data.get('status')
        valid_statuses = [choice[0] for choice in ProjectStatus.choices]
        
        if status and status not in valid_statuses:
            raise ValidationError('Выберите корректный статус проекта')
        
        return status
    
    def clean(self):
        """Общая валидация формы"""
        cleaned_data = super().clean()
        
        # Если команда предопределена, используем её
        if self.selected_team:
            cleaned_data['team'] = self.selected_team
        
        return cleaned_data
    
    def save(self, commit=True):
        """Переопределяем метод save для автогенерации content_folder"""
        instance = super().save(commit=False)
        
        # Проверяем, является ли это новым проектом
        is_new_project = instance.pk is None
        
        # Убеждаемся что команда установлена
        if self.selected_team and not instance.team:
            instance.team = self.selected_team
        
        # Автогенерируем папку если её нет
        if not instance.content_folder and instance.team:
            try:
                instance.content_folder = generate_content_folder(
                    instance.title, 
                    instance.team,  # Передаем команду для изоляции
                    instance.id
                )
            except Exception as e:
                raise ValidationError(f'Ошибка генерации папки: {str(e)}')
        
        if commit:
            instance.save()
            # Создаем первую главу автоматически только для новых проектов
            if is_new_project:
                instance.create_first_chapter()
        return instance


class ProjectEditForm(forms.ModelForm):
    """Упрощенная форма для редактирования только изменяемых параметров проекта"""
    
    class Meta:
        model = Project
        fields = ['title', 'description', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название проекта'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание проекта (необязательно)'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Делаем поле title обязательным
        self.fields['title'].required = True
        
        # Добавляем пользовательские подписи для полей
        self.fields['title'].label = 'Название проекта'
        self.fields['description'].label = 'Описание'
        self.fields['status'].label = 'Статус проекта'
        
        # Добавляем help_text для пояснений
        self.fields['title'].help_text = 'Минимум 3 символа'
        self.fields['description'].help_text = 'Необязательное поле'
        self.fields['status'].help_text = (
            '<strong>Переводим</strong> - активная работа над проектом, '
            '<strong>Переведён</strong> - все главы готовы, '
            '<strong>Заморожен</strong> - временная приостановка, '
            '<strong>Заброшен</strong> - работа прекращена'
        )
    
    def clean_title(self):
        """Валидация названия проекта - минимум 3 символа"""
        title = self.cleaned_data.get('title')
        if not title or len(title.strip()) < 3:
            raise ValidationError('Название должно содержать минимум 3 символа')
        return title.strip()
    
    def clean_status(self):
        """Валидация статуса проекта"""
        status = self.cleaned_data.get('status')
        valid_statuses = [choice[0] for choice in ProjectStatus.choices]
        
        if status and status not in valid_statuses:
            raise ValidationError('Выберите корректный статус проекта')
        
        return status
    
    def clean(self):
        """Общая валидация формы"""
        cleaned_data = super().clean()
        
        # Дополнительная проверка на пустое название после обрезки пробелов
        title = cleaned_data.get('title')
        if title and not title.strip():
            raise ValidationError({'title': 'Название не может состоять только из пробелов'})
        
        return cleaned_data


class ChapterForm(forms.ModelForm):
    """Форма для создания новых глав"""
    
    class Meta:
        model = Chapter
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название главы (например: Глава 2)'
            })
        }
    
    def __init__(self, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        
        # Делаем поле обязательным
        self.fields['title'].required = True
        self.fields['title'].label = 'Название главы'
        self.fields['title'].help_text = 'Минимум 3 символа'
    
    def clean_title(self):
        """Валидация названия главы"""
        title = self.cleaned_data.get('title')
        if not title or len(title.strip()) < 3:
            raise ValidationError('Название должно содержать минимум 3 символа')
        
        # Проверяем уникальность названия в рамках проекта
        if self.project:
            existing_chapter = self.project.chapters.filter(title=title.strip()).first()
            if existing_chapter:
                raise ValidationError('Глава с таким названием уже существует в проекте')
        
        return title.strip()
    
    def save(self, commit=True):
        """Переопределяем метод save для установки проекта"""
        instance = super().save(commit=False)
        
        if self.project:
            instance.project = self.project
        
        if commit:
            instance.save()
            
            # Создаем структуру папок для новой главы
            try:
                from utils.file_system import DirectoryManager
                DirectoryManager.create_chapter_directory(
                    instance.project.team.id,
                    instance.project.content_folder,
                    instance.id
                )
            except Exception:
                pass
        
        return instance


class FileUploadForm(forms.Form):
    """Форма для загрузки файлов в папки главы"""
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.jpg,.jpeg,.png,.gif,.pdf,.txt,.doc,.docx,.zip,.rar'
        }),
        help_text='Максимальный размер файла: 50MB. Поддерживаемые форматы: изображения, документы, архивы'
    )
    
    folder = forms.ChoiceField(
        choices=[
            ('raw', 'RAW - Исходные материалы'),
            ('translation', 'Translation - Переводы'),
            ('cleaning', 'Cleaning - Очистка'),
            ('typesetting', 'Typesetting - Тайпинг'),
            ('editing', 'Editing - Редактура'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Папка назначения'
    )
    
    def clean_file(self):
        """Валидация загружаемого файла"""
        uploaded_file = self.cleaned_data.get('file')
        
        if not uploaded_file:
            raise ValidationError('Файл не выбран')
        
        # Проверка размера файла (50MB максимум)
        max_size = 50 * 1024 * 1024  # 50MB в байтах
        if uploaded_file.size > max_size:
            raise ValidationError(f'Размер файла слишком большой. Максимум: {max_size // (1024*1024)}MB')
        
        # Проверка типа файла по расширению
        allowed_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',  # Изображения
            '.pdf', '.txt', '.doc', '.docx', '.rtf',          # Документы
            '.zip', '.rar', '.7z', '.tar', '.gz'              # Архивы
        ]
        
        filename = uploaded_file.name.lower()
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise ValidationError(
            )
        
        # Проверка имени файла на безопасность
        if not self._is_safe_filename(uploaded_file.name):
            raise ValidationError('Недопустимое имя файла. Используйте только латинские буквы, цифры, дефисы и подчеркивания')
        
        return uploaded_file
    
    def clean_folder(self):
        """Валидация папки назначения"""
        folder = self.cleaned_data.get('folder')
        valid_folders = ['raw', 'translation', 'cleaning', 'typesetting', 'editing']
        
        if folder not in valid_folders:
            raise ValidationError('Недопустимая папка назначения')
        
        return folder
    
    def _is_safe_filename(self, filename):
        """Проверка безопасности имени файла"""
        import re
        # Разрешаем только латинские буквы, цифры, дефисы, подчеркивания и точки
        safe_pattern = re.compile(r'^[a-zA-Z0-9._-]+$')
        return safe_pattern.match(filename) is not None



class MaterialForm(forms.ModelForm):
    """Форма для создания/редактирования материалов проекта"""
    
    class Meta:
        model = ProjectMaterial
        fields = ['title', 'material_type', 'content', 'order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название материала'
            }),
            'material_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Содержимое материала'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = True
        self.fields['content'].required = True
        self.fields['order'].required = False
        self.fields['order'].initial = 1
        self.fields['order'].help_text = 'Меньшее число = выше в списке (по умолчанию 1)'
    
    def clean_title(self):
        """Валидация названия"""
        title = self.cleaned_data.get('title')
        if not title or len(title.strip()) < 3:
            raise ValidationError('Название должно содержать минимум 3 символа')
        return title.strip()
    
    def clean_content(self):
        """Валидация содержимого"""
        content = self.cleaned_data.get('content')
        if not content or len(content.strip()) < 10:
            raise ValidationError('Содержимое должно содержать минимум 10 символов')
        return content.strip()
