from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wiki', '0019_add_edit_fork_local_path'),
    ]

    operations = [
        migrations.AddField(
            model_name='userbranch',
            name='conflict_files',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Files with unresolved rebase conflicts',
            ),
        ),
    ]
