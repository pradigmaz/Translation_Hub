from django.urls import path
from django.contrib.auth import views as auth_views
from .views.auth import RegisterView
from .views.dashboard import DashboardView
from .views.profile import ProfileView
from .views.settings import TeamsView, TasksView, SettingsView

app_name = 'users'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('teams/', TeamsView.as_view(), name='teams'),
    path('tasks/', TasksView.as_view(), name='tasks'),
    path('settings/', SettingsView.as_view(), name='settings'),
]