# Generated manually - удаление неиспользуемых моделей content app

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0002_initial'),
    ]

    operations = [
        # Удаляем неиспользуемые модели
        migrations.DeleteModel(
            name='TextContent',
        ),
        migrations.DeleteModel(
            name='ImageContent',
        ),
        migrations.DeleteModel(
            name='ProjectDocument',
        ),
    ]
