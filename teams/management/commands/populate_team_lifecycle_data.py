"""
Management command для заполнения данных жизненного цикла команд.

Эта команда обновляет существующие команды, устанавливая:
- Статус ACTIVE для всех команд
- Значения joined_at и is_active для участников команд
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from teams.models import Team, TeamMembership


class Command(BaseCommand):
    help = 'Заполняет данные жизненного цикла для существующих команд'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет сделано без фактического выполнения изменений',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод процесса обновления',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно обновить данные даже если они уже заполнены',
        )

    def handle(self, *args, **options):
        """Основная логика команды"""
        
        # Настройка логирования
        
        dry_run = options['dry_run']
        verbose = options['verbose']
        force = options['force']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('РЕЖИМ ТЕСТИРОВАНИЯ: изменения не будут сохранены')
            )
        
        if force:
            self.stdout.write(
                self.style.WARNING('ПРИНУДИТЕЛЬНЫЙ РЕЖИМ: данные будут перезаписаны')
            )
        
        try:
            # Получаем все команды
            teams = Team.objects.select_related('creator').all()
            total_teams = teams.count()
            
            if total_teams == 0:
                self.stdout.write(
                    self.style.WARNING('В системе нет команд для обновления')
                )
                return
            
            self.stdout.write(f'Найдено команд для обработки: {total_teams}')
            
            # Счетчики для статистики
            teams_updated = 0
            memberships_updated = 0
            teams_skipped = 0
            error_count = 0
            
            # Обрабатываем каждую команду
            for team in teams:
                try:
                    with transaction.atomic():
                        team_changes = []
                        
                        # 1. Проверяем и устанавливаем статус ACTIVE
                        if not team.status or force:
                            if not dry_run:
                                team.status = 'active'
                                team.save(update_fields=['status'])
                            teams_updated += 1
                            team_changes.append('установлен статус ACTIVE')
                        else:
                            teams_skipped += 1
                        
                        # 2. Обновляем участников команды
                        memberships = TeamMembership.objects.filter(team=team)
                        team_membership_updates = 0
                        
                        for membership in memberships:
                            updated_fields = []
                            
                            # Устанавливаем joined_at если не установлено или принудительно
                            if not membership.joined_at or force:
                                if not dry_run:
                                    membership.joined_at = team.created_at if hasattr(team, 'created_at') and team.created_at else timezone.now()
                                    updated_fields.append('joined_at')
                            
                            # Устанавливаем is_active=True если не установлено или принудительно
                            if membership.is_active is None or (force and not membership.is_active):
                                if not dry_run:
                                    membership.is_active = True
                                    updated_fields.append('is_active')
                            
                            if updated_fields:
                                if not dry_run:
                                    membership.save(update_fields=updated_fields)
                                team_membership_updates += 1
                                memberships_updated += 1
                        
                        if team_membership_updates > 0:
                            team_changes.append(f'обновлено {team_membership_updates} участников')
                        
                        # Выводим информацию о изменениях
                        if team_changes:
                            changes_text = ', '.join(team_changes)
                            message = f'  Команда "{team.name}": {changes_text}'
                            if dry_run:
                                message = f'[DRY RUN] {message}'
                            
                            self.stdout.write(self.style.SUCCESS(message))
                            
                        elif verbose:
                            self.stdout.write(f'  Команда "{team.name}": без изменений')
                
                except Exception as e:
                    error_count += 1
                    error_message = f'Ошибка при обработке команды "{team.name}": {str(e)}'
                    self.stdout.write(self.style.ERROR(error_message))
                    # Транзакция откатится автоматически при выходе из with блока
                    continue
            
            # Выводим итоговую статистику
            self.stdout.write('\n' + '='*60)
            self.stdout.write('ИТОГИ ЗАПОЛНЕНИЯ ДАННЫХ ЖИЗНЕННОГО ЦИКЛА:')
            self.stdout.write(f'Всего команд обработано: {total_teams}')
            self.stdout.write(f'Команд обновлено: {teams_updated}')
            self.stdout.write(f'Команд пропущено (уже заполнены): {teams_skipped}')
            self.stdout.write(f'Участников обновлено: {memberships_updated}')

            
            if error_count > 0:
                self.stdout.write(self.style.ERROR(f'Ошибок: {error_count}'))
            else:
                self.stdout.write(self.style.SUCCESS('Ошибок: 0'))
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('\nЭто был тестовый запуск. Для применения изменений '
                                     'запустите команду без флага --dry-run')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('\nЗаполнение данных жизненного цикла завершено успешно!')
                )

                
        except Exception as e:
            error_message = f'Критическая ошибка при выполнении команды: {str(e)}'
            self.stdout.write(self.style.ERROR(error_message))
            raise CommandError(error_message)