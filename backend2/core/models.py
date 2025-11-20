from mongoengine import (
    Document, EmbeddedDocument,
    StringField, EmailField, BooleanField, DateTimeField,
    IntField, FloatField, ListField, DictField,
    EmbeddedDocumentField, ReferenceField, ObjectIdField,
    URLField, FileField, ImageField
)
from datetime import datetime
from django.contrib.auth.models import AbstractUser

# ============================================
# 1. КОНТЕНТ-СПРАВОЧНИК
# ============================================

class ContentDictionary(Document):
    """Централизованный справочник всех текстов сайта"""
    key = StringField(required=True, unique=True, max_length=200)
    value = StringField(required=True)  # Markdown/HTML
    page = StringField(max_length=100, default='general')
    locale = StringField(max_length=10, default='ru')
    updated_by = StringField(max_length=200)  # email пользователя
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'content_dictionary',
        'indexes': [
            'key',
            'page',
            'locale',
            {'fields': ['page', 'locale']},
        ]
    }
    
    def __str__(self):
        return f"{self.key} ({self.page})"


class ContentRevision(Document):
    """История изменений контента"""
    content_key = StringField(required=True)
    old_value = StringField()
    new_value = StringField()
    changed_by = StringField()
    changed_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'content_revisions'}


# ============================================
# 2. ПОЛЬЗОВАТЕЛИ И РОЛИ
# ============================================

class User(Document):
    """Пользователи системы (члены клуба)"""
    email = EmailField(required=True, unique=True)
    first_name = StringField(max_length=100)
    last_name = StringField(max_length=100)
    password_hash = StringField(required=True)
    
    # Роли
    roles = ListField(StringField(choices=[
        'admin_roles',      # Администратор ролей
        'section_admin',    # Администратор раздела
        'presidium',        # Член Президиума
        'member_physical',  # Член НКП (физ. лицо)
        'member_legal',     # Член НКП (юр. лицо)
    ]))
    
    # Членство в НКП
    is_nkp_member = BooleanField(default=False)
    membership_type = StringField(choices=['physical', 'legal', None])
    membership_started_at = DateTimeField()
    membership_expires_at = DateTimeField()
    
    # Профиль
    phone = StringField(max_length=20)
    city = StringField(max_length=100)
    avatar = ImageField()
    
    # Связь с питомником (для юр. лиц)
    kennel = ReferenceField('Kennel')
    
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    last_login = DateTimeField()
    
    meta = {
        'collection': 'users',
        'indexes': ['email', 'is_nkp_member']
    }
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


# ============================================
# 3. ПУБЛИЧНЫЙ КОНТЕНТ
# ============================================

class News(Document):
    """Новости"""
    title_key = StringField(required=True)  # Ссылка на content_dictionary
    lead_key = StringField()
    body_key = StringField()
    
    slug = StringField(unique=True)
    tags = ListField(StringField())
    is_featured = BooleanField(default=False)
    cover_image = ImageField()
    
    author = ReferenceField(User)
    published_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'news',
        'ordering': ['-published_at']
    }


class Page(Document):
    """CMS страницы"""
    slug = StringField(required=True, unique=True)
    title_key = StringField(required=True)
    
    # Структура секций с ссылками на ключи контента
    sections = ListField(DictField())  # [{"type": "text", "dict_keys": ["key1", "key2"]}, ...]
    
    is_published = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'pages'}


class Gallery(Document):
    """Галереи фотографий"""
    title_key = StringField(required=True)
    description_key = StringField()
    
    images = ListField(DictField())  # [{"file": "path", "caption_key": "key"}, ...]
    is_highlight = BooleanField(default=False)  # Показывать на главной
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'galleries'}


# ============================================
# 4. МЕРОПРИЯТИЯ И ВЫСТАВКИ
# ============================================

class Judge(Document):
    """Судьи"""
    name = StringField(required=True)
    rank = StringField()  # Категория судьи
    bio_key = StringField()
    photo = ImageField()
    
    # Методические материалы
    materials = ListField(DictField())  # [{"type": "pdf", "url": "..."}, ...]
    
    meta = {'collection': 'judges'}


class Event(Document):
    """Мероприятия и выставки"""
    title_key = StringField(required=True)
    description_key = StringField()
    
    event_type = StringField(choices=['exhibition', 'seminar', 'meeting', 'other'])
    location = StringField()
    starts_at = DateTimeField(required=True)
    ends_at = DateTimeField()
    
    judges = ListField(ReferenceField(Judge))
    registration_link = URLField()
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'events',
        'ordering': ['starts_at']
    }


class EventReport(Document):
    """Отчеты о мероприятиях"""
    event = ReferenceField(Event, required=True)
    
    photos = ListField(ImageField())
    videos = ListField(URLField())
    
    # Результаты
    results = ListField(DictField())  # [{"class": "открытый", "dog_id": "...", "place": 1}, ...]
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'event_reports'}


class Seminar(Document):
    """Семинары для судей/хендлеров"""
    title_key = StringField(required=True)
    description_key = StringField()
    
    speaker = ReferenceField(Judge)
    date = DateTimeField()
    materials = ListField(FileField())
    
    meta = {'collection': 'seminars'}


# ============================================
# 5. О ПОРОДЕ
# ============================================

class BreedStandard(Document):
    """Стандарты породы FCI"""
    title_key = StringField(required=True)
    content_key = StringField()
    
    fci_number = StringField()
    illustrations = ListField(ImageField())
    
    version = StringField()
    approved_date = DateTimeField()
    
    meta = {'collection': 'breed_standards'}


class BreedArticle(Document):
    """Статьи о породе"""
    title_key = StringField(required=True)
    content_key = StringField()
    
    category = StringField(choices=['history', 'character', 'care', 'grooming', 'feeding'])
    videos = ListField(URLField())
    
    meta = {'collection': 'breed_articles'}


# ============================================
# 6. О КЛУБЕ
# ============================================

class ClubDocument(Document):
    """Документы клуба (устав, положения и т.д.)"""
    title_key = StringField(required=True)
    description_key = StringField()
    
    file = FileField(required=True)
    document_type = StringField(choices=['charter', 'regulation', 'standard', 'form'])
    
    uploaded_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'club_documents'}


class BoardMember(Document):
    """Члены Президиума"""
    name = StringField(required=True)
    position = StringField()  # Должность
    bio_key = StringField()
    photo = ImageField()
    
    email = EmailField()
    phone = StringField()
    
    order = IntField(default=0)
    
    meta = {
        'collection': 'club_board',
        'ordering': ['order']
    }


class MembershipPlan(Document):
    """Планы членства"""
    name_key = StringField(required=True)
    description_key = StringField()
    
    membership_type = StringField(choices=['physical', 'legal'])
    annual_fee = FloatField()
    
    benefits = ListField(StringField())  # Список ключей преференций
    
    meta = {'collection': 'membership_plans'}


# ============================================
# 7. ЛИЧНЫЙ КАБИНЕТ - ПИТОМНИКИ И СОБАКИ
# ============================================

class Kennel(Document):
    """Питомники"""
    owner = ReferenceField(User, required=True)
    
    name = StringField(required=True)
    prefix = StringField()  # Префикс/аффикс
    
    site_url = URLField()
    socials = DictField()  # {"vk": "url", "instagram": "url", ...}
    
    # Для мониторинга сайта
    monitor_enabled = BooleanField(default=False)
    last_check_at = DateTimeField()
    last_screenshot = ImageField()
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'kennels'}


class Dog(Document):
    """Собаки"""
    owner = ReferenceField(User, required=True)
    kennel = ReferenceField(Kennel)
    
    name = StringField(required=True)
    registered_name = StringField()
    sex = StringField(choices=['male', 'female'])
    date_of_birth = DateTimeField()
    
    # Родословная
    pedigree_number = StringField()
    microchip = StringField()
    
    # Родители
    sire = ReferenceField('self')  # Отец
    dam = ReferenceField('self')   # Мать
    
    # Титулы и достижения
    titles = ListField(StringField())
    is_champion = BooleanField(default=False)
    
    photos = ListField(ImageField())
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'dogs'}


class Litter(Document):
    """Пометы"""
    kennel = ReferenceField(Kennel, required=True)
    
    sire = ReferenceField(Dog, required=True)  # Отец
    dam = ReferenceField(Dog, required=True)   # Мать
    
    whelped_at = DateTimeField()  # Дата рождения помета
    puppies_count = IntField()
    
    notes_key = StringField()  # Описание помета
    
    status = StringField(choices=['announced', 'born', 'sold'], default='announced')
    
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'litters',
        'ordering': ['-whelped_at']
    }


# ============================================
# 8. ЗАЯВЛЕНИЯ И ЗАПРОСЫ
# ============================================

class Application(Document):
    """Заявления членов клуба"""
    user = ReferenceField(User, required=True)
    
    application_type = StringField(choices=[
        'membership',
        'litter_registration',
        'kennel_registration',
        'document_request',
        'complaint',
        'other'
    ])
    
    payload = DictField()  # Данные заявления
    status = StringField(choices=['new', 'in_progress', 'done', 'rejected'], default='new')
    
    history = ListField(DictField())  # История изменений статуса
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'applications',
        'ordering': ['-created_at']
    }


# ============================================
# 9. ДОСТИЖЕНИЯ И ЧЛЕНСТВО
# ============================================

class Achievement(Document):
    """Достижения на выставках"""
    user = ReferenceField(User, required=True)
    dog = ReferenceField(Dog)
    event = ReferenceField(Event)
    
    title = StringField()
    place = IntField()
    certificate = FileField()
    
    achieved_at = DateTimeField()
    
    meta = {'collection': 'achievements'}


class MembershipPayment(Document):
    """История взносов"""
    user = ReferenceField(User, required=True)
    
    amount = FloatField(required=True)
    payment_date = DateTimeField(default=datetime.utcnow)
    period_start = DateTimeField()
    period_end = DateTimeField()
    
    payment_method = StringField()
    transaction_id = StringField()
    
    meta = {'collection': 'membership_payments'}


# ============================================
# 10. ПРЕФЕРЕНЦИИ И МАТЕРИАЛЫ
# ============================================

class MemberBenefit(Document):
    """Льготы для членов НКП"""
    name_key = StringField(required=True)
    description_key = StringField()
    
    benefit_type = StringField(choices=['discount', 'access', 'service', 'priority'])
    membership_types = ListField(StringField())  # ['physical', 'legal']
    
    is_active = BooleanField(default=True)
    
    meta = {'collection': 'member_benefits'}


class ProtectedMaterial(Document):
    """Закрытые материалы для членов"""
    title_key = StringField(required=True)
    description_key = StringField()
    
    file = FileField()
    url = URLField()
    
    required_membership = ListField(StringField())  # Какое членство требуется
    
    uploaded_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'protected_materials'}


# ============================================
# 11. МОНИТОРИНГ САЙТОВ ПИТОМНИКОВ
# ============================================

class SiteMonitor(Document):
    """Мониторинг сайтов питомников"""
    kennel = ReferenceField(Kennel, required=True)
    
    url = URLField(required=True)
    check_frequency = IntField(default=7)  # дней
    
    last_check = DateTimeField()
    last_status_code = IntField()
    last_screenshot = ImageField()
    
    updates = ListField(DictField())  # История изменений
    
    is_active = BooleanField(default=True)
    
    meta = {'collection': 'site_monitors'}


# ============================================
# 12. АУДИТ
# ============================================

class AuditLog(Document):
    """Журнал аудита"""
    user = StringField()  # email
    action = StringField()
    resource_type = StringField()
    resource_id = StringField()
    
    changes = DictField()
    ip_address = StringField()
    
    timestamp = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'audit_logs',
        'ordering': ['-timestamp']
    }
