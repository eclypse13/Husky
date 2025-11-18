from django.core.management.base import BaseCommand
from core.models import *
from datetime import datetime, timedelta
from django.contrib.auth.models import User as DjangoUser
from django.utils import timezone


class Command(BaseCommand):
    help = 'Загружает тестовые данные в MongoDB'

    def handle(self, *args, **options):
        self.stdout.write('Создание тестовых данных...')
        
        # 1. Создать Django суперпользователя
        if not DjangoUser.objects.filter(username='admin').exists():
            admin = DjangoUser.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            admin.last_login = timezone.now()
            admin.save()
            self.stdout.write(self.style.SUCCESS('Django admin создан'))
        
        # 2. Контент-справочник - основа всего текста
        content_data = {
            # Общие
            'LOGO_TEXT': ('general', 'НКП СХ'),
            'FOOTER_FULL_NAME': ('general', 'Национальный Клуб Породы Сибирский Хаски'),
            'FOOTER_EMAIL': ('general', 'info@nkp-husky.ru'),
            
            # Главная
            'HOME_TITLE': ('home', 'Добро пожаловать в НКП Сибирский Хаски'),
            'HOME_SUBTITLE': ('home', 'Объединяем любителей и заводчиков легендарной северной породы'),
            'HOME_ABOUT': ('home', 'Национальный клуб породы сибирский хаски – это сообщество профессионалов и любителей породы, объединенных общей целью: сохранение, развитие и популяризация чистопородного разведения сибирских хаски в России.'),
            'HOME_GOALS_TITLE': ('home', 'Наши цели'),
            'HOME_GOALS_TEXT': ('home', '- Сохранение породных качеств сибирских хаски\n- Поддержка ответственного разведения\n- Организация выставок и мероприятий\n- Обучение владельцев и заводчиков\n- Взаимодействие с FCI и РКФ'),
            
            # О клубе
            'CLUB_HISTORY_TITLE': ('club', 'История НКП'),
            'CLUB_HISTORY': ('club', 'Национальный клуб породы сибирский хаски был основан в 1996 году группой энтузиастов породы. За годы работы клуб стал крупнейшим объединением заводчиков и любителей хаски в России.'),
            'CLUB_MISSION': ('club', 'Наша миссия – сохранить уникальные рабочие качества северных ездовых собак, их характер и внешний вид, соответствующий стандарту FCI.'),
            
            # О породе
            'BREED_TITLE': ('breed', 'Сибирский хаски – порода с историей'),
            'BREED_STANDARD': ('breed', 'Стандарт FCI №270. Группа 5 (Шпицы и породы примитивного типа), Секция 1 (Северные ездовые собаки).'),
            'BREED_CHARACTER': ('breed', 'Дружелюбный и мягкий характер, но вместе с тем живой и энергичный. Сибирские хаски не проявляют собственнических качеств сторожевых собак и не слишком подозрительны к незнакомцам.'),
            'BREED_CARE_TITLE': ('breed', 'Уход и содержание'),
            'BREED_CARE': ('breed', 'Хаски нуждаются в активных физических нагрузках, регулярном вычесывании шерсти (особенно во время линьки) и правильном питании.'),
            
            # Мероприятия
            'EVENTS_TITLE': ('events', 'Календарь мероприятий НКП'),
            'EVENTS_INTRO': ('events', 'Наш клуб проводит выставки, семинары, тренировки и другие мероприятия для членов клуба и любителей породы.'),
            
            # Документы
            'DOCS_CHARTER': ('club', 'Устав НКП Сибирский Хаски'),
            'DOCS_REGULATIONS': ('club', 'Положение о членстве'),
        }
        
        # MongoEngine использует другой синтаксис для upsert
        for key, (page, value) in content_data.items():
            try:
                # Пытаемся найти существующий документ
                content = ContentDictionary.objects.get(key=key)
                # Обновляем его
                content.value = value
                content.page = page
                content.locale = 'ru'
                content.updated_by = 'system'
                content.updated_at = datetime.utcnow()
                content.save()
            except ContentDictionary.DoesNotExist:
                # Создаем новый
                ContentDictionary(
                    key=key,
                    value=value,
                    page=page,
                    locale='ru',
                    updated_by='system',
                    updated_at=datetime.utcnow()
                ).save()
        
        self.stdout.write(self.style.SUCCESS(f'Создано {len(content_data)} записей в справочнике'))
        
        # 3. MongoDB пользователи
        if not User.objects.filter(email='admin@example.com').first():
            admin_user = User(
                email='admin@example.com',
                first_name='Администратор',
                last_name='Системы',
                password_hash='02c5121796a42ec3c7707dd2a71f5d31c27b6be5924ef6e5aa51359d0e5951cc',
                roles=['admin_roles', 'section_admin'],
                is_nkp_member=True,
                membership_type='physical',
                phone='+7 (999) 123-45-67',
                city='Москва'
            )
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('MongoDB admin создан'))
        
        # Член НКП (физ. лицо)
        if not User.objects.filter(email='member@example.com').first():
            member = User(
                email='member@example.com',
                first_name='Иван',
                last_name='Петров',
                password_hash='pbkdf2_sha256$...',
                roles=['member_physical'],
                is_nkp_member=True,
                membership_type='physical',
                membership_started_at=datetime.utcnow() - timedelta(days=365),
                membership_expires_at=datetime.utcnow() + timedelta(days=365),
                phone='+7 (999) 111-22-33',
                city='Санкт-Петербург'
            )
            member.save()
            self.stdout.write(self.style.SUCCESS('Член НКП (физ.л.) создан'))
        
        # 4. Новости
        news_items = [
            {
                'title': 'Итоги Всероссийской выставки 2024',
                'lead': 'Подведены итоги крупнейшей выставки сибирских хаски',
                'body': 'В выставке приняли участие более 150 собак из 30 регионов России. Победителем в классе чемпионов стал...',
                'tags': ['выставки', '2024'],
                'is_featured': True
            },
            {
                'title': 'Новый семинар для заводчиков',
                'lead': 'Приглашаем на семинар по генетике окрасов',
                'body': 'Семинар пройдет 15 марта в Москве. Спикер - генетик-кинолог...',
                'tags': ['семинары', 'обучение'],
                'is_featured': True
            },
            {
                'title': 'Изменения в стандарте породы',
                'lead': 'FCI утвердила обновления стандарта №270',
                'body': 'Основные изменения касаются описания движений и пропорций...',
                'tags': ['стандарт', 'fci'],
                'is_featured': False
            },
        ]
        
        for i, news_data in enumerate(news_items):
            title_key = f"NEWS_{i+1}_TITLE"
            lead_key = f"NEWS_{i+1}_LEAD"
            body_key = f"NEWS_{i+1}_BODY"
            slug = f"news-{i+1}"
            
            # Проверяем, существует ли уже новость
            if not News.objects.filter(slug=slug).first():
                # Сохраняем тексты в справочник
                for content_key, content_value in [
                    (title_key, news_data['title']),
                    (lead_key, news_data['lead']),
                    (body_key, news_data['body'])
                ]:
                    if not ContentDictionary.objects.filter(key=content_key).first():
                        ContentDictionary(key=content_key, value=content_value, page='news').save()
                
                # Создаем новость
                News(
                    title_key=title_key,
                    lead_key=lead_key,
                    body_key=body_key,
                    slug=slug,
                    tags=news_data['tags'],
                    is_featured=news_data['is_featured'],
                    published_at=datetime.utcnow() - timedelta(days=i*3)
                ).save()
        
        self.stdout.write(self.style.SUCCESS(f'Создано {len(news_items)} новостей'))
        
        # 5. Галереи
        if not Gallery.objects.filter(title_key='GALLERY_1_TITLE').first():
            Gallery(
                title_key='GALLERY_1_TITLE',
                description_key='GALLERY_1_DESC',
                is_highlight=True
            ).save()
            if not ContentDictionary.objects.filter(key='GALLERY_1_TITLE').first():
                ContentDictionary(key='GALLERY_1_TITLE', value='Наши чемпионы', page='galleries').save()
        
        if not Gallery.objects.filter(title_key='GALLERY_2_TITLE').first():
            Gallery(
                title_key='GALLERY_2_TITLE',
                description_key='GALLERY_2_DESC',
                is_highlight=True
            ).save()
            if not ContentDictionary.objects.filter(key='GALLERY_2_TITLE').first():
                ContentDictionary(key='GALLERY_2_TITLE', value='Выставка 2024', page='galleries').save()
        
        self.stdout.write(self.style.SUCCESS('Созданы 2 галереи'))
        
        # 6. События
        events_data = [
            {
                'title': 'Монопородная выставка НКП СХ',
                'desc': 'Специализированная выставка сибирских хаски',
                'type': 'exhibition',
                'location': 'Москва, КВЦ Сокольники',
                'days': 30
            },
            {
                'title': 'Семинар по хендлингу',
                'desc': 'Обучение правильному показу собак',
                'type': 'seminar',
                'location': 'Санкт-Петербург',
                'days': 45
            },
            {
                'title': 'Встреча владельцев хаски',
                'desc': 'Неформальная встреча членов клуба',
                'type': 'meeting',
                'location': 'Парк Сокольники',
                'days': 14
            }
        ]
        
        for i, event_data in enumerate(events_data):
            title_key = f"EVENT_{i+1}_TITLE"
            desc_key = f"EVENT_{i+1}_DESC"
            
            if not Event.objects.filter(title_key=title_key).first():
                for content_key, content_value in [
                    (title_key, event_data['title']),
                    (desc_key, event_data['desc'])
                ]:
                    if not ContentDictionary.objects.filter(key=content_key).first():
                        ContentDictionary(key=content_key, value=content_value, page='events').save()
                
                Event(
                    title_key=title_key,
                    description_key=desc_key,
                    event_type=event_data['type'],
                    location=event_data['location'],
                    starts_at=datetime.utcnow() + timedelta(days=event_data['days'])
                ).save()
        
        self.stdout.write(self.style.SUCCESS(f'Создано {len(events_data)} событий'))
        
        # 7. Судьи
        if not Judge.objects.filter(name='Мария Иванова').first():
            Judge(
                name='Мария Иванова',
                rank='Всепородный судья FCI',
                bio_key='JUDGE_1_BIO'
            ).save()
            if not ContentDictionary.objects.filter(key='JUDGE_1_BIO').first():
                ContentDictionary(key='JUDGE_1_BIO', value='Опыт судейства более 20 лет', page='judges').save()
        
        # 8. Документы клуба
        if not ClubDocument.objects.filter(title_key='DOC_CHARTER').first():
            ClubDocument(
                title_key='DOC_CHARTER',
                description_key='DOC_CHARTER_DESC',
                document_type='charter'
            ).save()
            if not ContentDictionary.objects.filter(key='DOC_CHARTER_DESC').first():
                ContentDictionary(key='DOC_CHARTER_DESC', value='Устав НКП утвержден в 2020 году', page='documents').save()
        
        # 9. Члены Президиума
        if not BoardMember.objects.filter(name='Алексей Смирнов').first():
            BoardMember(
                name='Алексей Смирнов',
                position='Президент НКП',
                bio_key='BOARD_1_BIO',
                email='president@nkp-husky.ru',
                order=1
            ).save()
            if not ContentDictionary.objects.filter(key='BOARD_1_BIO').first():
                ContentDictionary(key='BOARD_1_BIO', value='Президент НКП с 2015 года', page='board').save()
        
        # 10. Стандарт породы
        if not BreedStandard.objects.filter(fci_number='270').first():
            BreedStandard(
                title_key='STANDARD_FCI_270',
                content_key='STANDARD_FCI_270_CONTENT',
                fci_number='270',
                version='2020'
            ).save()
            if not ContentDictionary.objects.filter(key='STANDARD_FCI_270').first():
                ContentDictionary(key='STANDARD_FCI_270', value='Стандарт FCI №270', page='breed').save()
        
        # 11. Статьи о породе
        if not BreedArticle.objects.filter(title_key='BREED_HISTORY').first():
            BreedArticle(
                title_key='BREED_HISTORY',
                content_key='BREED_HISTORY_CONTENT',
                category='history'
            ).save()
            if not ContentDictionary.objects.filter(key='BREED_HISTORY').first():
                ContentDictionary(key='BREED_HISTORY', value='История породы сибирский хаски', page='breed').save()
        
        self.stdout.write(self.style.SUCCESS('✓ Все тестовые данные созданы!'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Учетные данные:'))
        self.stdout.write('  Django Admin: admin@example.com / admin123')
        self.stdout.write('  Член НКП: member@example.com')
        self.stdout.write('')
        self.stdout.write('Доступ:')
        self.stdout.write('  API: http://localhost:8000/api/')
        self.stdout.write('  Swagger: http://localhost:8000/api/schema/swagger-ui/')
        self.stdout.write('  Django Admin: http://localhost:8000/admin/')
