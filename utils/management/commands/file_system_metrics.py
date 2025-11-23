import json
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from utils.file_monitoring import file_metrics


class Command(BaseCommand):
    help = 'Получение метрик файловой системы и статистики операций'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['disk', 'operations', 'errors', 'all'],
            default='all',
            help='Тип метрик для отображения',
        )
        
        parser.add_argument(
            '--user-id',
            type=int,
            help='Показать метрики для конкретного пользователя',
        )
        
        parser.add_argument(
            '--team-id',
            type=int,
            help='Показать метрики для конкретной команды',
        )
        
        parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='Формат вывода данных',
        )
        
        parser.add_argument(
            '--save-to',
            type=str,
            help='Сохранить метрики в JSON файл',
        )
        
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Показать детальную информацию',
        )
        
        parser.add_argument(
            '--refresh-cache',
            action='store_true',
            help='Принудительно обновить кэш метрик',
        )
    
    def handle(self, *args, **options):
        """Основная логика команды."""
        
        start_time = timezone.now()
        self.stdout.write(
            self.style.SUCCESS(f'Получение метрик файловой системы: {start_time}')
        )
        
        try:
            # Обновляем кэш если требуется
            if options['refresh_cache']:
                file_metrics.last_cache_update = None
                self.stdout.write("Кэш метрик обновлен")
            
            # Собираем метрики
            metrics_data = {}
            
            if options['type'] in ['disk', 'all']:
                metrics_data['disk_metrics'] = self._get_disk_metrics(options)

            # Добавляем метаданные
            metrics_data['metadata'] = {
                'timestamp': timezone.now().isoformat(),
                'command_options': options,
                'generation_time_seconds': (timezone.now() - start_time).total_seconds()
            }
            
            # Выводим результаты
            if options['format'] == 'json':
                self._display_json(metrics_data)
            else:
                self._display_table(metrics_data, options)
            
            # Сохраняем в файл если требуется
            if options['save_to']:
                self._save_metrics(metrics_data, options['save_to'])
            
            # Показываем время выполнения
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            self.stdout.write(
                self.style.SUCCESS(f'\nМетрики получены за {duration:.2f} секунд')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при получении метрик: {e}')
            )
            raise CommandError(f"Команда завершилась с ошибкой: {e}")
    
    def _get_disk_metrics(self, options):
        """Получить метрики дискового пространства."""
        
        disk_metrics = {}
        
        # Общие метрики
        disk_metrics['general'] = file_metrics.get_cached_metrics()
        
        # Метрики конкретного пользователя
        if options['user_id']:
            disk_metrics['user'] = file_metrics.get_user_storage_usage(options['user_id'])
        
        # Метрики конкретной команды
        if options['team_id']:
            disk_metrics['team'] = file_metrics.get_team_storage_usage(options['team_id'])
        
        return disk_metrics
    
        # Извлекаем только информацию об ошибках
        error_metrics = {
            'error_summary': {},
            'recent_errors': [],
            'error_trends': {}
        }
        
        # Суммарная статистика ошибок
        total_errors = 0
        for operation_type, stats in operation_stats.get('operations', {}).items():
            error_count = stats.get('error_count', 0)
            if error_count > 0:
                error_metrics['error_summary'][operation_type] = {
                    'error_count': error_count,
                    'total_operations': stats.get('total_count', 0),
                    'error_rate': (error_count / stats.get('total_count', 1)) * 100
                }
                total_errors += error_count
        
        error_metrics['total_errors'] = total_errors
        
        # Детальная информация об ошибках
        error_metrics['detailed_errors'] = operation_stats.get('errors', {})
        
        return error_metrics
    
    def _display_table(self, metrics_data, options):
        """Отобразить метрики в табличном формате."""
        
        # Метрики диска
        if 'disk_metrics' in metrics_data:
            self._display_disk_table(metrics_data['disk_metrics'], options)
        
        # Метрики операций
        if 'operation_metrics' in metrics_data:
            self._display_operations_table(metrics_data['operation_metrics'], options)
        
        # Метрики ошибок
        if 'error_metrics' in metrics_data:
            self._display_errors_table(metrics_data['error_metrics'], options)
    
    def _display_disk_table(self, disk_metrics, options):
        """Отобразить метрики диска в табличном формате."""
        
        self.stdout.write(f"\n{self.style.SUCCESS('=== МЕТРИКИ ДИСКОВОГО ПРОСТРАНСТВА ===')}")
        
        # Общие метрики
        general = disk_metrics.get('general', {})
        if general:
            # Информация о диске
            disk_usage = general.get('disk_usage', {})
            if disk_usage and 'error' not in disk_usage:
                self.stdout.write(f"\n{self.style.HTTP_INFO('Общая информация о диске:')}")
                self.stdout.write(f"  Общий размер: {self._format_bytes(disk_usage['total'])}")
                self.stdout.write(f"  Использовано: {self._format_bytes(disk_usage['used'])} ({disk_usage['percent_used']:.1f}%)")
                self.stdout.write(f"  Свободно: {self._format_bytes(disk_usage['free'])}")
                
                # Предупреждения о месте на диске
                if disk_usage['percent_used'] > 90:
                    self.stdout.write(self.style.ERROR("  ⚠️  КРИТИЧЕСКИ МАЛО МЕСТА НА ДИСКЕ!"))
                elif disk_usage['percent_used'] > 80:
                    self.stdout.write(self.style.WARNING("  ⚠️  Мало места на диске"))
            
            # Разбивка по медиа папкам
            media_breakdown = general.get('media_breakdown', {})
            if media_breakdown:
                self.stdout.write(f"\n{self.style.HTTP_INFO('Использование медиа папок:')}")
                
                categories = ['total', 'users', 'teams', 'temp', 'backups']
                for category in categories:
                    if category in media_breakdown and 'error' not in media_breakdown[category]:
                        info = media_breakdown[category]
                        size_mb = info.get('size_mb', 0)
                        file_count = info.get('file_count', 0)
                        
                        if category == 'total':
                            self.stdout.write(f"  {category.upper()}: {self._format_bytes(info['size_bytes'])} ({file_count} файлов)")
                            self.stdout.write("  " + "-" * 50)
                        else:
                            percentage = (info['size_bytes'] / media_breakdown['total']['size_bytes'] * 100) if media_breakdown['total']['size_bytes'] > 0 else 0
                            self.stdout.write(f"  {category}: {self._format_bytes(info['size_bytes'])} ({file_count} файлов, {percentage:.1f}%)")
        
        # Метрики пользователя
        if 'user' in disk_metrics:
            user_metrics = disk_metrics['user']
            if 'error' not in user_metrics:
                user_id = user_metrics["user_id"]
                self.stdout.write(f"\n{self.style.HTTP_INFO(f'Метрики пользователя {user_id}:')}")
                self.stdout.write(f"  Общий размер: {self._format_bytes(user_metrics['size_bytes'])}")
                self.stdout.write(f"  Количество файлов: {user_metrics['file_count']}")
                
                # Разбивка по типам файлов
                if options['detailed'] and 'file_types' in user_metrics:
                    self.stdout.write("  Типы файлов:")
                    for file_type, type_info in user_metrics['file_types'].items():
                        self.stdout.write(f"    {file_type or 'без расширения'}: {type_info['count']} файлов, {self._format_bytes(type_info['size'])}")
        
        # Метрики команды
        if 'team' in disk_metrics:
            team_metrics = disk_metrics['team']
            if 'error' not in team_metrics:
                team_id = team_metrics["team_id"]
                self.stdout.write(f"\n{self.style.HTTP_INFO(f'Метрики команды {team_id}:')}")
                self.stdout.write(f"  Общий размер: {self._format_bytes(team_metrics['size_bytes'])}")
                self.stdout.write(f"  Количество файлов: {team_metrics['file_count']}")
                
                # Разбивка по проектам
                if options['detailed'] and 'projects' in team_metrics:
                    self.stdout.write("  Проекты:")
                    for project_name, project_info in team_metrics['projects'].items():
                        self.stdout.write(f"    {project_name}: {project_info['file_count']} файлов, {self._format_bytes(project_info['size_bytes'])}")
    
    def _display_operations_table(self, operation_metrics, options):
        """Отобразить метрики операций в табличном формате."""
        
        self.stdout.write(f"\n{self.style.SUCCESS('=== МЕТРИКИ ФАЙЛОВЫХ ОПЕРАЦИЙ ===')}")
        
        operations = operation_metrics.get('operations', {})
        if not operations:
            self.stdout.write("Нет данных о файловых операциях")
            return
        
        # Общая статистика
        total_operations = sum(stats.get('total_count', 0) for stats in operations.values())
        total_success = sum(stats.get('success_count', 0) for stats in operations.values())
        total_errors = sum(stats.get('error_count', 0) for stats in operations.values())
        total_size = sum(stats.get('total_size', 0) for stats in operations.values())
        
        self.stdout.write(f"\n{self.style.HTTP_INFO('Общая статистика:')}")
        self.stdout.write(f"  Всего операций: {total_operations}")
        self.stdout.write(f"  Успешных: {total_success}")
        self.stdout.write(f"  Ошибок: {total_errors}")
        if total_operations > 0:
            success_rate = (total_success / total_operations) * 100
            self.stdout.write(f"  Успешность: {success_rate:.1f}%")
        self.stdout.write(f"  Общий объем данных: {self._format_bytes(total_size)}")
        
        # Детальная статистика по операциям
        self.stdout.write(f"\n{self.style.HTTP_INFO('Статистика по типам операций:')}")
        self.stdout.write(f"{'Операция':<25} {'Всего':<8} {'Успешно':<8} {'Ошибки':<8} {'Успешность':<12} {'Объем данных':<15}")
        self.stdout.write("-" * 85)
        
        for operation_type, stats in operations.items():
            total = stats.get('total_count', 0)
            success = stats.get('success_count', 0)
            errors = stats.get('error_count', 0)
            size = stats.get('total_size', 0)
            
            success_rate = (success / total * 100) if total > 0 else 0
            
            self.stdout.write(
                f"{operation_type:<25} {total:<8} {success:<8} {errors:<8} "
                f"{success_rate:<11.1f}% {self._format_bytes(size):<15}"
            )
        
        # Недавние операции (если детальный режим)
        if options['detailed']:
            self.stdout.write(f"\n{self.style.HTTP_INFO('Недавние операции:')}")
            
            all_recent = []
            for operation_type, stats in operations.items():
                recent_ops = stats.get('recent_operations', [])[-5:]  # Последние 5
                for op in recent_ops:
                    op['operation_type'] = operation_type
                    all_recent.append(op)
            
            # Сортируем по времени
            all_recent.sort(key=lambda x: x['timestamp'], reverse=True)
            
            for op in all_recent[:10]:  # Показываем последние 10
                status = "✓" if op['success'] else "✗"
                timestamp = op['timestamp'][:19]  # Убираем микросекунды
                self.stdout.write(
                    f"  {status} {timestamp} {op['operation_type']} "
                    f"(пользователь: {op.get('user_id', 'N/A')}, размер: {self._format_bytes(op.get('file_size', 0))})"
                )
    
    def _display_errors_table(self, error_metrics, options):
        """Отобразить метрики ошибок в табличном формате."""
        
        self.stdout.write(f"\n{self.style.SUCCESS('=== МЕТРИКИ ОШИБОК ===')}")
        
        total_errors = error_metrics.get('total_errors', 0)
        if total_errors == 0:
            self.stdout.write(self.style.SUCCESS("Ошибок не обнаружено! 🎉"))
            return
        
        # Общая статистика ошибок
        self.stdout.write(f"\n{self.style.HTTP_INFO('Общая статистика ошибок:')}")
        self.stdout.write(f"  Всего ошибок: {total_errors}")
        
        # Ошибки по типам операций
        error_summary = error_metrics.get('error_summary', {})
        if error_summary:
            self.stdout.write(f"\n{self.style.HTTP_INFO('Ошибки по типам операций:')}")
            self.stdout.write(f"{'Операция':<25} {'Ошибки':<8} {'Всего операций':<15} {'Процент ошибок':<15}")
            self.stdout.write("-" * 70)
            
            for operation_type, stats in error_summary.items():
                error_count = stats['error_count']
                total_ops = stats['total_operations']
                error_rate = stats['error_rate']
                
                # Цветовая индикация уровня ошибок
                if error_rate > 10:
                    style = self.style.ERROR
                elif error_rate > 5:
                    style = self.style.WARNING
                else:
                    style = self.style.SUCCESS
                
                self.stdout.write(style(
                    f"{operation_type:<25} {error_count:<8} {total_ops:<15} {error_rate:<14.1f}%"
                ))
        
        # Детальная информация об ошибках
        detailed_errors = error_metrics.get('detailed_errors', {})
        if detailed_errors and options['detailed']:
            self.stdout.write(f"\n{self.style.HTTP_INFO('Детальная информация об ошибках:')}")
            
            for error_type, error_info in detailed_errors.items():
                error_count = error_info.get('count', 0)
                recent_errors = error_info.get('recent_errors', [])
                
                self.stdout.write(f"\n  {error_type.upper()} (всего: {error_count}):")
                
                # Показываем последние ошибки
                for error in recent_errors[-3:]:  # Последние 3 ошибки
                    timestamp = error['timestamp'][:19]
                    message = error['message'][:80] + "..." if len(error['message']) > 80 else error['message']
                    user_id = error.get('user_id', 'N/A')
                    
                    self.stdout.write(f"    [{timestamp}] Пользователь {user_id}: {message}")
    
    def _display_json(self, metrics_data):
        """Отобразить метрики в JSON формате."""
        
        json_output = json.dumps(metrics_data, ensure_ascii=False, indent=2, default=str)
        self.stdout.write(json_output)
    
    def _save_metrics(self, metrics_data, filename):
        """Сохранить метрики в JSON файл."""
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, ensure_ascii=False, indent=2, default=str)
            
            self.stdout.write(f"\nМетрики сохранены в файл: {filename}")
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Не удалось сохранить метрики в {filename}: {e}")
            )
    
    def _format_bytes(self, bytes_count):
        """Форматировать размер в байтах в читаемый вид."""
        
        if bytes_count == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(bytes_count)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"