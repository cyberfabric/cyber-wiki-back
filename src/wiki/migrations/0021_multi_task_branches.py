from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wiki', '0020_userbranch_conflict_files'),
    ]

    operations = [
        # Add name + is_selected to UserBranch
        migrations.AddField(
            model_name='userbranch',
            name='name',
            field=models.CharField(
                blank=True,
                max_length=200,
                help_text='Human-readable task name',
            ),
        ),
        migrations.AddField(
            model_name='userbranch',
            name='is_selected',
            field=models.BooleanField(
                default=False,
                help_text='Whether this is the currently active task for this user+space',
            ),
        ),

        # Add user_branch FK to UserDraftChange (nullable for backward compat)
        migrations.AddField(
            model_name='userdraftchange',
            name='user_branch',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='draft_changes',
                to='wiki.userbranch',
                help_text='Task (branch) this draft is staged for',
            ),
        ),

        # Remove the old unique_together on UserDraftChange
        migrations.AlterUniqueTogether(
            name='userdraftchange',
            unique_together=set(),
        ),

        # Add new partial unique constraint (per branch+file, when branch is set)
        migrations.AddConstraint(
            model_name='userdraftchange',
            constraint=models.UniqueConstraint(
                fields=['user', 'user_branch', 'file_path'],
                condition=models.Q(user_branch__isnull=False),
                name='unique_draft_per_branch_file',
            ),
        ),
    ]
