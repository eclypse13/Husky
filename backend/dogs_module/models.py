from django.db import models


class Breeder(models.Model):
    uuid = models.CharField(max_length=255, unique=True, blank=True, null=True)
    name = models.CharField(max_length=500)
    is_breeder = models.BooleanField()
    kennel = models.CharField(max_length=500, blank=True, null=True)
    breeder_url = models.CharField(max_length=1000, blank=True, null=True)
    kennel_url = models.CharField(max_length=1000, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'breeder'
        app_label = 'dogs_module'
        verbose_name = 'Заводчик'
        verbose_name_plural = 'Заводчики'

    def __str__(self):
        return self.name or f'Breeder #{self.id}'


class Owner(models.Model):
    uuid = models.CharField(max_length=255, unique=True, blank=True, null=True)
    name = models.CharField(max_length=500)
    is_main_owner = models.BooleanField()
    kennel = models.CharField(max_length=500, blank=True, null=True)
    owner_url = models.CharField(max_length=1000, blank=True, null=True)
    kennel_url = models.CharField(max_length=1000, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'owner'
        app_label = 'dogs_module'
        verbose_name = 'Владелец'
        verbose_name_plural = 'Владельцы'

    def __str__(self):
        return self.name or f'Owner #{self.id}'


class Dog(models.Model):
    # Идентификаторы
    uuid = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    zooportal_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    zoo_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    ofa_appnum = models.CharField(max_length=20, blank=True, null=True, unique=True, db_index=True)

    # Имена
    registered_name = models.CharField(max_length=500, blank=True, null=True)
    call_name = models.CharField(max_length=255, blank=True, null=True)
    link_name = models.CharField(max_length=500, blank=True, null=True)

    # Пол (1 = кобель, 2 = сука)
    SEX_CHOICES = [(1, 'Кобель'), (2, 'Сука')]
    sex = models.IntegerField(choices=SEX_CHOICES)

    # Дата рождения
    year_of_birth = models.IntegerField(blank=True, null=True)
    month_of_birth = models.IntegerField(blank=True, null=True)
    day_of_birth = models.IntegerField(blank=True, null=True)
    date_of_birth = models.DateTimeField(blank=True, null=True)

    # Дата смерти
    year_of_death = models.IntegerField(blank=True, null=True)
    month_of_death = models.IntegerField(blank=True, null=True)
    day_of_death = models.IntegerField(blank=True, null=True)
    date_of_death = models.DateTimeField(blank=True, null=True)

    # География
    land_of_birth = models.CharField(max_length=255, blank=True, null=True)
    land_of_birth_code = models.CharField(max_length=10, blank=True, null=True)
    land_of_standing = models.CharField(max_length=255, blank=True, null=True)

    # Внешность
    size = models.FloatField(blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)
    color = models.CharField(max_length=255, blank=True, null=True)
    color_marking = models.CharField(max_length=255, blank=True, null=True)
    eyes_color = models.CharField(max_length=100, blank=True, null=True)
    variety = models.CharField(max_length=255, blank=True, null=True)
    distinguishing_features = models.CharField(max_length=1000, blank=True, null=True)
    photo_url = models.CharField(max_length=1000, blank=True, null=True)
    photo_yadisk_path = models.CharField(
        max_length=500, blank=True, null=True,
        verbose_name='Путь фото на Яндекс.Диске',
    )
    photo_yadisk_url = models.TextField(null=True, blank=True, verbose_name='Публичная ссылка фото на Яндекс.Диске')
    photo_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    # Титулы
    prefix_titles = models.CharField(max_length=500, blank=True, null=True)
    suffix_titles = models.CharField(max_length=500, blank=True, null=True)
    other_titles = models.CharField(max_length=500, blank=True, null=True)
    rating = models.IntegerField(default=0, blank=True, null=True)
    rating_updated_at = models.DateTimeField(blank=True, null=True)

    # Регистрация
    registration_status = models.IntegerField(blank=True, null=True)
    registration_number = models.CharField(max_length=255, blank=True, null=True)
    brand_chip = models.CharField(max_length=255, blank=True, null=True)

    # Родословная
    coi = models.FloatField(blank=True, null=True)
    coi_updated_on = models.DateTimeField(blank=True, null=True)
    incomplete_pedigree = models.BooleanField(blank=True, null=True)

    # Статусы
    locked = models.BooleanField(blank=True, null=True)
    removed = models.BooleanField(blank=True, null=True)
    show_ad = models.BooleanField(blank=True, null=True)
    is_new = models.BooleanField(blank=True, null=True)
    modified = models.BooleanField(blank=True, null=True)
    modified_at = models.DateTimeField(blank=True, null=True)

    # Здоровье
    health_info_general = models.JSONField(blank=True, null=True)
    health_info_genetic = models.JSONField(blank=True, null=True)
    neutered = models.BooleanField(blank=True, null=True)
    approved_for_breeding = models.BooleanField(blank=True, null=True)
    frozen_semen = models.BooleanField(blank=True, null=True)
    artificial_insemination = models.BooleanField(blank=True, null=True)

    # Источник и прочее
    source = models.CharField(max_length=255, blank=True, null=True)
    has_conflicts = models.BooleanField(blank=True, null=True)
    conflicts = models.JSONField(blank=True, null=True)
    kennel = models.CharField(max_length=500, blank=True, null=True)
    notes = models.CharField(max_length=2000, blank=True, null=True)
    data_correctness_notes = models.CharField(max_length=2000, blank=True, null=True)
    club = models.CharField(max_length=255, blank=True, null=True)
    sports = models.JSONField(blank=True, null=True)

    # Мать (dam)
    dam = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='children_as_dam',
        db_column='dam_id'
    )
    dam_uuid = models.CharField(max_length=255, blank=True, null=True)
    dam_name = models.CharField(max_length=500, blank=True, null=True)
    dam_link_name = models.CharField(max_length=500, blank=True, null=True)

    # Отец (sire)
    sire = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='children_as_sire',
        db_column='sire_id'
    )
    sire_uuid = models.CharField(max_length=255, blank=True, null=True)
    sire_name = models.CharField(max_length=500, blank=True, null=True)
    sire_link_name = models.CharField(max_length=500, blank=True, null=True)

    # Помёт рождения (зарезервировано для будущего использования)
    birth_litter = models.IntegerField(blank=True, null=True, db_column='birth_litter_id')

    # ManyToMany связи
    breeders = models.ManyToManyField(
        Breeder,
        through='Dogbreederlink',
        related_name='dogs'
    )
    owners = models.ManyToManyField(
        Owner,
        through='Dogownerlink',
        related_name='dogs'
    )
    siblings = models.ManyToManyField(
        'self',
        through='Dogsiblinglink',
        symmetrical=False,
        related_name='sibling_of'
    )

    def save(self, *args, **kwargs):
        if not self.zoo_hash and self.registered_name and self.sex:
            self.zoo_hash = self.generate_zoo_hash()

        super().save(*args, **kwargs)

    @staticmethod
    def compute_zoo_hash(name: str, sex: int):
        import hashlib
        if not name or not sex:
            return None
        normalized = name.strip().lower()
        sex_str = 'male' if sex == 1 else 'female' if sex == 2 else None
        if not sex_str:
            return None
        return hashlib.sha256(f"{normalized}|{sex_str}".encode('utf-8')).hexdigest()

    def generate_zoo_hash(self):
        name = self.registered_name or self.call_name or ''
        sex = self.sex or 0
        return self.compute_zoo_hash(name, sex)

    class Meta:
        managed = True
        db_table = 'dog'
        app_label = 'dogs_module'
        verbose_name = 'Собака'
        verbose_name_plural = 'Собаки'
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['zooportal_id']),
            models.Index(fields=['zoo_hash']),
            models.Index(fields=['sex', 'year_of_birth']),
        ]

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.call_name or self.registered_name or f'Dog #{self.id}'

    @property
    def sex_display(self):
        return 'Кобель' if self.sex == 1 else 'Сука'

    @property
    def is_alive(self):
        return self.date_of_death is None


# class Litter(models.Model):
#     date_of_birth = models.DateTimeField(blank=True, null=True)
#     litter_male_count = models.IntegerField(blank=True, null=True)
#     litter_female_count = models.IntegerField(blank=True, null=True)
#     litter_undef_count = models.IntegerField(blank=True, null=True)
#     sire = models.ForeignKey(
#         Dog, on_delete=models.SET_NULL, blank=True, null=True,
#         related_name='litters_as_sire'
#     )
#     dam = models.ForeignKey(
#         Dog, on_delete=models.SET_NULL, blank=True, null=True,
#         related_name='litters_as_dam'
#     )
#     mating_partner = models.ForeignKey(
#         Dog, on_delete=models.SET_NULL, blank=True, null=True,
#         related_name='litters_as_mating_partner'
#     )
#
#     class Meta:
#         managed = True
#         db_table = 'litter'
#         app_label = 'dogs_module'
#         verbose_name = 'Помёт'
#         verbose_name_plural = 'Помёты'
#
#     def __str__(self):
#         dam_name = self.dam.display_name if self.dam else '?'
#         sire_name = self.sire.display_name if self.sire else '?'
#         date = self.date_of_birth.strftime('%d.%m.%Y') if self.date_of_birth else '?'
#         return f'{dam_name} × {sire_name} ({date})'

class DogBestrussianRating(models.Model):
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name='bestrussian_ratings')
    year = models.PositiveSmallIntegerField()
    position = models.PositiveSmallIntegerField(blank=True, null=True)
    points = models.PositiveSmallIntegerField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'dog_bestrussian_rating'
        app_label = 'dogs_module'
        unique_together = [('dog', 'year')]
        verbose_name = 'Рейтинг Best Russian Dog'
        verbose_name_plural = 'Рейтинги Best Russian Dog'

    def __str__(self):
        return f'{self.dog_id} — {self.year}: #{self.position}'

class Dogbreederlink(models.Model):
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, db_column='dog_id')
    breeder = models.ForeignKey(Breeder, on_delete=models.CASCADE, db_column='breeder_id')

    class Meta:
        managed = True
        db_table = 'dogbreederlink'
        app_label = 'dogs_module'
        unique_together = (('dog', 'breeder'),)


class Dogownerlink(models.Model):
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, db_column='dog_id')
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE, db_column='owner_id')

    class Meta:
        managed = True
        db_table = 'dogownerlink'
        app_label = 'dogs_module'
        unique_together = (('dog', 'owner'),)


class Dogsiblinglink(models.Model):
    dog = models.ForeignKey(
        Dog, on_delete=models.CASCADE,
        db_column='dog_id', related_name='sibling_links_as_dog'
    )
    sibling = models.ForeignKey(
        Dog, on_delete=models.CASCADE,
        db_column='sibling_id', related_name='sibling_links_as_sibling'
    )

    class Meta:
        managed = True
        db_table = 'dogsiblinglink'
        app_label = 'dogs_module'
        unique_together = (('dog', 'sibling'),)


class Title(models.Model):
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name='titles')
    short_name = models.CharField(max_length=100)
    long_name = models.CharField(max_length=500, blank=True, null=True)
    is_prefix = models.BooleanField()
    has_winner_year = models.BooleanField(blank=True, null=True)
    winner_year = models.IntegerField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'title'
        app_label = 'dogs_module'
        verbose_name = 'Титул'
        verbose_name_plural = 'Титулы'
        unique_together = (('dog', 'short_name', 'country'),)

    def __str__(self):
        return f'{self.short_name} — {self.dog.display_name}'


class MedicalRecord(models.Model):
    dog = models.ForeignKey(
        Dog, on_delete=models.CASCADE,
        blank=True, null=True, related_name='medical_records'
    )
    registry = models.CharField(max_length=255)
    test_date = models.DateTimeField(blank=True, null=True)
    report_date = models.DateTimeField(blank=True, null=True)
    age_in_months = models.IntegerField(blank=True, null=True)
    conclusion = models.CharField(max_length=1000, blank=True, null=True)
    ofa_number = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255)
    notes = models.CharField(max_length=1000, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'medical_record'
        app_label = 'dogs_module'
        verbose_name = 'Медицинская запись'
        verbose_name_plural = 'Медицинские записи'
        constraints = [
            models.UniqueConstraint(
                fields=["dog", "ofa_number"],
                name="unique_dog_ofa_number",
                condition=models.Q(ofa_number__isnull=False),
            )
        ]
        ordering = ["-test_date"]

    def __str__(self):
        dog_name = self.dog.display_name if self.dog else '?'
        return f'{self.registry} — {dog_name}'


class Mergelog(models.Model):
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name='merge_logs')
    resolved_fields = models.JSONField(blank=True, null=True)
    old_values = models.JSONField(blank=True, null=True)
    new_values = models.JSONField(blank=True, null=True)
    conflicts = models.JSONField(blank=True, null=True)
    resolved_date = models.DateTimeField()
    resolved_by_user_id = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'mergelog'
        app_label = 'dogs_module'
        verbose_name = 'Лог слияния'
        verbose_name_plural = 'Логи слияния'

    def __str__(self):
        return f'Merge #{self.id} — {self.dog.display_name}'


class ShowEvent(models.Model):
    """Выставочное мероприятие с Zooportal."""

    zooportal_show_id = models.CharField(max_length=50, unique=True, db_index=True)

    title = models.CharField(max_length=1000)
    event_date = models.DateField(blank=True, null=True)
    show_type = models.CharField(
        max_length=20, default='other',
        choices=[
            # Значения синхронизированы с constants/show_types.ShowType
            ('pk', 'Монопородная ПК'),
            ('kchk', 'Монопородная КЧК'),
            ('speciality', 'Специализированная'),
            ('sport', 'Спортивные соревнования'),
            ('world', 'World/Euro Dog Show'),
            ('other', 'Не учитывается'),
        ]
    )
    multiplier = models.FloatField(default=0.0)
    date_end = models.DateField(blank=True, null=True)  # если многодневная

    organizer = models.CharField(max_length=500, blank=True, null=True)
    rank = models.CharField(max_length=255, blank=True, null=True)  # CAC, CACIB...
    city = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=1000, blank=True, null=True)

    judges = models.CharField(max_length=2000, blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)  # "Результаты"

    results_parsed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'show_event'
        app_label = 'dogs_module'
        verbose_name = 'Выставка'
        verbose_name_plural = 'Выставки'
        indexes = [
            models.Index(fields=['event_date']),
            models.Index(fields=['zooportal_show_id']),
        ]

    def __str__(self):
        return f'{self.title} ({self.event_date})'


class ShowResult(models.Model):
    """Результат собаки на выставке."""

    event = models.ForeignKey(
        ShowEvent, on_delete=models.CASCADE, related_name='results'
    )
    dog = models.ForeignKey(
        'Dog', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='show_results'
    )

    catalog_number = models.IntegerField(blank=True, null=True)
    request_id = models.CharField(max_length=50, blank=True, null=True)

    show_class = models.CharField(max_length=100, blank=True, null=True)  # "Юниоров", "Открытый"

    # Результат: "ОТЛ, 1"
    grade = models.CharField(max_length=50, blank=True, null=True)  # "ОТЛ"
    place = models.IntegerField(blank=True, null=True)  # 1

    # Полученные титулы: "CW, CAC, ЧФ, СС"
    titles_won = models.CharField(max_length=500, blank=True, null=True)

    # Рейтинговые очки за это выступление
    rating_points = models.IntegerField(default=0)

    # Количество собак в каталоге — бонус к BOB/ЛПП
    catalog_count = models.IntegerField(default=0)

    # Доп. баллы без коэффициента
    bonus_points = models.IntegerField(default=0)

    # Номинация: main / junior / veteran / working
    nomination = models.CharField(max_length=20, default='main')

    class Meta:
        managed = True
        db_table = 'show_result'
        app_label = 'dogs_module'
        verbose_name = 'Результат выставки'
        verbose_name_plural = 'Результаты выставок'
        unique_together = [('event', 'dog')]
        indexes = [
            models.Index(fields=['dog', 'event']),
        ]

    def __str__(self):
        return f'{self.dog_name} @ {self.event} → {self.grade} {self.place}'


class ShowYearlyRating(models.Model):
    dog = models.ForeignKey(
        'Dog',
        on_delete=models.CASCADE,
        related_name='yearly_ratings'
    )
    year = models.SmallIntegerField(db_index=True)
    nomination = models.CharField(max_length=20, default='main')
    points = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'dogs_module'
        db_table = 'show_yearly_rating'
        unique_together = [('dog', 'year', 'nomination')]
        indexes = [
            models.Index(
                fields=['year', 'nomination'],
                name='yearly_rating_leaderboard_idx',
            ),
        ]

    def __str__(self):
        return f"Dog#{self.dog_id} {self.year}/{self.nomination} = {self.points}"


class ImportTaskProxy(models.Model):
    """Прокси-модель только для отображения пункта в Django Admin sidebar."""

    class Meta:
        managed = False
        app_label = 'dogs_module'
        verbose_name = 'Импорт данных'
        verbose_name_plural = 'Панель импорта'
