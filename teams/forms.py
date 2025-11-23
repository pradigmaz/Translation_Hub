"""
Формы для управления участниками команды.

Этот модуль содержит формы для поиска пользователей, добавления участников
и управления ролями в команде.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Role, TeamMembership, Team

User = get_user_model()


class TeamForm(forms.ModelForm):
    """
    Форма создания и редактирования команды с валидацией данных.
    
    Включает валидацию названия команды на длину, допустимые символы
    и уникальность для пользователя. При создании команды требует выбора
    хотя бы одной дополнительной роли для руководителя.
    """
    
    role_ids = forms.ModelMultipleChoiceField(
        queryset=Role.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Ваши роли в команде',
        help_text='Выберите хотя бы одну роль (роль "Руководитель" назначается автоматически)',
        required=True
    )

    class Meta:
        model = Team
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Название команды",
                    "maxlength": "100",
                }
            )
        }
    
    def __init__(self, *args, **kwargs):
        """
        Инициализация формы с настройкой доступных ролей.
        
        Исключает роли "Руководитель" и "Пользователь" из выбора,
        так как "Руководитель" назначается автоматически.
        """
        super().__init__(*args, **kwargs)
        
        # Настраиваем queryset для ролей
        if not self.instance.pk:
            # При создании команды показываем доступные роли
            self.fields['role_ids'].queryset = Role.objects.exclude(
                name__in=['Руководитель', 'Пользователь']
            ).order_by('name')
            self.fields['role_ids'].required = True
        else:
            # При редактировании команды убираем поле ролей
            self.fields.pop('role_ids', None)

    def clean_name(self):
        """
        Валидация поля названия команды.
        
        Returns:
            str: Очищенное название команды
            
        Raises:
            forms.ValidationError: При некорректном названии
        """
        name = self.cleaned_data.get("name")

        if not name or len(name.strip()) < 3:
            raise forms.ValidationError(
                "Название команды должно содержать минимум 3 символа"
            )

        if len(name) > 100:
            raise forms.ValidationError(
                "Название команды не может быть длиннее 100 символов"
            )

        # Проверка допустимых символов
        if not name.replace(" ", "").replace("-", "").replace("_", "").isalnum():
            raise forms.ValidationError(
                "Название может содержать только буквы, цифры, пробелы, дефисы и подчеркивания"
            )

        return name.strip()
    
    def clean_role_ids(self):
        """
        Валидация выбранных ролей при создании команды.
        
        Returns:
            QuerySet: Выбранные роли
            
        Raises:
            forms.ValidationError: Если роли не выбраны при создании команды
        """
        role_ids = self.cleaned_data.get('role_ids')
        
        # Проверяем только при создании новой команды
        if not self.instance.pk and not role_ids:
            raise forms.ValidationError(
                "Необходимо выбрать хотя бы одну роль для работы в команде"
            )
        
        return role_ids


class UserSearchForm(forms.Form):
    """
    Форма для поиска пользователей с валидацией минимальной длины запроса.
    
    Используется для поиска пользователей по username, display_name и email
    при добавлении новых участников в команду.
    """
    
    query = forms.CharField(
        max_length=100,
        min_length=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите имя пользователя или email',
            'autocomplete': 'off'
        }),
        label='Поиск пользователей',
        help_text='Минимум 2 символа для поиска'
    )
    
    def clean_query(self):
        """
        Валидация поискового запроса.
        
        Returns:
            str: Очищенный поисковый запрос
            
        Raises:
            forms.ValidationError: Если запрос слишком короткий
        """
        query = self.cleaned_data.get('query')
        if not query:
            raise forms.ValidationError("Поисковый запрос не может быть пустым")
        
        query = query.strip()
        if len(query) < 2:
            raise forms.ValidationError("Минимум 2 символа для поиска")
        
        return query


class MemberAddForm(forms.Form):
    """
    Форма для добавления нового участника в команду.
    
    Включает проверку на существующее членство и валидацию ролей.
    """
    
    user_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        label='ID пользователя'
    )
    
    role_ids = forms.ModelMultipleChoiceField(
        queryset=Role.objects.exclude(name='Пользователь'),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Роли',
        help_text='Выберите одну или несколько ролей для участника',
        required=True
    )
    
    def __init__(self, team, *args, **kwargs):
        """
        Инициализация формы с привязкой к команде.
        
        Args:
            team (Team): Команда, в которую добавляется участник
        """
        super().__init__(*args, **kwargs)
        self.team = team
        
        # Ограничиваем выбор ролей (исключаем базовую роль "Пользователь")
        self.fields['role_ids'].queryset = Role.objects.exclude(name='Пользователь').order_by('name')
    
    def clean_user_id(self):
        """
        Валидация ID пользователя.
        
        Returns:
            int: ID пользователя
            
        Raises:
            forms.ValidationError: Если пользователь не найден или уже является участником
        """
        user_id = self.cleaned_data.get('user_id')
        
        if not user_id:
            raise forms.ValidationError("ID пользователя не указан")
        
        # Проверяем существование пользователя
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise forms.ValidationError("Пользователь не найден")
        
        # Проверяем на существующее активное членство
        if TeamMembership.objects.filter(
            team=self.team, 
            user=user, 
            is_active=True
        ).exists():
            raise forms.ValidationError(
                f"Пользователь {user.username} уже является активным участником команды"
            )
        
        return user_id
    
    def clean_role_ids(self):
        """
        Валидация выбранных ролей.
        
        Returns:
            QuerySet: Выбранные роли
            
        Raises:
            forms.ValidationError: Если роли не выбраны
        """
        role_ids = self.cleaned_data.get('role_ids')
        
        if not role_ids:
            raise forms.ValidationError("Необходимо выбрать хотя бы одну роль")
        
        return role_ids
    
    def get_user(self):
        """
        Возвращает объект пользователя по валидированному ID.
        
        Returns:
            User: Объект пользователя
        """
        if self.is_valid():
            user_id = self.cleaned_data['user_id']
            return User.objects.get(id=user_id)
        return None


class MemberRoleUpdateForm(forms.Form):
    """
    Форма для обновления ролей существующего участника команды.
    
    Предзаполняется текущими ролями участника.
    """
    
    role_ids = forms.ModelMultipleChoiceField(
        queryset=Role.objects.exclude(name='Пользователь'),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Роли',
        help_text='Выберите роли для участника',
        required=False  # Разрешаем пустой выбор для удаления всех ролей (кроме создателя)
    )
    
    def __init__(self, membership, *args, **kwargs):
        """
        Инициализация формы с предзаполнением текущих ролей.
        
        Args:
            membership (TeamMembership): Членство в команде для обновления
        """
        super().__init__(*args, **kwargs)
        self.membership = membership
        
        # Ограничиваем выбор ролей (исключаем базовую роль "Пользователь")
        self.fields['role_ids'].queryset = Role.objects.exclude(name='Пользователь').order_by('name')
        
        # Предзаполняем текущими ролями участника
        self.fields['role_ids'].initial = membership.roles.all()
    
    def clean_role_ids(self):
        """
        Валидация выбранных ролей с проверкой ограничений для создателя команды.
        
        Returns:
            QuerySet: Выбранные роли
            
        Raises:
            forms.ValidationError: Если создатель команды пытается удалить все роли
        """
        role_ids = self.cleaned_data.get('role_ids')
        
        # Проверяем, является ли участник создателем команды
        if self.membership.user == self.membership.team.creator:
            if not role_ids:
                raise forms.ValidationError(
                    "Создатель команды не может быть лишен всех ролей"
                )
        
        return role_ids
    
    def get_role_changes(self):
        """
        Возвращает информацию об изменениях ролей.
        
        Returns:
            dict: Словарь с ключами 'to_add' и 'to_remove', содержащими списки ролей
        """
        if not self.is_valid():
            return {'to_add': [], 'to_remove': []}
        
        new_roles = set(self.cleaned_data['role_ids'])
        current_roles = set(self.membership.roles.all())
        
        return {
            'to_add': list(new_roles - current_roles),
            'to_remove': list(current_roles - new_roles)
        }



class TeamJoinForm(forms.Form):
    """
    Форма для присоединения к команде.
    
    Позволяет пользователю выбрать роли при присоединении к команде.
    """
    
    role_ids = forms.ModelMultipleChoiceField(
        queryset=Role.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Выберите ваши роли в команде',
        help_text='Выберите хотя бы одну роль для работы в команде',
        required=True
    )
    
    def __init__(self, team, *args, **kwargs):
        """
        Инициализация формы.
        
        Args:
            team (Team): Команда, к которой присоединяется пользователь
        """
        super().__init__(*args, **kwargs)
        self.team = team
        
        # Исключаем роли "Руководитель" и "Пользователь"
        self.fields['role_ids'].queryset = Role.objects.exclude(
            name__in=['Руководитель', 'Пользователь']
        ).order_by('name')
    
    def clean_role_ids(self):
        """
        Валидация выбранных ролей.
        
        Returns:
            QuerySet: Выбранные роли
            
        Raises:
            forms.ValidationError: Если роли не выбраны
        """
        role_ids = self.cleaned_data.get('role_ids')
        
        if not role_ids:
            raise forms.ValidationError(
                'Необходимо выбрать хотя бы одну роль для работы в команде'
            )
        
        return role_ids


class LeadershipTransferForm(forms.Form):
    """
    Форма для передачи прав руководителя команды.
    
    Позволяет выбрать один из трех вариантов:
    1. Оставить текущие роли (кроме "Руководитель")
    2. Выбрать новые роли
    3. Покинуть команду
    """
    
    ACTION_KEEP = 'keep'
    ACTION_CHOOSE = 'choose'
    ACTION_LEAVE = 'leave'
    
    ACTION_CHOICES = [
        (ACTION_KEEP, 'Оставить текущие роли'),
        (ACTION_CHOOSE, 'Выбрать новые роли'),
        (ACTION_LEAVE, 'Покинуть команду'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Что произойдет с вашим участием в команде?',
        initial=ACTION_KEEP,
        required=True
    )
    
    new_roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label='Выберите новые роли',
        required=False
    )
    
    def __init__(self, team, current_leader_membership, *args, **kwargs):
        """
        Инициализация формы.
        
        Args:
            team (Team): Команда
            current_leader_membership (TeamMembership): Членство текущего руководителя
        """
        super().__init__(*args, **kwargs)
        self.team = team
        self.current_leader_membership = current_leader_membership
        
        # Ограничиваем выбор ролей (исключаем "Руководитель" и "Пользователь")
        self.fields['new_roles'].queryset = Role.objects.exclude(
            name__in=['Руководитель', 'Пользователь']
        ).order_by('name')
    
    def clean(self):
        """
        Валидация формы.
        
        Проверяет, что если выбрано "Выбрать новые роли", то роли действительно выбраны.
        """
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        new_roles = cleaned_data.get('new_roles')
        
        if action == self.ACTION_CHOOSE and not new_roles:
            raise forms.ValidationError(
                'Выберите хотя бы одну роль или измените действие.'
            )
        
        return cleaned_data
