# Generated migration for RepositorySettings model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RepositorySettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('repository_id', models.CharField(help_text='Repository identifier', max_length=255)),
                ('provider', models.CharField(help_text='Git provider (github, bitbucket_server, etc.)', max_length=50)),
                ('base_url', models.URLField(blank=True, help_text='Provider base URL')),
                ('branch', models.CharField(default='main', help_text='Default branch', max_length=255)),
                ('settings', models.JSONField(default=dict, help_text='Repository-specific settings (document index, view mode, etc.)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repository_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Repository Settings',
                'verbose_name_plural': 'Repository Settings',
                'ordering': ['-updated_at'],
                'unique_together': {('user', 'repository_id', 'provider')},
            },
        ),
    ]
