from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_fastlink_alter_judge_options_remove_judge_bio_key_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='judgedetails',
            name='initiative_stack',
        ),
        migrations.RemoveField(
            model_name='judgedetails',
            name='initiative_state',
        ),
        migrations.RemoveField(
            model_name='judgedetails',
            name='initiative_text',
        ),
        migrations.RemoveField(
            model_name='judgedetails',
            name='initiative_title',
        ),
        migrations.AddField(
            model_name='judgedetails',
            name='initiatives',
            field=models.JSONField(blank=True, default=list, verbose_name='Инициативы и проекты'),
        ),
    ]
