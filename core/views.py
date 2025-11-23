from django.views.generic import TemplateView
from django.shortcuts import render


class MainPageView(TemplateView):
    """Представление главной страницы сайта"""
    template_name = 'main.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class DocsView(TemplateView):
    """Представление страницы документации"""
    template_name = 'docs.html'


# Обработчики ошибок
def handler404(request, exception):
    """Обработчик ошибки 404 - страница не найдена"""
    return render(request, '404.html', status=404)


def handler500(request):
    """Обработчик ошибки 500 - внутренняя ошибка сервера"""
    return render(request, '500.html', status=500)


def handler403(request, exception):
    """Обработчик ошибки 403 - доступ запрещен"""
    return render(request, '403.html', status=403)
