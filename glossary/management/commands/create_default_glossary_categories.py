from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from glossary.models import GlossaryCategory

User = get_user_model()


class Command(BaseCommand):
    help = 'Создает базовые категории базы знаний'

    def add_arguments(self, parser):
        parser.add_argument('--admin-user', type=str, help='Username администратора')

    def handle(self, *args, **options):
        admin_username = options.get('admin_user')
        if admin_username:
            try:
                admin_user = User.objects.get(username=admin_username, is_superuser=True)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Суперпользователь {admin_username} не найден'))
                return
        else:
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                self.stdout.write(self.style.ERROR('Не найден ни один суперпользователь'))
                return

        categories_data = [
            {'name': 'База знаний по манге', 'content_type': 'manga', 'scope': 'global'},
            {'name': 'База знаний по манхве', 'content_type': 'manhwa', 'scope': 'global'},
            {'name': 'База знаний по маньхуа', 'content_type': 'manhua', 'scope': 'global'},
            {'name': 'Общие статьи для переводчиков', 'content_type': 'general', 'scope': 'global'},
        ]

        created_count = 0
        for category_data in categories_data:
            category, created = GlossaryCategory.objects.get_or_create(
                name=category_data['name'],
                content_type=category_data['content_type'],
                scope=category_data['scope'],
                defaults={'created_by': admin_user, 'is_active': True}
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Создана категория: {category.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  Категория уже существует: {category.name}'))

        self.stdout.write(self.style.SUCCESS(f'\n🎉 Создано {created_count} новых категорий'))