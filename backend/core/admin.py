"""
Кастомная реализация админки для MongoEngine моделей
"""

from collections import OrderedDict
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.admin.widgets import AdminTextareaWidget, AdminFileWidget
from mongoengine.fields import StringField, EmailField, BooleanField, DateTimeField, IntField, FloatField, ListField, \
    DictField, ReferenceField, URLField, FileField, ImageField
from .models import (
    ContentDictionary, ContentRevision,
    User, News, Page, Gallery,
    Judge, JudgeDetails, FastLink,
    Event, EventReport, Season,
    Race, Seminar,
    EventReportPhoto, EventReportVideo,
    BreedStandard, BreedArticle,
    ClubDocument, ClubStats,
    BoardMember, President,
    PresidentBadge, PresidentAchievement,
    WorkingGroup, MembershipPlan,
    Kennel, Dog, Litter,
    Application,
    Achievement, MembershipPayment,
    MemberBenefit, ProtectedMaterial,
    SiteMonitor, AuditLog
)


# Базовые классы и утилиты

class MongoAdminForm(forms.Form):
    """Базовая форма для MongoEngine документов"""
    pass


def create_mongo_form(model_class, fields=None, exclude=None):
    """Динамически создает форму для MongoEngine документа"""
    form_fields = {}

    if fields is None:
        for field_name, field in model_class._fields.items():
            if exclude and field_name in exclude:
                continue

            if isinstance(field, StringField):
                if field.max_length:
                    form_fields[field_name] = forms.CharField(
                        max_length=field.max_length,
                        required=field.required,
                        label=field_name.replace('_', ' ').title()
                    )
                else:
                    form_fields[field_name] = forms.CharField(
                        widget=forms.Textarea,
                        required=field.required,
                        label=field_name.replace('_', ' ').title()
                    )
            elif isinstance(field, EmailField):
                form_fields[field_name] = forms.EmailField(
                    required=field.required,
                    label=field_name.replace('_', ' ').title()
                )
            elif isinstance(field, BooleanField):
                form_fields[field_name] = forms.BooleanField(
                    required=False,
                    label=field_name.replace('_', ' ').title()
                )
            elif isinstance(field, DateTimeField):
                form_fields[field_name] = forms.DateTimeField(
                    required=field.required,
                    label=field_name.replace('_', ' ').title()
                )
            elif isinstance(field, IntField):
                form_fields[field_name] = forms.IntegerField(
                    required=field.required,
                    label=field_name.replace('_', ' ').title()
                )
            elif isinstance(field, FloatField):
                form_fields[field_name] = forms.FloatField(
                    required=field.required,
                    label=field_name.replace('_', ' ').title()
                )
            elif isinstance(field, ListField):
                form_fields[field_name] = forms.CharField(
                    widget=forms.Textarea,
                    required=field.required,
                    label=field_name.replace('_', ' ').title(),
                    help_text='Введите значения через запятую'
                )
            elif isinstance(field, URLField):
                form_fields[field_name] = forms.URLField(
                    required=field.required,
                    label=field_name.replace('_', ' ').title()
                )
            else:
                form_fields[field_name] = forms.CharField(
                    required=field.required,
                    label=field_name.replace('_', ' ').title()
                )

    return type(f'{model_class.__name__}Form', (MongoAdminForm,), form_fields)


# Формы для моделей

class ContentDictionaryAdminForm(forms.Form):
    key = forms.CharField(max_length=200, label='Ключ', help_text='Уникальный ключ для контента')
    value = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}), label='Значение',
                            help_text='Markdown/HTML контент')
    page = forms.CharField(max_length=100, required=False, label='Страница', initial='general')
    locale = forms.CharField(max_length=10, required=False, label='Локаль', initial='ru')
    updated_by = forms.EmailField(required=False, label='Обновлено пользователем')


class UserAdminForm(forms.Form):
    email = forms.EmailField(label='Email')
    first_name = forms.CharField(max_length=100, required=False, label='Имя')
    last_name = forms.CharField(max_length=100, required=False, label='Фамилия')
    password_hash = forms.CharField(widget=forms.PasswordInput, required=False, label='Пароль (хэш)')

    roles = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        label='Роли',
        help_text='Одна роль на строку: admin_roles, section_admin, presidium, member_physical, member_legal'
    )

    is_nkp_member = forms.BooleanField(required=False, label='Член НКП')
    membership_type = forms.ChoiceField(
        choices=[('', '---'), ('physical', 'Физ. лицо'), ('legal', 'Юр. лицо')],
        required=False,
        label='Тип членства'
    )
    membership_started_at = forms.DateTimeField(required=False, label='Членство началось')
    membership_expires_at = forms.DateTimeField(required=False, label='Членство истекает')

    phone = forms.CharField(max_length=20, required=False, label='Телефон')
    city = forms.CharField(max_length=100, required=False, label='Город')
    is_active = forms.BooleanField(required=False, initial=True, label='Активен')


class NewsAdminForm(forms.Form):
    title_key = forms.CharField(max_length=200, label='Ключ заголовка')
    lead_key = forms.CharField(required=False, label='Ключ лида')
    body_key = forms.CharField(required=False, widget=forms.Textarea, label='Ключ тела статьи')
    slug = forms.SlugField(required=False, label='Slug')
    tags = forms.CharField(required=False, label='Теги', help_text='Через запятую')
    is_featured = forms.BooleanField(required=False, label='Избранное')
    published_at = forms.DateTimeField(required=False, label='Дата публикации')


class EventAdminForm(forms.Form):
    title_key = forms.CharField(max_length=200, label='Ключ названия')
    description_key = forms.CharField(required=False, widget=forms.Textarea, label='Ключ описания')
    event_type = forms.ChoiceField(
        choices=[('exhibition', 'Выставка'), ('seminar', 'Семинар'), ('meeting', 'Встреча'), ('other', 'Другое')],
        label='Тип мероприятия'
    )
    location = forms.CharField(required=False, label='Место проведения')
    starts_at = forms.DateTimeField(label='Начало')
    ends_at = forms.DateTimeField(required=False, label='Окончание')
    registration_link = forms.URLField(required=False, label='Ссылка на регистрацию')


class DogAdminForm(forms.Form):
    name = forms.CharField(max_length=200, label='Имя')
    registered_name = forms.CharField(required=False, label='Зарегистрированное имя')
    sex = forms.ChoiceField(choices=[('male', 'Кобель'), ('female', 'Сука')], label='Пол')
    date_of_birth = forms.DateTimeField(required=False, label='Дата рождения')
    pedigree_number = forms.CharField(required=False, label='Номер родословной')
    microchip = forms.CharField(required=False, label='Чип')
    titles = forms.CharField(required=False, widget=forms.Textarea, label='Титулы', help_text='Один на строку')
    is_champion = forms.BooleanField(required=False, label='Чемпион')


class KennelAdminForm(forms.Form):
    name = forms.CharField(max_length=200, label='Название питомника')
    prefix = forms.CharField(required=False, label='Префикс/аффикс')
    site_url = forms.URLField(required=False, label='Сайт')
    monitor_enabled = forms.BooleanField(required=False, label='Мониторинг включен')


class ApplicationAdminForm(forms.Form):
    application_type = forms.ChoiceField(
        choices=[
            ('membership', 'Членство'),
            ('litter_registration', 'Регистрация помета'),
            ('kennel_registration', 'Регистрация питомника'),
            ('document_request', 'Запрос документа'),
            ('complaint', 'Жалоба'),
            ('other', 'Другое')
        ],
        label='Тип заявления'
    )
    status = forms.ChoiceField(
        choices=[
            ('new', 'Новое'),
            ('in_progress', 'В обработке'),
            ('done', 'Выполнено'),
            ('rejected', 'Отклонено')
        ],
        initial='new',
        label='Статус'
    )


# Базовый класс MongoModelAdmin

class MongoModelAdmin:
    """Базовый класс для администрирования MongoEngine моделей"""

    model = None
    form_class = None
    list_display = ['__str__']
    list_filter = []
    search_fields = []
    readonly_fields = []
    fieldsets = None
    ordering = None

    # новые поля для меню
    menu_group = 'other'
    menu_group_title = 'Прочее'
    menu_order = 100
    show_in_menu = True

    def __init__(self, model, admin_site):
        self.model = model
        self.admin_site = admin_site

        if self.form_class is None:
            self.form_class = create_mongo_form(model)

    def get_list_display(self):
        return self.list_display

    def get_search_fields(self):
        return self.search_fields

    def get_list_filter(self):
        return self.list_filter


# Админ-классы для моделей

class ContentDictionaryAdmin(MongoModelAdmin):
    form_class = ContentDictionaryAdminForm
    list_display = ['key', 'page', 'locale', 'updated_at', 'updated_by']
    list_filter = ['page', 'locale']
    search_fields = ['key', 'value', 'page']
    ordering = ['page', 'key']


class ContentRevisionAdmin(MongoModelAdmin):
    list_display = ['content_key', 'changed_by', 'changed_at']
    list_filter = ['changed_at']
    search_fields = ['content_key', 'changed_by']
    readonly_fields = ['content_key', 'old_value', 'new_value', 'changed_by', 'changed_at']
    ordering = ['-changed_at']


class UserAdmin(MongoModelAdmin):
    form_class = UserAdminForm
    list_display = ['email', 'first_name', 'last_name', 'is_nkp_member', 'membership_type', 'is_active', 'created_at']
    list_filter = ['is_nkp_member', 'membership_type', 'is_active', 'roles']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('email', 'first_name', 'last_name', 'password_hash')
        }),
        ('Роли', {
            'fields': ('roles',)
        }),
        ('Членство', {
            'fields': ('is_nkp_member', 'membership_type', 'membership_started_at', 'membership_expires_at')
        }),
        ('Профиль', {
            'fields': ('phone', 'city', 'avatar')
        }),
        ('Статус', {
            'fields': ('is_active', 'created_at', 'last_login')
        }),
    )


class NewsAdmin(MongoModelAdmin):
    form_class = NewsAdminForm
    list_display = ['title_key', 'slug', 'is_featured', 'author', 'published_at']
    list_filter = ['is_featured', 'published_at']
    search_fields = ['title_key', 'slug', 'tags']
    ordering = ['-published_at']


class PageAdmin(MongoModelAdmin):
    list_display = ['slug', 'title_key', 'is_published', 'created_at']
    list_filter = ['is_published', 'created_at']
    search_fields = ['slug', 'title_key']
    ordering = ['-created_at']


class GalleryAdmin(MongoModelAdmin):
    list_display = ['title_key', 'is_highlight', 'created_at']
    list_filter = ['is_highlight', 'created_at']
    search_fields = ['title_key']
    ordering = ['-created_at']


class JudgeAdmin(MongoModelAdmin):
    list_display = ['name', 'rank']
    search_fields = ['name', 'rank']
    ordering = ['name']


class JudgeDetailsAdmin(MongoModelAdmin):
    list_display = ['title']
    search_fields = ['title']
    ordering = ['title']


class FastLinkAdmin(MongoModelAdmin):
    list_display = ['title']
    search_fields = ['title']
    ordering = ['title']


class EventAdmin(MongoModelAdmin):
    form_class = EventAdminForm
    list_display = ['title_key', 'event_type', 'location', 'starts_at']
    list_filter = ['event_type', 'starts_at']
    search_fields = ['title_key', 'location']
    ordering = ['-starts_at']


class EventReportPhotoAdmin(MongoModelAdmin):
    list_display = ["report", "file", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["report__event__title_key"]

class EventReportVideoAdmin(MongoModelAdmin):
    list_display = ["report", "file", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["report__event__title_key"]

class EventReportAdmin(MongoModelAdmin):
    list_display = ['event', 'created_at']
    list_filter = ['created_at']
    search_fields = ['event__title_key']
    ordering = ['-created_at']
    exclude = ("photos", "videos")

class SeasonAdmin(MongoModelAdmin):
    list_display = ['name', 'start_date', 'end_date']
    list_filter = ['name', 'start_date']
    search_fields = ['name']
    ordering = ['start_date']


class RaceAdmin(MongoModelAdmin):
    list_display = ['title', 'date', 'city']
    list_filter = ['title', 'date', 'city']
    search_fields = ['title', 'city']
    ordering = ['date']


class SeminarAdmin(MongoModelAdmin):
    list_display = ['title_key', 'speaker', 'date']
    list_filter = ['date']
    search_fields = ['title_key']
    ordering = ['-date']


class BreedStandardAdmin(MongoModelAdmin):
    list_display = ['title_key', 'fci_number', 'version', 'approved_date']
    search_fields = ['title_key', 'fci_number']
    ordering = ['-approved_date']


class BreedArticleAdmin(MongoModelAdmin):
    list_display = ['title_key', 'category']
    list_filter = ['category']
    search_fields = ['title_key']
    ordering = ['title_key']


class ClubDocumentAdmin(MongoModelAdmin):
    list_display = ['title_key', 'document_type', "order", 'uploaded_at']
    list_editable = ("order",)
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['title_key']
    ordering = ["order", '-uploaded_at']


class ClubStatsAdmin(MongoModelAdmin):
    list_display = (
        "members_count",
        "kennels_count",
        "dogs_in_archive_count",
        "regions_count",
        "updated_at",
    )

    def has_add_permission(self, request):
        # запрещаем создавать больше одной записи
        if dj_models.ClubStats.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        # обычно не даём удалять, чтобы статистика не исчезла
        return False


class BoardMemberAdmin(MongoModelAdmin):
    list_display = ['name', 'position', 'order', 'email']
    search_fields = ['name', 'position', 'email']
    ordering = ['order', 'name']

class PresidentAdmin(MongoModelAdmin):
    list_display = ["full_name","position","email","phone","is_active",]
    list_filter = ["is_active"]
    search_fields = ["full_name","position","subtitle","email","phone","socials",]
    ordering = ["full_name"]

    fieldsets = (
        ("Основная информация", {"fields": ("full_name","position","subtitle","is_active",)}),
        ("Основной текст", {"fields": ("main_text","highlight_text",)}),
        ("Цитата", {"fields": ("quote",)}),
        ("Контакты", {"fields": ("email","phone","reception_days","socials",)}),
    )


class PresidentBadgeAdmin(MongoModelAdmin):
    list_display = ["text", "president", "is_primary", "sort_order"]
    list_filter = ["is_primary"]
    search_fields = ["text"]
    ordering = ["sort_order"]

    fieldsets = (
        ("Бейдж", {"fields": ("president","icon","text","is_primary","sort_order",)}),
    )


class PresidentAchievementAdmin(MongoModelAdmin):
    list_display = ["year", "title", "president", "sort_order"]
    search_fields = ["year", "title", "text"]
    ordering = ["sort_order", "year"]

    fieldsets = (
        ("Достижение", {"fields": ("president","year","title","text","sort_order",)}),
    )

class WorkingGroupAdmin(MongoModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    ordering = ['name']


class MembershipPlanAdmin(MongoModelAdmin):
    list_display = ['name_key', 'membership_type', 'annual_fee']
    list_filter = ['membership_type']
    search_fields = ['name_key']
    ordering = ['membership_type', 'annual_fee']


class KennelAdmin(MongoModelAdmin):
    form_class = KennelAdminForm
    list_display = ['name', 'prefix', 'owner', 'monitor_enabled', 'created_at']
    list_filter = ['monitor_enabled', 'created_at']
    search_fields = ['name', 'prefix']
    ordering = ['name']


class DogAdmin(MongoModelAdmin):
    form_class = DogAdminForm
    list_display = ['name', 'registered_name', 'sex', 'owner', 'is_champion']
    list_filter = ['sex', 'is_champion', 'date_of_birth']
    search_fields = ['name', 'registered_name', 'pedigree_number', 'microchip']
    ordering = ['name']


class LitterAdmin(MongoModelAdmin):
    list_display = ['kennel', 'sire', 'dam', 'whelped_at', 'status']
    list_filter = ['status', 'whelped_at']
    search_fields = ['kennel__name']
    ordering = ['-whelped_at']


class ApplicationAdmin(MongoModelAdmin):
    form_class = ApplicationAdminForm
    list_display = ['user', 'application_type', 'status', 'created_at']
    list_filter = ['application_type', 'status', 'created_at']
    search_fields = ['user__email']
    ordering = ['-created_at']


class AchievementAdmin(MongoModelAdmin):
    list_display = ['user', 'dog', 'title', 'place', 'achieved_at']
    list_filter = ['achieved_at']
    search_fields = ['title', 'user__email']
    ordering = ['-achieved_at']


class MembershipPaymentAdmin(MongoModelAdmin):
    list_display = ['user', 'amount', 'payment_date', 'period_start', 'period_end']
    list_filter = ['payment_date', 'payment_method']
    search_fields = ['user__email', 'transaction_id']
    ordering = ['-payment_date']


class MemberBenefitAdmin(MongoModelAdmin):
    list_display = ['name_key', 'benefit_type', 'is_active']
    list_filter = ['benefit_type', 'is_active']
    search_fields = ['name_key']
    ordering = ['name_key']


class ProtectedMaterialAdmin(MongoModelAdmin):
    list_display = ['title_key', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['title_key']
    ordering = ['-uploaded_at']


class SiteMonitorAdmin(MongoModelAdmin):
    list_display = ['kennel', 'url', 'last_check', 'last_status_code', 'is_active']
    list_filter = ['is_active', 'last_status_code', 'last_check']
    search_fields = ['kennel__name', 'url']
    ordering = ['-last_check']


class AuditLogAdmin(MongoModelAdmin):
    list_display = ['user', 'action', 'resource_type', 'resource_id', 'timestamp']
    list_filter = ['action', 'resource_type', 'timestamp']
    search_fields = ['user', 'resource_type', 'resource_id']
    readonly_fields = ['user', 'action', 'resource_type', 'resource_id', 'changes', 'ip_address', 'timestamp']
    ordering = ['-timestamp']


# Реестр и регистрация моделей

ADMIN_REGISTRY = {
    ContentDictionary: ContentDictionaryAdmin,
    ContentRevision: ContentRevisionAdmin,
    User: UserAdmin,
    News: NewsAdmin,
    Page: PageAdmin,
    Gallery: GalleryAdmin,
    Judge: JudgeAdmin,
    JudgeDetails: JudgeDetailsAdmin,
    FastLink: FastLinkAdmin,
    Event: EventAdmin,
    EventReport: EventReportAdmin,
    EventReportPhoto: EventReportPhotoAdmin,
    EventReportVideo: EventReportVideoAdmin,
    Season: SeasonAdmin,
    Race: RaceAdmin,
    Seminar: SeminarAdmin,
    BreedStandard: BreedStandardAdmin,
    BreedArticle: BreedArticleAdmin,
    ClubDocument: ClubDocumentAdmin,
    ClubStats: ClubStatsAdmin,
    BoardMember: BoardMemberAdmin,
    President: PresidentAdmin,
    PresidentBadge: PresidentBadgeAdmin,
    PresidentAchievement: PresidentAchievementAdmin,
    WorkingGroup: WorkingGroupAdmin,
    MembershipPlan: MembershipPlanAdmin,
    Kennel: KennelAdmin,
    Dog: DogAdmin,
    Litter: LitterAdmin,
    Application: ApplicationAdmin,
    Achievement: AchievementAdmin,
    MembershipPayment: MembershipPaymentAdmin,
    MemberBenefit: MemberBenefitAdmin,
    ProtectedMaterial: ProtectedMaterialAdmin,
    SiteMonitor: SiteMonitorAdmin,
    AuditLog: AuditLogAdmin,
}


def get_admin_config(model):
    """Возвращает конфигурацию админки для модели"""
    admin_class = ADMIN_REGISTRY.get(model, MongoModelAdmin)
    return admin_class(model, admin.site)


def register_mongo_model(model, admin_class=None):
    """Регистрирует MongoEngine модель в админке"""
    if admin_class is None:
        admin_class = ADMIN_REGISTRY.get(model, MongoModelAdmin)

    # Инициализируем админ класс
    admin_instance = admin_class(model, admin.site)
    ADMIN_REGISTRY[model] = admin_class

    return admin_instance


# Экспорт для использования в admin_views.py
__all__ = [
    'MongoModelAdmin',
    'ADMIN_REGISTRY',
    'get_admin_config',
    'register_mongo_model',
    'ContentDictionaryAdmin',
    'UserAdmin',
    'NewsAdmin',
    'EventAdmin',
    'DogAdmin',
    'KennelAdmin',
    'ClubStats',
    'DogAdmin',
    'LitterAdmin',
    'ApplicationAdmin',
    'AchievementAdmin',
    'WorkingGroupAdmin',
    'MembershipPaymentAdmin',
    'MemberBenefitAdmin',
    'ProtectedMaterialAdmin',
    'SiteMonitorAdmin',
    'AuditLogAdmin',
]


# группировка моделей по блокам

ADMIN_GROUPS = OrderedDict([
    ('content', {
        'title': 'Контент сайта',
        'models': [
            'ContentDictionary',
            'News',
            'Page',
            'Gallery',
            'FastLink',
            'BreedStandard',
            'BreedArticle',
            'ClubDocument',
            'ProtectedMaterial',
            'ClubStats',
        ]
    }),
    ('people', {
        'title': 'Люди и структура',
        'models': [
            'User',
            'Judge',
            'JudgeDetails',
            'President',
            'BoardMember',
            'WorkingGroup',
        ]
    }),
    ('membership', {
        'title': 'Членство и заявки',
        'models': [
            'MembershipPlan',
            'Application',
            'MembershipPayment',
            'MemberBenefit',
        ]
    }),
    ('breeding', {
        'title': 'Питомники и собаки',
        'models': [
            'Kennel',
            'Dog',
            'Litter',
            'Achievement',
        ]
    }),
    ('events', {
        'title': 'Мероприятия',
        'models': [
            'Event',
            'EventReport',
            'Season',
            'Race',
            'Seminar',
        ]
    }),
    ('system', {
        'title': 'Система',
        'models': [
            'ContentRevision',
            'SiteMonitor',
            'AuditLog',
        ]
    }),
])

HIDDEN_MODELS = {
    'EventReportPhoto',
    'EventReportVideo',
}

def build_grouped_app_list(app_list):
    """
    Получает стандартный app_list от Django admin
    и возвращает новый список блоков по ADMIN_GROUPS.
    """
    model_map = {}

    # Собираем все модели из стандартного app_list
    for app in app_list:
        for model_dict in app.get('models', []):
            object_name = model_dict.get('object_name')
            if object_name:
                model_map[object_name] = model_dict

    grouped_app_list = []

    # Формируем блоки по нашему словарю
    for group_key, group_data in ADMIN_GROUPS.items():
        grouped_models = []

        for model_name in group_data['models']:
            if model_name in HIDDEN_MODELS:
                continue
            if model_name in model_map:
                grouped_models.append(model_map[model_name])

        if grouped_models:
            grouped_app_list.append({
                'name': group_data['title'],
                'app_label': group_key,
                'app_url': '',
                'has_module_perms': True,
                'models': grouped_models,
            })

    # Добавляем все модели, которые не вошли в группы
    grouped_names = {
        model_name
        for group_data in ADMIN_GROUPS.values()
        for model_name in group_data['models']
    } | HIDDEN_MODELS

    other_models = [
        model_dict
        for object_name, model_dict in model_map.items()
        if object_name not in grouped_names
    ]

    if other_models:
        grouped_app_list.append({
            'name': 'Прочее',
            'app_label': 'other',
            'app_url': '',
            'has_module_perms': True,
            'models': other_models,
        })

    return grouped_app_list

# Django ORM admin
from . import models_django as dj_models


class DefaultModelAdmin(admin.ModelAdmin):
    list_display = ['__str__']


@admin.register(dj_models.SiteBannerSettings)
class SiteBannerSettingsAdmin(admin.ModelAdmin):
    list_display = ["id", "is_enabled", "updated_at"]
    fields = ["is_enabled", "message"]
    search_fields = ["message"]


DJANGO_MODELS = [
    dj_models.ContentDictionary,
    dj_models.ContentRevision,
    dj_models.User,
    dj_models.News,
    dj_models.Page,
    dj_models.Gallery,
    dj_models.Judge,
    dj_models.JudgeDetails,
    dj_models.FastLink,
    dj_models.Event,
    dj_models.EventReportPhoto,
    dj_models.EventReportVideo,
    dj_models.EventReport,
    dj_models.Season,
    dj_models.Race,
    dj_models.Seminar,
    dj_models.BreedStandard,
    dj_models.BreedArticle,
    dj_models.ClubDocument,
    dj_models.ClubStats,
    dj_models.WorkingGroup,
    dj_models.BoardMember,
    dj_models.President,
    dj_models.PresidentBadge,
    dj_models.PresidentAchievement,
    dj_models.MembershipPlan,
    dj_models.Kennel,
    dj_models.Dog,
    dj_models.Litter,
    dj_models.Application,
    dj_models.Achievement,
    dj_models.MembershipPayment,
    dj_models.MemberBenefit,
    dj_models.ProtectedMaterial,
    dj_models.SiteMonitor,
    dj_models.AuditLog,
]

for model in DJANGO_MODELS:
    try:
        admin.site.register(model, DefaultModelAdmin)
    except admin.sites.AlreadyRegistered:
        pass


_original_get_app_list = admin.site.get_app_list

def custom_get_app_list(request, app_label=None):
    app_list = _original_get_app_list(request, app_label)

    # Группируем только на главной странице.
    # Если открыт конкретный app_label, можно вернуть как есть.
    if app_label:
        return app_list

    return build_grouped_app_list(app_list)

admin.site.get_app_list = custom_get_app_list