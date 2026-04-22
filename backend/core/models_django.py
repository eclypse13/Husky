from django.core.validators import FileExtensionValidator
from django.db import models
import os
from django.core.exceptions import ValidationError


def validate_svg(value):
    ext = os.path.splitext(value.name)[1]
    valid_exts = ['.svg']
    if not ext.lower() in valid_exts:
        raise ValidationError('Формат файла не поддерживается, выберите файл в формате SVG')


# Choice tuples
ROLE_CHOICES = [
    ('admin_roles', 'admin_roles'),
    ('section_admin', 'section_admin'),
    ('presidium', 'presidium'),
    ('member_physical', 'member_physical'),
    ('member_legal', 'member_legal'),
]

MEMBERSHIP_TYPES = [
    ('physical', 'physical'),
    ('legal', 'legal'),
]

EVENT_TYPES = [
    ('exhibition', 'Выставка'),
    ('seminar', 'Семинар'),
    ('meeting', 'Встреча'),
    ('other', 'Другое'),
]

APPLICATION_TYPES = [
    ('membership', 'Членство'),
    ('litter_registration', 'Регистрация помёта'),
    ('kennel_registration', 'Регистрация питомника'),
    ('document_request', 'Запрос документов'),
    ('complaint', 'Жалоба'),
    ('other', 'Другое'),
]

APPLICATION_STATUSES = [
    ('new', 'Новая'),
    ('in_progress', 'В процессе'),
    ('done', 'Рассмотрена'),
    ('rejected', 'Отклонена'),
]

LITTER_STATUSES = [
    ('announced', 'announced'),
    ('born', 'born'),
    ('sold', 'sold'),
]

BENEFIT_TYPES = [
    ('discount', 'discount'),
    ('access', 'access'),
    ('service', 'service'),
    ('priority', 'priority'),
]

DOCUMENT_TYPES = [
    ('charter', 'устав'),
    ('regulation', 'регламент'),
    ('standard', 'стандарт'),
    ('form', 'форма'),
]

INITIATIVE_STATES = [
    ('active', 'Активный'),
    ('in developing', 'В разработке'),
    ('planning', 'Планирование'),
]


class ContentDictionary(models.Model):
    key = models.CharField(max_length=200, unique=True)
    value = models.TextField()
    page = models.CharField(max_length=100, default='general')
    locale = models.CharField(max_length=10, default='ru')
    updated_by = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['page', 'key']
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['page']),
            models.Index(fields=['locale']),
            models.Index(fields=['page', 'locale']),
        ]

    def __str__(self):
        return f'{self.key} ({self.page})'


class ContentRevision(models.Model):
    content_key = models.CharField(max_length=200)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    changed_by = models.CharField(max_length=200, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.content_key} @ {self.changed_at:%Y-%m-%d}'


class User(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    password_hash = models.CharField(max_length=255)

    roles = models.JSONField(default=list, blank=True)

    is_nkp_member = models.BooleanField(default=False)
    membership_type = models.CharField(max_length=10, choices=MEMBERSHIP_TYPES, blank=True, null=True)
    membership_started_at = models.DateTimeField(blank=True, null=True)
    membership_expires_at = models.DateTimeField(blank=True, null=True)

    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    kennel = models.ForeignKey('Kennel', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_nkp_member']),
        ]

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email})'.strip()


class News(models.Model):
    title_key = models.CharField(max_length=200)
    lead_key = models.CharField(max_length=255, blank=True)
    body_key = models.TextField(blank=True)

    slug = models.SlugField(unique=True)
    tags = models.JSONField(default=list, blank=True)
    is_featured = models.BooleanField(default=False)
    cover_image = models.ImageField(upload_to='news/', blank=True, null=True)

    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='authored_news')
    published_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.slug


class Page(models.Model):
    slug = models.SlugField(unique=True)
    title_key = models.CharField(max_length=200)
    sections = models.JSONField(default=list, blank=True)

    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.slug


class Gallery(models.Model):
    title_key = models.CharField(max_length=200)
    description_key = models.CharField(max_length=255, blank=True)
    images = models.JSONField(default=list, blank=True)
    is_highlight = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title_key


class Judge(models.Model):
    name = models.CharField(max_length=200, verbose_name='Имя')
    rank = models.CharField(max_length=200, blank=True, verbose_name='Должность')
    email = models.EmailField(max_length=200, blank=True, verbose_name='Эл. почта')
    photo = models.ImageField(upload_to='judges/', blank=True, null=True, verbose_name='Фотография')
    materials = models.CharField(max_length=1000, blank=True, verbose_name='Доп. информация')
    judge_id = models.ForeignKey('JudgeDetails', on_delete=models.SET_NULL,
                                 null=True, blank=True, db_column='judge_id', related_name='judge',
                                 verbose_name='Детальная информация')

    class Meta:
        ordering = ['name']
        verbose_name = "Породный эксперт"
        verbose_name_plural = "Породные эксперты"

    def __str__(self):
        return self.name


class JudgeDetails(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='ID')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    info = models.JSONField(default=list, blank=True, verbose_name='Информация')
    additional_info_title = models.JSONField(default=list, blank=True, verbose_name='Доп. информация заголовок')
    additional_info_text = models.JSONField(default=list, blank=True, verbose_name='Доп. информация текст')
    work_directions = models.JSONField(default=list, blank=True, verbose_name='Направления работы')
    initiatives = models.JSONField(default=list, blank=True, verbose_name='Инициативы и проекты')
    sidebar_text = models.CharField(max_length=200, verbose_name='Текст')
    sidebar_achievements = models.JSONField(default=list, verbose_name='Достижения')
    kennel = models.ForeignKey('Kennel', on_delete=models.SET_NULL, null=True, blank=True, related_name='details',
                               verbose_name='Питомник')
    kennel_url = models.URLField(blank=True, verbose_name='Ссылка на питомник')

    class Meta:
        ordering = ['title']
        verbose_name = "Породный эксперт (подробно)"
        verbose_name_plural = "Породные эксперты (подробно)"

    def __str__(self):
        return self.title


class FastLink(models.Model):
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    link = models.URLField(verbose_name='Ссылка')
    image = models.FileField(upload_to='svgs/', blank=True, null=True,
                             validators=[validate_svg], verbose_name='SVG-картинка')

    class Meta:
        ordering = ['title']
        verbose_name = "Быстрая ссылка"
        verbose_name_plural = "Быстрые ссылки"

    def __str__(self):
        return self.title


class Event(models.Model):
    title_key = models.CharField(max_length=200, verbose_name="Название")
    description_key = models.TextField(blank=True, verbose_name="Описание")
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, blank=True,
                                  verbose_name="Тип мероприятия")
    location = models.CharField(max_length=255, blank=True, verbose_name="Локация")
    starts_at = models.DateTimeField(verbose_name="Начало")
    ends_at = models.DateTimeField(blank=True, null=True, verbose_name="Завершение")

    judges = models.ManyToManyField(Judge, related_name='events', blank=True, verbose_name="Породные эксперты")
    registration_link = models.URLField(blank=True, verbose_name="Ссылка на регистрацию")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        ordering = ['starts_at']
        verbose_name = "Мероприятие"
        verbose_name_plural = "Мероприятия"

    def __str__(self):
        return self.title_key


class EventReport(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reports', verbose_name="Мероприятие")
    # photos = models.JSONField(default=list, blank=True, verbose_name="Фото")
    # videos = models.JSONField(default=list, blank=True, verbose_name="Видео")
    results = models.FileField(
        upload_to="event_reports/results/",
        blank=True,
        null=True,
        verbose_name="Файл с результатами",
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf", "docx", "doc", "rtf",
                    "xlsx", "xls", "ppt", "pptx",
                    "txt"
                ]
            )
        ],
    )

    result_description = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Содержание"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Отчёт о мероприятии"
        verbose_name_plural = "Отчёты о мероприятиях"

    def __str__(self):
        return f'Отчёт для {self.event}'


class EventReportPhoto(models.Model):
    report = models.ForeignKey(
        EventReport,
        on_delete=models.CASCADE,
        related_name="photo_items",
        verbose_name="Отчёт",
    )
    file = models.ImageField(upload_to="event_reports/photos/", verbose_name="Фото")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Фото отчёта"
        verbose_name_plural = "Фото отчёта"


class EventReportVideo(models.Model):
    report = models.ForeignKey(
        EventReport,
        on_delete=models.CASCADE,
        related_name="video_items",
        verbose_name="Отчёт",
    )
    file = models.FileField(upload_to="event_reports/videos/", verbose_name="Видео")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Видео отчёта"
        verbose_name_plural = "Видео отчёта"


class Season(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название сезона')  # Зима 2026
    start_date = models.DateField(verbose_name='Начало')
    end_date = models.DateField(verbose_name='Конец')

    class Meta:
        ordering = ["start_date"]
        verbose_name = "Сезон"
        verbose_name_plural = "Сезоны"

    def __str__(self):
        return self.name


class Race(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название гонки")
    date = models.DateField(verbose_name="Дата проведения")
    location = models.CharField(max_length=255, verbose_name="Место проведения")
    organization = models.CharField(max_length=255, blank=True, verbose_name="Организация")
    organizers = models.CharField(max_length=255, blank=True, verbose_name="Организаторы")
    judge = models.CharField(max_length=255, blank=True, verbose_name="Судья")
    distances = models.CharField(max_length=255, blank=True, verbose_name="Дистанции (например: 4,2 км · 8,3 км)")
    is_qualifying = models.BooleanField(default=True, verbose_name="Квалификационная гонка")
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="races", verbose_name="Сезон")
    city = models.CharField(max_length=100, blank=True, verbose_name="Город")
    participants_count = models.PositiveIntegerField(default=0, verbose_name="Количество участников")
    results_file = models.FileField(upload_to="data/race_results/",blank=True,null=True,verbose_name="JSON-файл с результатами")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Гонка"
        verbose_name_plural = "Гонки"

    def __str__(self):
        return f"{self.title} ({self.date})"


class Seminar(models.Model):
    title_key = models.CharField(max_length=200)
    description_key = models.TextField(blank=True)
    speaker = models.ForeignKey(Judge, on_delete=models.SET_NULL, null=True, blank=True, related_name='seminars',
                                verbose_name='Спикер')
    date = models.DateTimeField(blank=True, null=True, verbose_name='Дата')
    materials = models.JSONField(default=list, blank=True, verbose_name="Материалы")

    class Meta:
        ordering = ['-date']
        verbose_name = "Семинар"
        verbose_name_plural = "Семинары"

    def __str__(self):
        return self.title_key


class BreedStandard(models.Model):
    title_key = models.CharField(max_length=200)
    content_key = models.CharField(max_length=200, blank=True)
    fci_number = models.CharField(max_length=50, blank=True)
    illustrations = models.JSONField(default=list, blank=True)
    version = models.CharField(max_length=50, blank=True)
    approved_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-approved_date']

    def __str__(self):
        return self.title_key


class BreedArticle(models.Model):
    title_key = models.CharField(max_length=200)
    content_key = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=50, choices=[
        ('history', 'history'),
        ('character', 'character'),
        ('care', 'care'),
        ('grooming', 'grooming'),
        ('feeding', 'feeding'),
    ], blank=True)
    videos = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['title_key']

    def __str__(self):
        return self.title_key


class ClubDocument(models.Model):
    title_key = models.CharField(max_length=200, verbose_name="Заголовок")
    description_key = models.TextField(blank=True, verbose_name="Описание")
    file = models.FileField(upload_to='documents/', verbose_name="Файл")
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES, verbose_name="Тип документа")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")
    order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        verbose_name="Порядок"
    )

    class Meta:
        ordering = ["document_type", "order", "-uploaded_at"]
        verbose_name = "Документ клуба"
        verbose_name_plural = "Документы клуба"

    def __str__(self):
        return self.title_key


class ClubStats(models.Model):
    members_count = models.PositiveIntegerField(default=0, verbose_name="Владельцев сибирских хаски")
    kennels_count = models.PositiveIntegerField(default=0, verbose_name="Питомников")
    dogs_in_archive_count = models.PositiveIntegerField(default=0, verbose_name="Собак в архиве")
    regions_count = models.PositiveIntegerField(default=0, verbose_name="Регионов")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Статистика клуба"
        verbose_name_plural = "Статистика клуба"

    def clean(self):
        # гарантируем, что в таблице будет максимум 1 объект
        if ClubStats.objects.exclude(pk=self.pk).exists():
            raise ValidationError("Статистика клуба уже создана. Можно редактировать только одну запись.")

    def save(self, *args, **kwargs):
        self.full_clean()  # запускает clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return "Статистика клуба"


class WorkingGroup(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')

    class Meta:
        ordering = ['name']
        verbose_name = 'Рабочая группа'
        verbose_name_plural = 'Рабочие группы'

    def __str__(self):
        return self.name


class BoardMember(models.Model):
    name = models.CharField(max_length=200, verbose_name='Имя')
    position = models.CharField(max_length=200, blank=True, verbose_name='Должность')
    bio_key = models.CharField(max_length=200, blank=True, verbose_name='Доп. информация')
    photo = models.ImageField(upload_to='board/', blank=True, null=True, verbose_name='Фото')
    email = models.EmailField(blank=True, verbose_name='Почта')
    phone = models.CharField(max_length=50, blank=True, verbose_name='Номер телефона')
    order = models.IntegerField(default=0, verbose_name='Порядок')
    working_group = models.ForeignKey(WorkingGroup, on_delete=models.CASCADE, null=True, related_name='members',
                                      verbose_name="Рабочая группа")

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Член клуба'
        verbose_name_plural = 'Члены клуба'

    def __str__(self):
        return f'{self.name} ({self.position})'


class MembershipPlan(models.Model):
    name_key = models.CharField(max_length=200)
    description_key = models.TextField(blank=True)
    membership_type = models.CharField(max_length=10, choices=MEMBERSHIP_TYPES)
    annual_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    benefits = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['membership_type', 'annual_fee']

    def __str__(self):
        return f'{self.name_key} ({self.membership_type})'


class Kennel(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kennels')
    name = models.CharField(max_length=200)
    prefix = models.CharField(max_length=200, blank=True)
    site_url = models.URLField(blank=True)
    socials = models.JSONField(default=dict, blank=True)
    monitor_enabled = models.BooleanField(default=False)
    last_check_at = models.DateTimeField(blank=True, null=True)
    last_screenshot = models.ImageField(upload_to='kennel_checks/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Dog(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dogs')
    kennel = models.ForeignKey(Kennel, on_delete=models.SET_NULL, null=True, blank=True, related_name='dogs')
    name = models.CharField(max_length=200)
    registered_name = models.CharField(max_length=200, blank=True)
    sex = models.CharField(max_length=10, choices=[('male', 'male'), ('female', 'female')], blank=True)
    date_of_birth = models.DateTimeField(blank=True, null=True)
    pedigree_number = models.CharField(max_length=200, blank=True)
    microchip = models.CharField(max_length=200, blank=True)
    sire = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sired_litters')
    dam = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='whelped_litters')
    titles = models.JSONField(default=list, blank=True)
    is_champion = models.BooleanField(default=False)
    photos = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Litter(models.Model):
    kennel = models.ForeignKey(Kennel, on_delete=models.CASCADE, related_name='litters')
    sire = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name='litters_as_sire')
    dam = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name='litters_as_dam')
    whelped_at = models.DateTimeField(blank=True, null=True)
    puppies_count = models.IntegerField(blank=True, null=True)
    notes_key = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=LITTER_STATUSES, default='announced')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-whelped_at']

    def __str__(self):
        return f'Litter {self.kennel} ({self.whelped_at})'


class Application(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    application_type = models.CharField(max_length=32, choices=APPLICATION_TYPES)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=APPLICATION_STATUSES, default='new')
    history = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.application_type} ({self.status})'


class Achievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    dog = models.ForeignKey(Dog, on_delete=models.SET_NULL, null=True, blank=True, related_name='achievements')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='achievements')
    title = models.CharField(max_length=200, blank=True)
    place = models.IntegerField(blank=True, null=True)
    certificate = models.FileField(upload_to='achievements/', blank=True, null=True)
    achieved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-achieved_at']

    def __str__(self):
        return f'{self.title} ({self.user})'


class MembershipPayment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    period_start = models.DateTimeField(blank=True, null=True)
    period_end = models.DateTimeField(blank=True, null=True)
    payment_method = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f'{self.user.email} - {self.amount}'


class MemberBenefit(models.Model):
    name_key = models.CharField(max_length=200)
    description_key = models.TextField(blank=True)
    benefit_type = models.CharField(max_length=20, choices=BENEFIT_TYPES)
    membership_types = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name_key']

    def __str__(self):
        return self.name_key


class ProtectedMaterial(models.Model):
    title_key = models.CharField(max_length=200)
    description_key = models.TextField(blank=True)
    file = models.FileField(upload_to='protected/', blank=True, null=True)
    url = models.URLField(blank=True)
    required_membership = models.JSONField(default=list, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title_key


class SiteMonitor(models.Model):
    kennel = models.ForeignKey(Kennel, on_delete=models.CASCADE, related_name='monitors')
    url = models.URLField()
    check_frequency = models.IntegerField(default=7)
    last_check = models.DateTimeField(blank=True, null=True)
    last_status_code = models.IntegerField(blank=True, null=True)
    last_screenshot = models.ImageField(upload_to='site_checks/', blank=True, null=True)
    updates = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_check']

    def __str__(self):
        return f'{self.kennel} -> {self.url}'


class AuditLog(models.Model):
    user = models.CharField(max_length=200)
    action = models.CharField(max_length=200)
    resource_type = models.CharField(max_length=200)
    resource_id = models.CharField(max_length=200)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.action} by {self.user}'


class SiteBannerSettings(models.Model):
    is_enabled = models.BooleanField(default=True)
    message = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Настройки баннера сайта"
        verbose_name_plural = "Настройки баннера сайта"

    def __str__(self):
        return "Баннер сайта"
