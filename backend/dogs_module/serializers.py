# dogs_module/serializers.py
"""
Сериализаторы — конвертируют объекты Django моделей в JSON и обратно.
"""

from rest_framework import serializers
from .models import Dog, Breeder, Owner, Title, MedicalRecord, Litter

class BreederSerializer(serializers.ModelSerializer):
    class Meta:
        model = Breeder
        fields = ['id', 'uuid', 'name', 'kennel', 'breeder_url', 'kennel_url']


class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = ['id', 'uuid', 'name', 'kennel', 'owner_url', 'kennel_url']


class TitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Title
        fields = ['id', 'short_name', 'long_name', 'is_prefix', 'country', 'winner_year']


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ['id', 'registry', 'test_date', 'conclusion', 'ofa_number', 'source']


class LitterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Litter
        fields = [
            'id', 'date_of_birth',
            'litter_male_count', 'litter_female_count', 'litter_undef_count'
        ]


class DogParentSerializer(serializers.ModelSerializer):
    """Краткая информация о родителе (без вложенных)."""
    display_name = serializers.SerializerMethodField()
    sex_display = serializers.SerializerMethodField()

    class Meta:
        model = Dog
        fields = [
            'id', 'uuid', 'zoo_hash', 'display_name',
            'registered_name', 'call_name',
            'sex', 'sex_display',
            'year_of_birth', 'color', 'photo_url'
        ]

    def get_display_name(self, obj):
        return obj.display_name

    def get_sex_display(self, obj):
        return obj.sex_display


# ============================================================
# СПИСОК — для страницы поиска
# ============================================================

class DogListSerializer(serializers.ModelSerializer):
    """
    Краткая информация о собаке для списка/поиска.

    breeder_names — список имён заводчиков (из таблицы breeder через dogbreederlink).
    Это правильный источник данных о питомнике, а НЕ dog.kennel.
    """
    display_name = serializers.SerializerMethodField()
    sex_display = serializers.SerializerMethodField()
    breeder_names = serializers.SerializerMethodField()

    class Meta:
        model = Dog
        fields = [
            'id', 'uuid', 'zoo_hash',
            'display_name', 'registered_name', 'call_name',
            'sex', 'sex_display',
            'year_of_birth', 'date_of_birth',
            'color', 'photo_url',
            'land_of_birth',
            'prefix_titles', 'suffix_titles',
            'breeder_names',
        ]

    def get_display_name(self, obj):
        return obj.display_name

    def get_sex_display(self, obj):
        return obj.sex_display

    def get_breeder_names(self, obj):
        """
        Возвращает список имён заводчиков.
        Источник: breeder.name через ManyToMany (dogbreederlink).
        """
        return [b.name for b in obj.breeders.all()]


# ============================================================
# ДЕТАЛИ — полная информация
# ============================================================

class DogDetailSerializer(serializers.ModelSerializer):
    """Полная информация о собаке."""
    display_name = serializers.SerializerMethodField()
    sex_display = serializers.SerializerMethodField()
    is_alive = serializers.SerializerMethodField()

    dam = DogParentSerializer(read_only=True)
    sire = DogParentSerializer(read_only=True)
    breeders = BreederSerializer(many=True, read_only=True)
    owners = OwnerSerializer(many=True, read_only=True)
    titles = TitleSerializer(many=True, read_only=True)
    medical_records = MedicalRecordSerializer(many=True, read_only=True)
    birth_litter = LitterSerializer(read_only=True)

    class Meta:
        model = Dog
        fields = [
            'id', 'uuid', 'zoo_hash', 'zooportal_id',
            'display_name', 'registered_name', 'call_name', 'link_name',
            'sex', 'sex_display',
            'year_of_birth', 'month_of_birth', 'day_of_birth', 'date_of_birth',
            'year_of_death', 'date_of_death', 'is_alive',
            'land_of_birth', 'land_of_birth_code', 'land_of_standing',
            'size', 'weight', 'color', 'color_marking', 'eyes_color',
            'variety', 'photo_url',
            'prefix_titles', 'suffix_titles', 'other_titles',
            'registration_number', 'brand_chip',
            'coi', 'incomplete_pedigree',
            'neutered', 'approved_for_breeding',
            'kennel',
            'dam', 'sire',
            'breeders', 'owners',
            'titles', 'medical_records',
            'birth_litter',
        ]

    def get_display_name(self, obj):
        return obj.display_name

    def get_sex_display(self, obj):
        return obj.sex_display

    def get_is_alive(self, obj):
        return obj.is_alive


# ============================================================
# РОДОСЛОВНАЯ — рекурсивное дерево
# ============================================================

class PedigreeSerializer(serializers.ModelSerializer):
    """Рекурсивное дерево родословной."""
    display_name = serializers.SerializerMethodField()
    dam = serializers.SerializerMethodField()
    sire = serializers.SerializerMethodField()

    class Meta:
        model = Dog
        fields = [
            'id', 'uuid', 'display_name', 'registered_name', 'call_name',
            'sex', 'year_of_birth', 'date_of_birth', 'photo_url', 'color',
            'land_of_birth', 'prefix_titles', 'suffix_titles', 'coi',
            'dam', 'sire',
        ]

    def get_display_name(self, obj):
        return obj.display_name

    def get_dam(self, obj):
        depth = self.context.get('depth', 3)
        current = self.context.get('current_depth', 0)
        if obj.dam and current < depth:
            return PedigreeSerializer(
                obj.dam,
                context={**self.context, 'current_depth': current + 1}
            ).data
        return None

    def get_sire(self, obj):
        depth = self.context.get('depth', 3)
        current = self.context.get('current_depth', 0)
        if obj.sire and current < depth:
            return PedigreeSerializer(
                obj.sire,
                context={**self.context, 'current_depth': current + 1}
            ).data
        return None

class ImportZooportalDogSerializer(serializers.Serializer):
    """Сериализатор для импорта одной собаки"""
    zooportal_id = serializers.CharField(
        required=True,
        help_text="ID собаки на Zooportal (например: 17516431)",
        min_length=1,
        max_length=20
    )

    class Meta:
        ref_name = 'ImportZooportalDog'


class ImportZooportalPageSerializer(serializers.Serializer):
    """Сериализатор для импорта страницы поиска"""
    page_num = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="Номер страницы поиска (от 1 и выше)"
    )
    max_dogs = serializers.IntegerField(
        required=False,
        default=11,
        min_value=1,
        max_value=11,
        help_text="Максимальное количество собак (по умолчанию 10)"
    )
    delay = serializers.FloatField(
        required=False,
        default=2.0,
        min_value=0.5,
        max_value=10.0,
        help_text="Задержка между собаками в секундах (по умолчанию 2.0)"
    )

    class Meta:
        ref_name = 'ImportZooportalPage'


class ImportZooportalRangeSerializer(serializers.Serializer):
    """Сериализатор для импорта диапазона страниц"""
    start_page = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="Начальная страница (включительно)"
    )
    end_page = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="Конечная страница (включительно)"
    )
    max_dogs_per_page = serializers.IntegerField(
        required=False,
        default=11,
        min_value=1,
        max_value=11,
        help_text="Максимум собак на странице (по умолчанию 10)"
    )
    delay = serializers.FloatField(
        required=False,
        default=2.0,
        min_value=0.5,
        max_value=10.0,
        help_text="Задержка между собаками (по умолчанию 2.0)"
    )

    def validate(self, data):
        if data['start_page'] > data['end_page']:
            raise serializers.ValidationError(
                "start_page должна быть меньше или равна end_page"
            )
        return data

    class Meta:
        ref_name = 'ImportZooportalRange'


class TaskResponseSerializer(serializers.Serializer):
    """Ответ с task_id"""
    task_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField()
    check_status_url = serializers.CharField()

    class Meta:
        ref_name = 'TaskResponse'


class TaskStatusResponseSerializer(serializers.Serializer):
    """Ответ со статусом задачи"""
    task_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField(required=False)
    progress = serializers.DictField(required=False)
    result = serializers.DictField(required=False)
    error = serializers.CharField(required=False)

    class Meta:
        ref_name = 'TaskStatusResponse'


class ImportBreedarchiveDogSerializer(serializers.Serializer):
    uuid = serializers.CharField(help_text="UUID собаки в BreedArchive")
    force_update = serializers.BooleanField(default=False, required=False)


class ImportBreedarchiveRecentSerializer(serializers.Serializer):
    pages_count = serializers.IntegerField(default=1, min_value=1, max_value=10)
    start_page = serializers.IntegerField(default=0, min_value=0, max_value=9)
    is_full_sync = serializers.BooleanField(default=False)


class ImportBreedarchiveBrowseSerializer(serializers.Serializer):
    recent_days = serializers.IntegerField(default=1, min_value=1, max_value=30)

class ImportBreedarchiveFullPedigreeSerializer(serializers.Serializer):
    """Сериализатор для загрузки полной родословной по UUID."""
    uuid = serializers.CharField(
        help_text="UUID собаки в BreedArchive (из URL /animal/view/name-{uuid})"
    )
    force_update = serializers.BooleanField(
        default=False,
        required=False,
        help_text="True — сбросить кеш и загрузить заново даже если собака уже есть в БД",
    )

# ------ hybrid

class ImportHybridDogSerializer(serializers.Serializer):
    zooportal_id = serializers.CharField(required=True, max_length=20)
    generations  = serializers.IntegerField(required=False, default=5, min_value=1, max_value=5)

    class Meta:
        ref_name = 'ImportHybridDog'


class ImportHybridPageSerializer(serializers.Serializer):
    page_num = serializers.IntegerField(required=True, min_value=1)
    max_dogs = serializers.IntegerField(required=False, default=11, min_value=1, max_value=11)
    delay = serializers.FloatField(required=False, default=2.0, min_value=0.5, max_value=10.0)
    generations = serializers.IntegerField(required=False, default=3, min_value=1, max_value=5)

    class Meta:
        ref_name = 'ImportHybridPage'


class ImportHybridRangeSerializer(serializers.Serializer):
    start_page = serializers.IntegerField(required=True, min_value=1)
    end_page = serializers.IntegerField(required=True, min_value=1)
    max_dogs_per_page = serializers.IntegerField(required=False, default=11, min_value=1, max_value=11)
    delay = serializers.FloatField(required=False, default=2.0, min_value=0.5, max_value=10.0)
    generations = serializers.IntegerField(required=False, default=5, min_value=1, max_value=5)
    countdown_between_pages = serializers.IntegerField(required=False, default=5, min_value=1, max_value=600)

    def validate(self, data):
        if data['start_page'] > data['end_page']:
            raise serializers.ValidationError("start_page должна быть ≤ end_page")
        return data

    class Meta:
        ref_name = 'ImportHybridRange'


class ImportHybridFullDogSerializer(serializers.Serializer):
    zooportal_id = serializers.CharField(
        required=True,
        max_length=20,
        help_text="ID собаки на Zooportal"
    )
    generations = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=5,
        help_text="Глубина парсинга Zoo страницы (для fallback родословной)"
    )
    force_update = serializers.BooleanField(
        required=False,
        default=False,
        help_text="True — сбросить BA-кеш и загрузить предков заново"
    )

    class Meta:
        ref_name = 'ImportHybridFullDog'


class ImportHybridFullPageSerializer(serializers.Serializer):
    page_num = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="Номер страницы Zoo поиска"
    )
    max_dogs = serializers.IntegerField(
        required=False,
        default=11,
        min_value=1,
        max_value=11,
    )
    generations = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=5,
    )
    delay = serializers.FloatField(
        required=False,
        default=2.0,
        min_value=0.5,
        max_value=10.0,
    )

    class Meta:
        ref_name = 'ImportHybridFullPage'


class ImportHybridFullRangeSerializer(serializers.Serializer):
    start_page = serializers.IntegerField(required=True, min_value=1)
    end_page = serializers.IntegerField(required=True, min_value=1)
    max_dogs_per_page = serializers.IntegerField(
        required=False, default=11, min_value=1, max_value=11
    )
    generations = serializers.IntegerField(
        required=False, default=5, min_value=1, max_value=5
    )
    delay = serializers.FloatField(
        required=False, default=2.0, min_value=0.5, max_value=10.0
    )
    countdown_between_pages = serializers.IntegerField(
        required=False, default=20, min_value=1, max_value=600,
        help_text="Пауза между страницами в секундах"
    )

    def validate(self, data):
        if data['start_page'] > data['end_page']:
            raise serializers.ValidationError("start_page должна быть ≤ end_page")
        return data

    class Meta:
        ref_name = 'ImportHybridFullRange'


class ImportOFADogSerializer(serializers.Serializer):
    """Импорт OFA записей для одной собаки."""

    dog_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID собаки в БД. Без поисковых параметров — имя и пол берутся из БД.",
    )
    registered_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Имя для поиска на OFA (с начала строки).",
    )
    registration_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Рег. номер AKC/UKC (например WS65368202). Самый точный параметр.",
    )
    ofa_number = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="OFA номер (например SH-22267E48M-C-VPI).",
    )

    def validate(self, data):
        has_search = any([
            data.get("registered_name"),
            data.get("registration_number"),
            data.get("ofa_number"),
        ])
        if not data.get("dog_id") and not has_search:
            raise serializers.ValidationError(
                "Нужен хотя бы один параметр: dog_id, registered_name, "
                "registration_number или ofa_number."
            )
        return data


class ImportOFABulkByRegSerializer(serializers.Serializer):
    """Bulk OFA-импорт по registration_number с диапазоном ID."""

    id_from = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        help_text="Нижняя граница Dog.id (включительно). По умолчанию 1.",
    )
    id_to = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Верхняя граница Dog.id (включительно). None = без ограничения.",
    )
    limit = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
        # max_value=1000,
        help_text="Макс. число собак в выборке. По умолчанию 100.",
    )
    delay = serializers.FloatField(
        required=False,
        default=1.5,
        min_value=0.5,
        help_text="Пауза между задачами в секундах. По умолчанию 1.5.",
    )
    only_without_ofa = serializers.BooleanField(
        required=False,
        default=True,
        help_text="True = пропустить собак с уже существующими OFA-записями.",
    )

    def validate(self, data):
        id_from = data.get("id_from", 1)
        id_to = data.get("id_to")
        if id_to is not None and id_to < id_from:
            raise serializers.ValidationError(
                "id_to должен быть больше или равен id_from."
            )
        return data


class ImportOFABulkByNameSerializer(serializers.Serializer):
    """Bulk OFA-импорт по registered_name с диапазоном ID."""

    id_from = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        help_text="Нижняя граница Dog.id (включительно). По умолчанию 1.",
    )
    id_to = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Верхняя граница Dog.id (включительно). None = без ограничения.",
    )
    limit = serializers.IntegerField(
        required=False,
        default=100,
        min_value=1,
        # max_value=1000,
        help_text="Макс. число собак в выборке. По умолчанию 100.",
    )
    delay = serializers.FloatField(
        required=False,
        default=1.5,
        min_value=0.5,
        help_text="Пауза между задачами в секундах. По умолчанию 1.5.",
    )
    only_without_ofa = serializers.BooleanField(
        required=False,
        default=True,
        help_text="True = пропустить собак с уже существующими OFA-записями.",
    )

    def validate(self, data):
        id_from = data.get("id_from", 1)
        id_to = data.get("id_to")
        if id_to is not None and id_to < id_from:
            raise serializers.ValidationError(
                "id_to должен быть больше или равен id_from."
            )
        return data
