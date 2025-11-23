from django.urls import path
from . import views

app_name = 'glossary'

urlpatterns = [
    path('project/<int:project_id>/', views.glossary_list, name='glossary_list'),
    path('project/<int:project_id>/<int:pk>/', views.glossary_detail, name='glossary_detail'),
    path('project/<int:project_id>/material/<int:material_id>/', views.material_detail, name='material_detail'),
]