from django.contrib import admin
from django.utils.html import format_html
from .models import GlossaryCategory, GlossaryTerm, CONTENT_TYPE_ICONS


@admin.register(GlossaryCategory)
class GlossaryCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'content_type_display', 'scope_display', 'created_by', 'articles_count', 'is_active', 'created_at')
    list_filter = ('content_type', 'scope', 'is_active', 'created_at')
    search_fields = ('name', 'created_by__username')
    readonly_fields = ('created_at', 'updated_at', 'articles_count')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'content_type', 'scope')
        }),
        ('Настройки', {
            'fields': ('is_active',)
        }),
        ('Метаданные', {
            'fields': ('created_by', 'created_at', 'updated_at', 'articles_count'),
            'classes': ('collapse',)
        })
    )
    
    def content_type_display(self, obj):
        icon = CONTENT_TYPE_ICONS.get(obj.content_type, '❓')
        return format_html('{} {}', icon, obj.get_content_type_display())
    content_type_display.short_description = 'Тип контента'
    content_type_display.admin_order_field = 'content_type'
    
    def scope_display(self, obj):
        colors = {'global': '#28a745', 'user': '#007cba', 'project': '#ffc107'}
        color = colors.get(obj.scope, '#6c757d')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_scope_display())
    scope_display.short_description = 'Область видимости'
    scope_display.admin_order_field = 'scope'
    
    def articles_count(self, obj):
        count = obj.terms.count()
        if count == 0:
            return format_html('<span style="color: #6c757d;">Нет статей</span>')
        return format_html('<strong>{} статей</strong>', count)
    articles_count.short_description = 'Количество статей'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(GlossaryTerm)
class GlossaryTermAdmin(admin.ModelAdmin):
    list_display = ('term', 'category_display', 'created_by', 'is_active', 'created_at')
    list_filter = ('category__content_type', 'category__scope', 'is_active', 'created_at', 'category')
    search_fields = ('term', 'definition', 'created_by__username', 'category__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {'fields': ('term', 'definition')}),
        ('Категоризация', {'fields': ('category',)}),
        ('Настройки', {'fields': ('is_active',)}),
        ('Метаданные', {'fields': ('created_by', 'created_at', 'updated_at'), 'classes': ('collapse',)})
    )
    actions = ['activate_articles', 'deactivate_articles']
    
    def category_display(self, obj):
        if not obj.category:
            return format_html('<span style="color: #dc3545;">Без категории</span>')
        icon = CONTENT_TYPE_ICONS.get(obj.category.content_type, '❓')
        return format_html('{} {} <small>({})</small>', icon, obj.category.name, obj.category.get_scope_display())
    category_display.short_description = 'Категория'
    category_display.admin_order_field = 'category__name'
    
    def project_display(self, obj):
        if obj.project:
            return format_html('<span style="color: #007cba;">{}</span>', obj.project.title)
        return format_html('<span style="color: #6c757d;">Общий термин</span>')
    project_display.short_description = 'Проект'
    project_display.admin_order_field = 'project__title'
    
    def activate_articles(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'Активировано {count} статей')
    activate_articles.short_description = '✅ Активировать выбранные статьи'
    
    def deactivate_articles(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано {count} статей')
    deactivate_articles.short_description = '❌ Деактивировать выбранные статьи'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'project', 'created_by')
