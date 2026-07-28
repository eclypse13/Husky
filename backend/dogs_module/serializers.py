from typing import Optional

from rest_framework import serializers
from .models import (
    Dog, Breeder, Owner, Title, MedicalRecord,
    ShowEvent, ShowResult,
)


def _best_dog_photo_url(dog) -> Optional[str]:
    """Ссылка для dog_photo: стабильный прокси на ЯД, иначе исходник."""
    if dog.photo_yadisk_path:
        return f"/api/dogs/photos/{dog.id}/raw/"
    return dog.photo_url or None


# Общие миксины валидации
class IdRangeValidatorMixin:
    """Проверяет что id_to >= id_from (если оба заданы)."""

    def validate(self, data):
        id_from = data.get('id_from', 1)
        id_to = data.get('id_to')
        if id_to is not None and id_to < id_from:
            raise serializers.ValidationError("id_to должен быть ≥ id_from.")
        return data


class DateRangeValidatorMixin:
    """Проверяет формат DD.MM.YYYY и что date_to >= date_from."""

    def validate(self, data):
        from datetime import datetime
        fmt = '%d.%m.%Y'
        try:
            dt_from = datetime.strptime(data['date_from'], fmt)
        except (ValueError, KeyError):
            raise serializers.ValidationError(
                {'date_from': 'Формат DD.MM.YYYY, например 01.01.2026'}
            )
        if data.get('date_to'):
            try:
                dt_to = datetime.strptime(data['date_to'], fmt)
            except ValueError:
                raise serializers.ValidationError(
                    {'date_to': 'Формат DD.MM.YYYY, например 31.01.2026'}
                )
            if dt_to < dt_from:
                raise serializers.ValidationError('date_to должна быть >= date_from')
        return data


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


# class LitterSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Litter
#         fields = [
#             'id', 'date_of_birth',
#             'litter_male_count', 'litter_female_count', 'litter_undef_count'
#         ]


class DogParentSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    sex_display = serializers.SerializerMethodField()
    dog_photo = serializers.SerializerMethodField()

    class Meta:
        model = Dog
        fields = [
            'id', 'uuid', 'zoo_hash', 'display_name',
            'registered_name', 'call_name',
            'sex', 'sex_display',
            'year_of_birth', 'color', 'photo_url', 'dog_photo',
        ]

    def get_display_name(self, obj): return obj.display_name

    def get_sex_display(self, obj):  return obj.sex_display

    def get_dog_photo(self, obj): return _best_dog_photo_url(obj)


class DogListSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    sex_display = serializers.SerializerMethodField()
    breeder_names = serializers.SerializerMethodField()
    dog_photo = serializers.SerializerMethodField()

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
            'rating', 'dog_photo',
        ]

    def get_display_name(self, obj): return obj.display_name

    def get_sex_display(self, obj): return obj.sex_display

    def get_breeder_names(self, obj): return [b.name for b in obj.breeders.all()]

    def get_dog_photo(self, obj): return _best_dog_photo_url(obj)


class DogDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    sex_display = serializers.SerializerMethodField()
    is_alive = serializers.SerializerMethodField()
    dog_photo = serializers.SerializerMethodField()

    dam = DogParentSerializer(read_only=True)
    sire = DogParentSerializer(read_only=True)
    breeders = BreederSerializer(many=True, read_only=True)
    owners = OwnerSerializer(many=True, read_only=True)
    titles = TitleSerializer(many=True, read_only=True)
    medical_records = MedicalRecordSerializer(many=True, read_only=True)
    # birth_litter = LitterSerializer(read_only=True)

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
            'kennel', 'rating',
            'dam', 'sire',
            'breeders', 'owners',
            'titles', 'medical_records',
            'dog_photo',
            # 'birth_litter',
        ]

    def get_display_name(self, obj): return obj.display_name

    def get_sex_display(self, obj): return obj.sex_display

    def get_is_alive(self, obj): return obj.is_alive

    def get_dog_photo(self, obj): return _best_dog_photo_url(obj)


class PedigreeSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    dam = serializers.SerializerMethodField()
    sire = serializers.SerializerMethodField()
    dog_photo = serializers.SerializerMethodField()

    class Meta:
        model = Dog
        fields = [
            'id', 'uuid', 'display_name', 'registered_name', 'call_name',
            'sex', 'year_of_birth', 'date_of_birth', 'photo_url', 'color',
            'land_of_birth', 'prefix_titles', 'suffix_titles', 'coi',
            'dam', 'sire', 'dog_photo',
        ]

    def get_display_name(self, obj):
        return obj.display_name

    def get_dog_photo(self, obj):
        return _best_dog_photo_url(obj)

    def get_dam(self, obj):
        depth = self.context.get('depth', 3)
        current = self.context.get('current_depth', 0)
        if obj.dam and current < depth:
            return PedigreeSerializer(
                obj.dam, context={**self.context, 'current_depth': current + 1}
            ).data
        return None

    def get_sire(self, obj):
        depth = self.context.get('depth', 3)
        current = self.context.get('current_depth', 0)
        if obj.sire and current < depth:
            return PedigreeSerializer(
                obj.sire, context={**self.context, 'current_depth': current + 1}
            ).data
        return None


# ВЫСТАВКИ
class ShowEventSerializer(serializers.ModelSerializer):
    results_count = serializers.SerializerMethodField()

    class Meta:
        model = ShowEvent
        fields = [
            'id', 'zooportal_show_id', 'title', 'event_date', 'date_end',
            'show_type', 'multiplier',
            'organizer', 'rank', 'city', 'address', 'judges', 'status',
            'results_parsed_at', 'created_at', 'results_count',
        ]

    def get_results_count(self, obj):
        return obj.results.count()


class ShowResultSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_date = serializers.DateField(source='event.event_date', read_only=True)
    event_id = serializers.CharField(source='event.zooportal_show_id', read_only=True)
    show_type = serializers.CharField(source='event.show_type', read_only=True)

    class Meta:
        model = ShowResult
        fields = [
            'id',
            'event_id',
            'event_title',
            'event_date',
            'show_type',
            'show_class',
            'grade',
            'place',
            'titles_won',
            'catalog_count',
            'bonus_points',
            'rating_points',
            'nomination',
        ]


class EventShowResultSerializer(serializers.ModelSerializer):
    dog = DogListSerializer(read_only=True)

    class Meta:
        model = ShowResult
        fields = [
            'id',
            'dog',
            'show_class',
            'grade',
            'place',
            'titles_won',
            'rating_points',
            'nomination',
        ]


# ИМПОРТ — ZOOPORTAL

class ImportZooportalDogSerializer(serializers.Serializer):
    zooportal_id = serializers.CharField(required=True, min_length=1, max_length=20)

    class Meta:
        ref_name = 'ImportZooportalDog'


class ImportZooportalPageSerializer(serializers.Serializer):
    page_num = serializers.IntegerField(required=True, min_value=1)
    max_dogs = serializers.IntegerField(required=False, default=11, min_value=1, max_value=11)
    delay = serializers.FloatField(required=False, default=2.0, min_value=0.5, max_value=10.0)

    class Meta:
        ref_name = 'ImportZooportalPage'


class ImportZooportalRangeSerializer(serializers.Serializer):
    start_page = serializers.IntegerField(required=True, min_value=1)
    end_page = serializers.IntegerField(required=True, min_value=1)
    max_dogs_per_page = serializers.IntegerField(required=False, default=11, min_value=1, max_value=11)
    delay = serializers.FloatField(required=False, default=2.0, min_value=0.5, max_value=10.0)

    def validate(self, data):
        if data['start_page'] > data['end_page']:
            raise serializers.ValidationError("start_page должна быть ≤ end_page")
        return data

    class Meta:
        ref_name = 'ImportZooportalRange'


class TaskResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField()
    check_status_url = serializers.CharField()

    class Meta:
        ref_name = 'TaskResponse'


class TaskStatusResponseSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    status = serializers.CharField()
    message = serializers.CharField(required=False)
    progress = serializers.DictField(required=False)
    result = serializers.DictField(required=False)
    error = serializers.CharField(required=False)

    class Meta:
        ref_name = 'TaskStatusResponse'


# ИМПОРТ — BREEDARCHIVE

class ImportBreedarchiveDogSerializer(serializers.Serializer):
    uuid = serializers.CharField()
    force_update = serializers.BooleanField(default=False, required=False)


class ImportBreedarchiveRecentSerializer(serializers.Serializer):
    pages_count = serializers.IntegerField(default=1, min_value=1, max_value=10)
    start_page = serializers.IntegerField(default=0, min_value=0, max_value=9)
    is_full_sync = serializers.BooleanField(default=False)


class ImportBreedarchiveBrowseSerializer(serializers.Serializer):
    recent_days = serializers.IntegerField(default=1, min_value=1, max_value=30)


class ImportBreedarchiveFullPedigreeSerializer(serializers.Serializer):
    uuid = serializers.CharField()
    force_update = serializers.BooleanField(default=False, required=False)


# ИМПОРТ — HYBRID

class ImportHybridDogSerializer(serializers.Serializer):
    zooportal_id = serializers.CharField(required=True, max_length=20)
    generations = serializers.IntegerField(required=False, default=5, min_value=1, max_value=5)

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
    zooportal_id = serializers.CharField(required=True, max_length=20)
    generations = serializers.IntegerField(required=False, default=5, min_value=1, max_value=5)
    force_update = serializers.BooleanField(required=False, default=False)

    class Meta:
        ref_name = 'ImportHybridFullDog'


class ImportHybridFullPageSerializer(serializers.Serializer):
    page_num = serializers.IntegerField(required=True, min_value=1)
    max_dogs = serializers.IntegerField(required=False, default=11, min_value=1, max_value=11)
    generations = serializers.IntegerField(required=False, default=5, min_value=1, max_value=5)
    delay = serializers.FloatField(required=False, default=2.0, min_value=0.5, max_value=10.0)

    class Meta:
        ref_name = 'ImportHybridFullPage'


class ImportHybridFullRangeSerializer(serializers.Serializer):
    start_page = serializers.IntegerField(required=True, min_value=1)
    end_page = serializers.IntegerField(required=True, min_value=1)
    max_dogs_per_page = serializers.IntegerField(required=False, default=11, min_value=1, max_value=11)
    generations = serializers.IntegerField(required=False, default=5, min_value=1, max_value=5)
    delay = serializers.FloatField(required=False, default=2.0, min_value=0.5, max_value=10.0)
    countdown_between_pages = serializers.IntegerField(required=False, default=20, min_value=1, max_value=600)

    def validate(self, data):
        if data['start_page'] > data['end_page']:
            raise serializers.ValidationError("start_page должна быть ≤ end_page")
        return data

    class Meta:
        ref_name = 'ImportHybridFullRange'


# ИМПОРТ — OFA

class ImportOFADogSerializer(serializers.Serializer):
    dog_id = serializers.IntegerField(required=False, allow_null=True)
    registered_name = serializers.CharField(required=False, allow_blank=True, max_length=500)
    registration_number = serializers.CharField(required=False, allow_blank=True, max_length=255)
    ofa_number = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, data):
        has_search = any([
            data.get('registered_name'),
            data.get('registration_number'),
            data.get('ofa_number'),
        ])
        if not data.get('dog_id') and not has_search:
            raise serializers.ValidationError(
                "Нужен хотя бы один параметр: dog_id, registered_name, "
                "registration_number или ofa_number."
            )
        return data


class _OFABulkBase(IdRangeValidatorMixin, serializers.Serializer):
    """Общие поля для bulk OFA-импорта."""
    id_from = serializers.IntegerField(required=False, default=1, min_value=1)
    id_to = serializers.IntegerField(required=False, allow_null=True, default=None)
    limit = serializers.IntegerField(required=False, default=100, min_value=1)
    delay = serializers.FloatField(required=False, default=1.5, min_value=0.5)
    only_without_ofa = serializers.BooleanField(required=False, default=True)


class ImportOFABulkByRegSerializer(_OFABulkBase):
    pass


class ImportOFABulkByNameSerializer(_OFABulkBase):
    pass


# ИМПОРТ — ВЫСТАВКИ
class ImportShowListSerializer(serializers.Serializer):
    date_str = serializers.CharField(help_text='Дата в формате DD.MM.YYYY (например 07.01.2026)')


class ImportShowResultsSerializer(serializers.Serializer):
    show_id = serializers.CharField(help_text='Zooportal ID мероприятия')
    import_missing_dogs = serializers.BooleanField(default=True)
    update_existing_dogs = serializers.BooleanField(required=False, default=True)


class ImportShowDateRangeSerializer(serializers.Serializer):
    date_from = serializers.CharField(help_text='DD.MM.YYYY')
    date_to = serializers.CharField(help_text='DD.MM.YYYY')
    countdown_between = serializers.IntegerField(default=10, min_value=1, max_value=300)


class RecalculateRatingsSerializer(serializers.Serializer):
    year = serializers.IntegerField(required=False, allow_null=True)


class ImportShowsFullSerializer(DateRangeValidatorMixin, serializers.Serializer):
    date_from = serializers.CharField(
        help_text='Дата начала DD.MM.YYYY'
    )
    date_to = serializers.CharField(
        required=False,
        allow_blank=True,
        default=None,
        help_text='Дата конца DD.MM.YYYY (если не указана — только date_from)'
    )


class ImportResultsForDateRangeSerializer(DateRangeValidatorMixin, serializers.Serializer):
    date_from = serializers.CharField(
        help_text='DD.MM.YYYY'
    )
    date_to = serializers.CharField(
        required=False,
        allow_blank=True,
        default=None,
        help_text='DD.MM.YYYY (если не указана — только date_from)'
    )
    only_without_results = serializers.BooleanField(
        default=True,
        help_text='True = пропускать выставки у которых результаты уже есть'
    )
    import_missing_dogs = serializers.BooleanField(
        default=True,
        help_text='True = запускать импорт собак которых нет в БД'
    )
    update_existing_dogs = serializers.BooleanField(required=False,
                                                    default=True,
                                                    help_text='True = запускать обновление импорт собак которые есть в БД'
                                                    )


# Yandex Photo
class PhotoUploadBulkSerializer(serializers.Serializer):
    id_from = serializers.IntegerField(
        default=1,
        help_text="С какого dog_id начать",
    )
    id_to = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="По какой dog_id (null = без ограничения)",
    )
    limit = serializers.IntegerField(
        default=500,
        max_value=2000,
        help_text="Сколько собак взять за один запуск",
    )
    delay = serializers.FloatField(
        default=0.5,
        help_text="Задержка между тасками в секундах",
    )
    only_without_yadisk = serializers.BooleanField(
        default=True,
        help_text="true = только новые (нет фото на ЯД), false = все (проверит байты и обновит изменившиеся)",
    )


class PhotoBackfillHashesSerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        default=1000,
        max_value=50000,
        help_text="Сколько фото обработать за прогон. Повторяй пока scanned > 0",
    )
    id_from = serializers.IntegerField(
        default=1,
        help_text="Начальный dog_id (включительно)",
    )
    id_to = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Конечный dog_id (включительно). Пусто = до конца",
    )


class PhotoBackfillHashesFromSourceSerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        default=1000,
        max_value=50000,
        help_text="Сколько собак обработать за прогон",
    )
    id_from = serializers.IntegerField(
        default=1,
        help_text="Начальный dog_id (включительно)",
    )
    id_to = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Конечный dog_id (включительно). Пусто = до конца",
    )
