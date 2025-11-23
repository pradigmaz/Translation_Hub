from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('create/', views.ProjectCreateView.as_view(), name='create_project'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='edit_project'),
    path('<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='delete_project'),
    path('<int:pk>/download/', views.ProjectDownloadView.as_view(), name='download_project_data'),
    
    # Chapter management
    path('<int:project_id>/chapters/create/', views.ChapterCreateView.as_view(), name='create_chapter'),
    path('<int:project_id>/chapters/<int:pk>/workspace/', views.ChapterWorkspaceView.as_view(), name='chapter_workspace'),
    path('<int:project_id>/chapters/<int:chapter_id>/delete/', views.delete_chapter, name='delete_chapter'),
    path('<int:project_id>/chapters/<int:chapter_id>/save-translation/', views.save_translation, name='save_translation'),
    path('<int:project_id>/chapters/<int:chapter_id>/update-status/', views.update_chapter_status, name='update_chapter_status'),
    
    # Comments
    path('<int:project_id>/chapters/<int:chapter_id>/comments/add/', views.add_comment, name='add_comment'),
    path('<int:project_id>/chapters/<int:chapter_id>/comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    
    # API endpoints для файлового менеджера
    path('<int:project_id>/chapters/<int:chapter_id>/file-counts/', views.chapter_file_counts, name='chapter_file_counts'),
    path('<int:project_id>/chapters/<int:chapter_id>/files/', views.chapter_files, name='chapter_files'),
    path('<int:project_id>/chapters/<int:chapter_id>/upload/', views.upload_file, name='upload_file'),
    path('<int:project_id>/chapters/<int:chapter_id>/download/<str:folder>/<str:filename>/', views.download_file, name='download_file'),
    path('<int:project_id>/chapters/<int:chapter_id>/download-archive/', views.download_chapter_archive, name='download_chapter_archive'),
    
    # Materials
    path('<int:pk>/materials/create/', views.MaterialCreateView.as_view(), name='create_material'),
    path('<int:pk>/materials/<int:material_id>/edit/', views.MaterialUpdateView.as_view(), name='edit_material'),
    path('<int:pk>/materials/<int:material_id>/delete/', views.MaterialDeleteView.as_view(), name='delete_material'),
]