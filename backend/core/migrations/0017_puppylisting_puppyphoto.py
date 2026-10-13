import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_president_presidentachievement_presidentbadge'),
    ]

    operations = [
        migrations.CreateModel(
            name='PuppyListing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Имя / кличка щенка')),
                ('sex', models.CharField(blank=True, choices=[('male', 'Кобель'), ('female', 'Сука')], max_length=10, verbose_name='Пол')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('date_of_birth', models.DateField(blank=True, null=True, verbose_name='Дата рождения')),
                ('color', models.CharField(blank=True, max_length=200, verbose_name='Окрас')),
                ('city', models.CharField(blank=True, max_length=120, verbose_name='Город')),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Цена, ₽')),
                ('kennel_name', models.CharField(blank=True, max_length=200, verbose_name='Питомник')),
                ('kennel_url', models.URLField(blank=True, verbose_name='Ссылка на питомник')),
                ('breeder_contact', models.CharField(max_length=300, verbose_name='Контакт заводчика')),
                ('sire_archive_id', models.IntegerField(blank=True, null=True, verbose_name='ID отца в архиве')),
                ('sire_name', models.CharField(blank=True, max_length=300, verbose_name='Отец (имя)')),
                ('dam_archive_id', models.IntegerField(blank=True, null=True, verbose_name='ID матери в архиве')),
                ('dam_name', models.CharField(blank=True, max_length=300, verbose_name='Мать (имя)')),
                ('is_nkp_member', models.BooleanField(default=False, verbose_name='Питомник — член НКП')),
                ('status', models.CharField(choices=[('available', 'Доступен'), ('reserved', 'Забронирован'), ('sold', 'Продан')], default='available', max_length=20, verbose_name='Статус')),
                ('is_published', models.BooleanField(default=True, verbose_name='Опубликовано')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='puppy_listings', to='core.user', verbose_name='Автор')),
            ],
            options={
                'verbose_name': 'Щенок на продажу',
                'verbose_name_plural': 'Щенки на продажу',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PuppyPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='puppies/', verbose_name='Фото')),
                ('order', models.PositiveIntegerField(db_index=True, default=0, verbose_name='Порядок')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='core.puppylisting', verbose_name='Объявление')),
            ],
            options={
                'verbose_name': 'Фото щенка',
                'verbose_name_plural': 'Фото щенка',
                'ordering': ['order', 'created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='puppylisting',
            index=models.Index(fields=['is_published'], name='core_puppy_is_publ_idx'),
        ),
        migrations.AddIndex(
            model_name='puppylisting',
            index=models.Index(fields=['status'], name='core_puppy_status_idx'),
        ),
    ]
