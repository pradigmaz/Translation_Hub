"""Миксины для AJAX представлений команд."""

import json
from django.http import JsonResponse
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError

from ..exceptions import TeamPermissionDenied, TeamNotFoundError, TeamStatusError



class AjaxResponseMixin:
    """Миксин для стандартизации AJAX ответов."""
    
    def ajax_response(self, success=True, data=None, message=None, errors=None, status=200):
        response_data = {
            'success': success,
            'data': data or {},
            'message': message or '',
            'errors': errors or []
        }
        
        # Добавляем timestamp для отладки
        from datetime import datetime
        response_data['timestamp'] = datetime.now().isoformat()
        
        return JsonResponse(response_data, status=status)
    
    def ajax_success(self, data=None, message=None):
        return self.ajax_response(
            success=True,
            data=data,
            message=message,
            status=200
        )
    
    def ajax_error(self, message=None, errors=None, status=400):
        return self.ajax_response(
            success=False,
            message=message,
            errors=errors,
            status=status
        )
    
    def handle_ajax_error(self, error, context=None):
        error_context = f" в {context}" if context else ""
        
        # Обработка специфичных для команд ошибок
        if isinstance(error, TeamPermissionDenied):
            return self.ajax_error(
                message=str(error),
                status=403
            )
        
        elif isinstance(error, TeamNotFoundError):
            return self.ajax_error(
                message="Команда не найдена",
                status=404
            )
        
        elif isinstance(error, TeamStatusError):
            return self.ajax_error(
                message=str(error),
                status=400
            )
        
        # Обработка стандартных Django ошибок
        elif isinstance(error, PermissionDenied):
            return self.ajax_error(
                message="У вас нет прав для выполнения этого действия",
                status=403
            )
        
        elif isinstance(error, ValidationError):
            
            # Обработка ошибок валидации форм
            if hasattr(error, 'error_dict'):
                errors = []
                for field, field_errors in error.error_dict.items():
                    for field_error in field_errors:
                        errors.append(f"{field}: {field_error.message}")
                return self.ajax_error(
                    message="Ошибка валидации данных",
                    errors=errors,
                    status=400
                )
            else:
                return self.ajax_error(
                    message=str(error),
                    status=400
                )
        
        elif isinstance(error, IntegrityError):
            return self.ajax_error(
                message="Ошибка целостности данных. Возможно, такая запись уже существует.",
                status=400
            )
        
        # Обработка неожиданных ошибок
        else:
            return self.ajax_error(
                message="Произошла внутренняя ошибка сервера",
                status=500
            )
    
    def dispatch(self, request, *args, **kwargs):
        # Проверяем, что это действительно AJAX запрос
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Для не-AJAX запросов используем стандартную обработку
            return super().dispatch(request, *args, **kwargs)
        
        try:
            return super().dispatch(request, *args, **kwargs)
        
        except (TeamPermissionDenied, TeamNotFoundError, TeamStatusError, 
                PermissionDenied, ValidationError, IntegrityError) as e:
            return self.handle_ajax_error(e, context=self.__class__.__name__)
        
        except Exception as e:
            return self.handle_ajax_error(e, context=self.__class__.__name__)


class AjaxRequiredMixin:
    """Миксин, требующий AJAX запросов."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            
            # Если есть AjaxResponseMixin, используем его для ответа
            if hasattr(self, 'ajax_error'):
                return self.ajax_error(
                    message="Этот endpoint доступен только для AJAX запросов",
                    status=400
                )
            else:
                from django.http import JsonResponse
                return JsonResponse({
                    'success': False,
                    'message': 'Этот endpoint доступен только для AJAX запросов'
                }, status=400)
        
        return super().dispatch(request, *args, **kwargs)


class AjaxFormMixin(AjaxResponseMixin):
    """Миксин для обработки форм в AJAX запросах."""
    
    def form_valid(self, form):
        try:
            # Сохраняем форму
            self.object = form.save()
            
            # Получаем данные для ответа
            response_data = self.get_ajax_success_data()
            
            return self.ajax_success(
                data=response_data,
                message=self.get_success_message()
            )
        
        except Exception as e:
            return self.handle_ajax_error(e, context="form_valid")
    
    def form_invalid(self, form):
        errors = []
        
        # Собираем ошибки по полям
        for field, field_errors in form.errors.items():
            for error in field_errors:
                if field == '__all__':
                    errors.append(str(error))
                else:
                    field_verbose = form.fields.get(field, {}).get('label', field)
                    errors.append(f"{field_verbose}: {error}")
        
        # Добавляем общие ошибки формы
        if hasattr(form, 'non_field_errors'):
            for error in form.non_field_errors():
                errors.append(str(error))
        
        return self.ajax_error(
            message="Ошибка валидации формы",
            errors=errors,
            status=400
        )
    
    def get_ajax_success_data(self):
        if hasattr(self, 'object') and self.object:
            return {
                'id': getattr(self.object, 'pk', None),
                'name': str(self.object)
            }
        return {}
    
    def get_success_message(self):
        return "Операция выполнена успешно"