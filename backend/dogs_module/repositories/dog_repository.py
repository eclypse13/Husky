# dogs_module/repositories/dog_repository.py
"""
Доступ к данным Dog.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ЧТЕНИЕ: одиночные объекты

def get_by_id(dog_id: int) -> Optional["Dog"]:
    from ..models import Dog
    try:
        return Dog.objects.using('dogs_db').get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_repository: dog_id={dog_id} не найдена")
        return None


def get_detail(dog_id) -> "Dog | None":
    """
    Объект Dog с prefetch всех связанных данных для DogDetailSerializer.
    Одним запросом получаем breeders / owners / titles / medical_records.
    """
    from ..models import Dog
    try:
        return (
            Dog.objects.using('dogs_db')
            .select_related('dam', 'sire', 'birth_litter')
            .prefetch_related('breeders', 'owners', 'titles', 'medical_records')
            .get(pk=dog_id)
        )
    except Dog.DoesNotExist:
        return None


def get_missing_zoo_ids(zoo_ids: list) -> list:
    """Из списка zooportal_id возвращает те, которых нет в БД."""
    if not zoo_ids:
        return []
    existing = get_existing_zooportal_ids(zoo_ids)
    return [zid for zid in zoo_ids if zid not in existing]


def get_by_zooportal_id(zooportal_id: str) -> Optional["Dog"]:
    from ..models import Dog
    if not zooportal_id:
        return None
    return Dog.objects.using('dogs_db').filter(
        zooportal_id=str(zooportal_id)
    ).first()

def get_by_uuid(uuid: str) -> Optional["Dog"]:
    from ..models import Dog
    if not uuid:
        return None
    return Dog.objects.using('dogs_db').filter(uuid=uuid).first()


def get_search_params(dog_id: int) -> Optional[dict]:
    """
    Параметры для поиска собаки на OFA: имя, рег. номер, пол, год.
    Обрезание апострофа из имени — domain-правило, живёт здесь т.к.
    нужно только для построения поискового запроса к OFA.
    """
    from ..models import Dog
    try:
        dog = Dog.objects.using('dogs_db').only(
            'id', 'registered_name', 'registration_number',
            'sex', 'year_of_birth', 'date_of_birth',
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_repository: dog_id={dog_id} не найдена")
        return None

    year = dog.year_of_birth if (dog.year_of_birth and dog.year_of_birth > 0) else None
    if not year and dog.date_of_birth:
        year = dog.date_of_birth.year

    name = dog.registered_name or ''
    for apostrophe in ["'", '\u2019', '\u2018']:
        if apostrophe in name:
            name = name.replace(apostrophe, '').strip()
            break

    return {
        'registered_name': name,
        'registration_number': dog.registration_number,
        'sex': dog.sex,
        'expected_year': year,
    }


def get_identity_fields(dog_id: int) -> Optional["Dog"]:
    """Лёгкая выборка для сверки личности собаки с OFA."""
    from ..models import Dog
    try:
        return Dog.objects.using('dogs_db').only(
            'id', 'sex', 'year_of_birth', 'date_of_birth'
        ).get(pk=dog_id)
    except Dog.DoesNotExist:
        return None


def get_coi_map(dog_ids) -> dict:
    """{id: coi} для набора id."""
    from ..models import Dog
    if not dog_ids:
        return {}
    return dict(
        Dog.objects.using('dogs_db')
        .filter(id__in=dog_ids)
        .values_list('id', 'coi')
    )


def get_by_ids(dog_ids) -> list:
    """Объекты Dog по списку id."""
    from ..models import Dog
    if not dog_ids:
        return []
    return list(Dog.objects.using('dogs_db').filter(id__in=dog_ids))


def get_siblings(dog) -> list:
    """Однопомётники (та же пара родителей), исключая саму собаку."""
    from ..models import Dog
    return list(
        Dog.objects.using('dogs_db')
        .filter(dam=dog.dam, sire=dog.sire)
        .exclude(id=dog.id)
    )


def get_offspring(dog) -> list:
    """Потомки собаки (по полу — как sire или как dam)."""
    from ..models import Dog
    if dog.sex == 1:
        return list(Dog.objects.using('dogs_db').filter(sire=dog))
    if dog.sex == 2:
        return list(Dog.objects.using('dogs_db').filter(dam=dog))
    return []


def search_by_name(query: str, limit: int = 20) -> list:
    """Объекты Dog по подстроке имени."""
    from ..models import Dog
    if not query:
        return []
    return list(
        Dog.objects.using('dogs_db')
        .filter(registered_name__icontains=query)[:limit]
    )


def get_overview_counts() -> dict:
    """Сводные счётчики: total, males, females, breeders, with_zooportal_id, with_uuid."""
    from ..models import Dog, Breeder
    dogs = Dog.objects.using('dogs_db')
    return {
        'total': dogs.count(),
        'males': dogs.filter(sex=1).count(),
        'females': dogs.filter(sex=2).count(),
        'breeders': Breeder.objects.using('dogs_db').count(),
        'with_zooportal_id': dogs.filter(zooportal_id__isnull=False).count(),
        'with_uuid': dogs.filter(uuid__isnull=False).count(),
    }


# Алиас: было два варианта с разными именами — оставляем оба имени, один код.
get_overview_stats = get_overview_counts


def search_ids_by_name(query: str, limit: int = 500) -> list:
    """id собак, чьё registered_name содержит query."""
    from ..models import Dog
    if not query:
        return []
    return list(
        Dog.objects.using('dogs_db')
        .filter(registered_name__icontains=query)
        .values_list('id', flat=True)[:limit]
    )


def get_names_map(dog_ids) -> dict:
    """{id: registered_name} для набора id."""
    from ..models import Dog
    if not dog_ids:
        return {}
    return {
        d['id']: d['registered_name']
        for d in Dog.objects.using('dogs_db')
        .filter(id__in=dog_ids)
        .values('id', 'registered_name')
    }


# ЧТЕНИЕ: батч-выборки

def get_offspring_with_parents_values() -> list:
    """Потомки с известными обоими родителями: id, sire_id, dam_id, coi."""
    from ..models import Dog
    return list(
        Dog.objects.using('dogs_db')
        .filter(sire_id__isnull=False, dam_id__isnull=False)
        .values('id', 'sire_id', 'dam_id', 'coi')
    )


def count_offspring_with_parents() -> int:
    from ..models import Dog
    return Dog.objects.using('dogs_db').filter(
        sire_id__isnull=False, dam_id__isnull=False
    ).count()


def get_parents_batch_values(dog_ids) -> list:
    """(id, sire_id, dam_id) для набора id — один SQL на поколение BFS."""
    from ..models import Dog
    if not dog_ids:
        return []
    return list(
        Dog.objects.using('dogs_db')
        .filter(id__in=dog_ids)
        .values('id', 'sire_id', 'dam_id')
    )


def get_coi_for_ancestors(ancestor_ids) -> dict:
    """{id: coi} для предков с непустым COI (для формулы Райта с 1+F_A)."""
    from ..models import Dog
    if not ancestor_ids:
        return {}
    return {
        row['id']: row['coi']
        for row in Dog.objects.using('dogs_db')
        .filter(id__in=ancestor_ids, coi__isnull=False)
        .values('id', 'coi')
    }


def iter_dogs_for_coi_recalc(only_missing: bool = True):
    """QuerySet собак с обоими родителями для массового пересчёта COI."""
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(sire_id__isnull=False, dam_id__isnull=False)
        .only('id', 'registered_name', 'sire_id', 'dam_id', 'coi')
    )
    if only_missing:
        qs = qs.filter(coi__isnull=True)
    return qs


def count_dogs_for_coi_recalc(only_missing: bool = True) -> int:
    return iter_dogs_for_coi_recalc(only_missing).count()


def save_coi(dog, coi_value, updated_at) -> None:
    """Сохраняет coi + coi_updated_on у объекта Dog."""
    dog.coi = coi_value
    dog.coi_updated_on = updated_at
    dog.save(using='dogs_db', update_fields=['coi', 'coi_updated_on'])


def get_by_zoo_hash(zoo_hash: str) -> "Dog | None":
    """Поиск Dog по zoo_hash — используется при merge Zoo↔BA записей."""
    from ..models import Dog
    if not zoo_hash:
        return None
    return Dog.objects.using('dogs_db').filter(zoo_hash=zoo_hash).first()


def get_by_uuid_bulk(uuids) -> dict:
    """
    {uuid: Dog} для набора uuid — один SQL.
    Используется в _save_ancestors для батч-загрузки.
    """
    from ..models import Dog
    if not uuids:
        return {}
    return {
        d.uuid: d
        for d in Dog.objects.using('dogs_db').filter(uuid__in=uuids)
        if d.uuid
    }


def get_by_zooportal_ids_bulk(zoo_ids) -> dict:
    """
    {zooportal_id: Dog} для набора zooportal_id — один SQL.
    Используется в _save_ancestors для батч-загрузки.
    """
    from ..models import Dog
    if not zoo_ids:
        return {}
    return {
        d.zooportal_id: d
        for d in Dog.objects.using('dogs_db').filter(zooportal_id__in=zoo_ids)
        if d.zooportal_id
    }


def get_by_zoo_hashes_bulk(hashes) -> dict:
    """
    {zoo_hash: Dog} для набора zoo_hash — один SQL.
    Используется в _save_ancestors как fallback после zooportal_id lookup.
    """
    from ..models import Dog
    if not hashes:
        return {}
    return {
        d.zoo_hash: d
        for d in Dog.objects.using('dogs_db').filter(zoo_hash__in=hashes)
        if d.zoo_hash
    }


def update_by_pk(pk: int, fields: dict) -> None:
    """Точечное обновление полей Dog по pk."""
    from ..models import Dog
    if fields:
        Dog.objects.using('dogs_db').filter(pk=pk).update(**fields)


def reparent_children(old_pk: int, new_pk: int) -> None:
    """
    Переключает всех потомков с old_pk на new_pk как dam/sire.
    Используется при слиянии Zoo и BA дубликатов.
    """
    from ..models import Dog
    Dog.objects.using('dogs_db').filter(dam_id=old_pk).update(dam_id=new_pk)
    Dog.objects.using('dogs_db').filter(sire_id=old_pk).update(sire_id=new_pk)


def stub_or_get_by_zooportal_id(zoo_id: str, name: str, sex: int) -> "Dog":
    """
    get_or_create стаб-предка по zooportal_id.
    Если не найден — создаёт минимальную запись.
    """
    from ..models import Dog
    dog, _ = Dog.objects.using('dogs_db').get_or_create(
        zooportal_id=zoo_id,
        defaults={
            'registered_name': name,
            'sex': sex,
            'zoo_hash': Dog.compute_zoo_hash(name, sex),
        },
    )
    return dog


def stub_or_get_by_name(name: str, sex: int) -> "Dog":
    """
    get_or_create стаб-предка по имени+полу (когда нет zooportal_id).
    """
    from ..models import Dog
    dog, _ = Dog.objects.using('dogs_db').get_or_create(
        registered_name=name,
        sex=sex,
        defaults={'zoo_hash': Dog.compute_zoo_hash(name, sex)},
    )
    return dog


def get_by_uuid_first(uuid: str) -> "Dog | None":
    """Dog по uuid или None — используется в BA-рекурсии как fallback."""
    from ..models import Dog
    if not uuid:
        return None
    return Dog.objects.using('dogs_db').filter(uuid=uuid).first()


def merge_zoo_hash_dog(zooportal_id: str, zoo_hash: str, update_fields: dict) -> "Dog | None":
    """
    Ищет Dog по zoo_hash (SELECT FOR UPDATE), обновляет его полями Zoo,
    возвращает найденный объект или None если не найден.
    Вся атомарность — внутри; caller просто проверяет результат.

    Список полей которые перезаписываются даже если заняты:
    zooportal_id, zoo_hash, modified_at, brand_chip, kennel,
    photo_url, registration_number, land_of_birth.
    """
    from ..models import Dog
    from django.db import transaction

    OVERWRITE_FIELDS = frozenset({
        'zooportal_id', 'zoo_hash', 'modified_at',
        'brand_chip', 'kennel', 'photo_url',
        'registration_number', 'land_of_birth',
    })

    try:
        with transaction.atomic(using='dogs_db'):
            hash_match = (
                Dog.objects
                .using('dogs_db')
                .select_for_update(nowait=False)
                .filter(zoo_hash=zoo_hash)
                .first()
            )
            if not hash_match:
                return None

            merge = {'zooportal_id': zooportal_id}
            for k, v in update_fields.items():
                if k in ('uuid', 'source') and getattr(hash_match, k, None):
                    continue
                current = getattr(hash_match, k, None)
                if current is not None and k not in OVERWRITE_FIELDS:
                    continue
                merge[k] = v

            Dog.objects.using('dogs_db').filter(pk=hash_match.pk).update(**merge)
            for k, v in merge.items():
                setattr(hash_match, k, v)

            return hash_match
    except Exception:
        return None


def merge_zoo_stub_into_ba(ba_dog_pk: int, zoo_hash: str, ba_dog_fields: dict) -> dict:
    """
    Атомарно находит Zoo-стаб по zoo_hash, переносит его поля на BA-запись,
    переключает FK детей и удаляет стаб.

    Возвращает словарь полей которые были перенесены с Zoo-стаба (для setattr на caller).
    """
    from ..models import Dog
    from django.db import transaction

    if not zoo_hash:
        return {}

    merge_update = {}
    with transaction.atomic(using='dogs_db'):
        zoo_twin = (
            Dog.objects
            .using('dogs_db')
            .select_for_update(nowait=False)
            .filter(zoo_hash=zoo_hash, uuid__isnull=True)
            .exclude(pk=ba_dog_pk)
            .first()
        )
        if not zoo_twin:
            return {}

        # Переносим поля Zoo которых нет в BA
        if zoo_twin.zooportal_id and not ba_dog_fields.get('zooportal_id'):
            merge_update['zooportal_id'] = zoo_twin.zooportal_id
        if zoo_twin.zoo_hash and not ba_dog_fields.get('zoo_hash'):
            merge_update['zoo_hash'] = zoo_twin.zoo_hash

        for field in (
                'brand_chip', 'kennel', 'eyes_color', 'club',
                'size', 'weight', 'sports', 'locked', 'removed',
                'frozen_semen', 'approved_for_breeding',
        ):
            zoo_val = getattr(zoo_twin, field, None)
            if zoo_val is not None and ba_dog_fields.get(field) is None:
                merge_update[field] = zoo_val

        if merge_update:
            Dog.objects.using('dogs_db').filter(pk=ba_dog_pk).update(**merge_update)

        # Переключаем FK потомков
        Dog.objects.using('dogs_db').filter(dam_id=zoo_twin.pk).update(dam_id=ba_dog_pk)
        Dog.objects.using('dogs_db').filter(sire_id=zoo_twin.pk).update(sire_id=ba_dog_pk)

        zoo_twin.delete(using='dogs_db')

    return merge_update


def create_dog(fields: dict) -> "Dog":
    """Создаёт новую запись Dog. Вынесено из integration._save_dog."""
    from ..models import Dog
    return Dog.objects.using('dogs_db').create(**fields)


def get_for_update_by_zoo_hash(zoo_hash: str) -> "Dog | None":
    """
    Атомарный SELECT FOR UPDATE по zoo_hash.
    Вызывается внутри transaction.atomic — для безопасного слияния Zoo/BA дублей.
    """
    from ..models import Dog
    from django.db import transaction
    return (
        Dog.objects
        .using('dogs_db')
        .select_for_update(nowait=False)
        .filter(zoo_hash=zoo_hash)
        .first()
    )


def upsert_ba_dog(uuid: str, defaults: dict) -> tuple:
    """
    update_or_create Dog по uuid (BA-источник).
    Возвращает (dog, created).
    При MultipleObjectsReturned — берёт первый и обновляет.
    """
    from ..models import Dog
    try:
        return Dog.objects.using('dogs_db').update_or_create(
            uuid=uuid, defaults=defaults
        )
    except Dog.MultipleObjectsReturned:
        dog = Dog.objects.using('dogs_db').filter(uuid=uuid).order_by('id').first()
        for k, v in defaults.items():
            setattr(dog, k, v)
        dog.save(using='dogs_db')
        return dog, False


def find_or_create_zoo_dog(zooportal_id: str, fields: dict) -> "Dog":
    """
    Ищет Dog по zooportal_id, затем по zoo_hash, иначе создаёт.
    Возвращает (dog, action) где action: 'found_by_id'|'found_by_hash'|'created'.
    """
    from ..models import Dog

    # 1. По zooportal_id
    existing = Dog.objects.using('dogs_db').filter(
        zooportal_id=zooportal_id
    ).order_by('id').first()
    if existing:
        return existing, 'found_by_id'

    # 2. По zoo_hash (атомарно)
    zoo_hash = fields.get('zoo_hash')
    if zoo_hash:
        try:
            with __import__('django').db.transaction.atomic(using='dogs_db'):
                from django.db import transaction as _tx
                with _tx.atomic(using='dogs_db'):
                    hash_match = (
                        Dog.objects
                        .using('dogs_db')
                        .select_for_update(nowait=False)
                        .filter(zoo_hash=zoo_hash)
                        .first()
                    )
                    if hash_match:
                        return hash_match, 'found_by_hash'
        except Exception:
            pass

    # 3. Создаём
    try:
        dog = Dog.objects.using('dogs_db').create(**fields)
        return dog, 'created'
    except Exception:
        # race condition — кто-то создал параллельно
        fallback = Dog.objects.using('dogs_db').filter(
            zooportal_id=zooportal_id
        ).first()
        if fallback:
            return fallback, 'found_by_id'
        raise


def update_fk_parents(dog_pk: int, dam_pk: int = None, sire_pk: int = None) -> None:
    """Устанавливает dam_id / sire_id для Dog по pk."""
    from ..models import Dog
    update = {}
    if dam_pk is not None:
        update['dam_id'] = dam_pk
    if sire_pk is not None:
        update['sire_id'] = sire_pk
    if update:
        Dog.objects.using('dogs_db').filter(pk=dog_pk).update(**update)


def upsert_zoo_fallback(zooportal_id: str, defaults: dict) -> "Dog":
    """update_or_create Dog из Zoo-fallback (когда BA не нашёл совпадений)."""
    from ..models import Dog
    dog, _ = Dog.objects.using('dogs_db').update_or_create(
        zooportal_id=zooportal_id,
        defaults=defaults,
    )
    return dog


# ── Фото ─────────────────────────────────────────────────────────────────────

def get_photo_fields(dog_id: int, with_zooportal: bool = False):
    """Лёгкая выборка полей фото одной собаки."""
    from ..models import Dog
    fields = ['id', 'photo_url', 'photo_yadisk_path', 'photo_yadisk_url', 'photo_hash']
    if with_zooportal:
        fields.append('zooportal_id')
    try:
        return Dog.objects.using('dogs_db').only(*fields).get(pk=dog_id)
    except Dog.DoesNotExist:
        return None


def update_photo_paths(dog_id: int, updates: dict) -> None:
    """Записывает photo_yadisk_path / photo_yadisk_url."""
    from ..models import Dog
    if updates:
        Dog.objects.using('dogs_db').filter(pk=dog_id).update(**updates)


def get_zoo_dogs_without_yadisk_photo(
        id_from: int = 1, id_to: int = None, limit: int = 100
) -> list:
    """Zoo-собаки с photo_url но без фото на ЯД."""
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(
            photo_url__icontains='zooportal',
            photo_yadisk_url__isnull=True,
            zooportal_id__isnull=False,
            id__gte=id_from,
        )
        .exclude(photo_url='')
        .exclude(zooportal_id='')
        .only('id')
        .order_by('id')
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)
    return list(qs.values('id')[:limit])

def get_dogs_with_yadisk_without_hash(
    limit: int = 1000,
    id_from: int = 1,
    id_to: int = None,
):
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(
            photo_yadisk_path__isnull=False,
            photo_hash__isnull=True,
            id__gte=id_from,
        )
        .exclude(photo_yadisk_path='')
        .only('id', 'photo_url', 'photo_yadisk_path', 'zooportal_id', 'source')
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)
    return list(qs[:limit])

def get_dogs_with_photo_url(
        id_from: int = 1, id_to: int = None,
        limit: int = 500, only_without_yadisk: bool = True,
) -> list:
    """Собаки с photo_url для bulk-синхронизации фото на ЯД."""
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(photo_url__isnull=False, id__gte=id_from)
        .exclude(photo_url='')
        .only('id')
        .order_by('id')
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)
    if only_without_yadisk:
        qs = qs.filter(photo_yadisk_path__isnull=True)
    return list(qs.values('id')[:limit])

def get_dogs_with_url_without_hash(
    limit: int = 1000,
    id_from: int = 1,
    id_to: int = None,
):
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(
            photo_url__isnull=False,
            photo_hash__isnull=True,
            id__gte=id_from,
        )
        .exclude(photo_url='')
        .values('id', 'photo_url', 'source')
    )
    if id_to:
        qs = qs.filter(id__lte=id_to)
    return list(qs[:limit])

def get_yadisk_path(dog_id: int):
    """photo_yadisk_path одной собаки или None."""
    from ..models import Dog
    try:
        return Dog.objects.using('dogs_db').only('id', 'photo_yadisk_path').get(pk=dog_id)
    except Dog.DoesNotExist:
        return None


def get_photo_coverage_counts() -> dict:
    """Счётчики статистики фото: всего / с url / на ЯД."""
    from ..models import Dog
    qs = Dog.objects.using('dogs_db')
    return {
        "total": qs.count(),
        "with_url": qs.exclude(photo_url__isnull=True).exclude(photo_url='').count(),
        "with_yadisk": qs.exclude(photo_yadisk_path__isnull=True).exclude(photo_yadisk_path='').count(),
    }


# ── Поиск по идентификаторам ─────────────────────────────────────────────────

def exists_by_zooportal_id(zooportal_id: str) -> bool:
    """Есть ли в БД собака с таким zooportal_id."""
    from ..models import Dog
    if not zooportal_id:
        return False
    return Dog.objects.using('dogs_db').filter(zooportal_id=zooportal_id).exists()


def get_existing_zooportal_ids(zoo_ids: list) -> set:
    """Из переданных zooportal_id вернуть те, что уже есть в БД."""
    from ..models import Dog
    if not zoo_ids:
        return set()
    return set(
        Dog.objects.using('dogs_db')
        .filter(zooportal_id__in=zoo_ids)
        .values_list('zooportal_id', flat=True)
    )


# OFA
def get_dogs_with_reg_number(
        id_from: int = 1, id_to: int = None, limit: int = 100,
) -> list:
    """Собаки с непустым registration_number — без доменной фильтрации."""
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(registration_number__isnull=False, id__gte=id_from)
        .exclude(registration_number='')
    )
    if id_to is not None:
        qs = qs.filter(id__lte=id_to)
    return list(
        qs.order_by('id')[:limit]
        .values('id', 'registered_name', 'registration_number', 'sex')
    )


def get_dogs_with_name(
        id_from: int = 1, id_to: int = None, limit: int = 100,
) -> list:
    """Собаки с непустым registered_name — без доменной фильтрации."""
    from ..models import Dog
    qs = (
        Dog.objects.using('dogs_db')
        .filter(registered_name__isnull=False, id__gte=id_from)
        .exclude(registered_name='')
    )
    if id_to is not None:
        qs = qs.filter(id__lte=id_to)
    return list(
        qs.order_by('id')[:limit]
        .values('id', 'registered_name', 'registration_number', 'sex')
    )


def search_filtered(
        search: str = None,
        sex: int = None,
        year: int = None,
        year_from: int = None,
        year_to: int = None,
        color: str = None,
        kennel: str = None,
        country: str = None,
):
    from ..models import Dog
    from backend.dogs_module.utils.text import build_color_filter
    qs = (
        Dog.objects.using('dogs_db')
        .order_by('-id')
        .select_related('dam', 'sire')
        .prefetch_related('breeders')
    )
    if search:
        qs = qs.filter(registered_name__icontains=search)
    if sex:
        qs = qs.filter(sex=sex)
    if year:
        qs = qs.filter(year_of_birth=year)
    if year_from:
        qs = qs.filter(year_of_birth__gte=year_from)
    if year_to:
        qs = qs.filter(year_of_birth__lte=year_to)
    if color:
        qs = build_color_filter(qs, color)
    if kennel:
        qs = qs.filter(kennel__icontains=kennel)
    if country:
        qs = qs.filter(land_of_birth__icontains=country)
    return qs


# ЗАПИСЬ

def update_fields_if_empty(dog_id: int, updates: dict) -> bool:
    """Обновляет поля собаки только если они сейчас пустые."""
    from ..models import Dog

    if not updates:
        return False

    try:
        dog = Dog.objects.using('dogs_db').only('id', *updates.keys()).get(pk=dog_id)
    except Dog.DoesNotExist:
        logger.error(f"dog_repository: dog_id={dog_id} не найдена при обновлении")
        return False

    actual_updates = {
        field: value
        for field, value in updates.items()
        if value and not getattr(dog, field, None)
    }

    if not actual_updates:
        return False

    Dog.objects.using('dogs_db').filter(pk=dog_id).update(**actual_updates)
    logger.info(f"dog_repository: dog_id={dog_id} — обновлено {list(actual_updates.keys())}")
    return True


def set_rating(dog_id: int, rating: int) -> None:
    from ..models import Dog
    from django.utils import timezone
    Dog.objects.using('dogs_db').filter(pk=dog_id).update(
        rating=rating,
        rating_updated_at=timezone.now(),
    )
    logger.debug(f"dog_repository: dog_id={dog_id} rating={rating}")


def reset_ratings_except(participant_ids: list) -> None:
    from ..models import Dog
    from django.utils import timezone
    Dog.objects.using('dogs_db').exclude(pk__in=participant_ids).filter(
        rating__gt=0
    ).update(rating=0, rating_updated_at=timezone.now())


# Специфические операции для integration.py

def get_by_uuid(uuid: str) -> "Dog | None":
    """Dog по uuid или None."""
    from ..models import Dog
    if not uuid:
        return None
    return Dog.objects.using('dogs_db').filter(uuid=uuid).first()


def upsert_by_uuid(uuid: str, defaults: dict) -> tuple:
    """update_or_create Dog по uuid. Возвращает (dog, created)."""
    from ..models import Dog
    try:
        return Dog.objects.using('dogs_db').update_or_create(uuid=uuid, defaults=defaults)
    except Dog.MultipleObjectsReturned:
        dog = Dog.objects.using('dogs_db').filter(uuid=uuid).order_by('id').first()
        for k, v in defaults.items():
            setattr(dog, k, v)
        dog.save(using='dogs_db')
        return dog, False


def find_zoo_twin(zoo_hash: str, exclude_pk: int) -> "Dog | None":
    """
    Ищет Zoo-запись (без uuid) с тем же zoo_hash для слияния Zoo→BA.
    Используется внутри transaction.atomic.
    """
    from ..models import Dog
    return (
        Dog.objects
        .using('dogs_db')
        .select_for_update(nowait=False)
        .filter(zoo_hash=zoo_hash, uuid__isnull=True)
        .exclude(pk=exclude_pk)
        .first()
    )


def reassign_children(old_pk: int, new_pk: int) -> None:
    """Перепривязывает детей от старой записи к новой (при слиянии Zoo→BA)."""
    from ..models import Dog
    Dog.objects.using('dogs_db').filter(dam_id=old_pk).update(dam_id=new_pk)
    Dog.objects.using('dogs_db').filter(sire_id=old_pk).update(sire_id=new_pk)


def delete_by_pk(pk: int) -> None:
    """Удаляет Dog по pk (при слиянии — удаляем Zoo-дубль)."""
    from ..models import Dog
    Dog.objects.using('dogs_db').filter(pk=pk).delete()


def create_stub(registered_name: str, sex: int, zooportal_id: str = None, zoo_hash: str = None) -> "Dog":
    """Создаёт минимальную запись Dog-стаб для предка без полных данных."""
    from ..models import Dog
    if zooportal_id:
        dog, _ = Dog.objects.using('dogs_db').get_or_create(
            zooportal_id=zooportal_id,
            defaults={
                'registered_name': registered_name,
                'sex': sex,
                'zoo_hash': zoo_hash or Dog.compute_zoo_hash(registered_name, sex),
            },
        )
    else:
        dog, _ = Dog.objects.using('dogs_db').get_or_create(
            registered_name=registered_name,
            sex=sex,
            defaults={'zoo_hash': zoo_hash or Dog.compute_zoo_hash(registered_name, sex)},
        )
    return dog


def set_zooportal_id(dog_pk: int, zooportal_id: str) -> None:
    """Прописывает zooportal_id если его не было."""
    from ..models import Dog
    Dog.objects.using('dogs_db').filter(pk=dog_pk).update(zooportal_id=zooportal_id)


def set_relationship(child_pk: int, relation: str, parent_pk: int) -> None:
    """Устанавливает sire_id или dam_id для ребёнка."""
    from ..models import Dog
    if relation == 'sire':
        Dog.objects.using('dogs_db').filter(pk=child_pk).update(sire_id=parent_pk)
    elif relation == 'dam':
        Dog.objects.using('dogs_db').filter(pk=child_pk).update(dam_id=parent_pk)


def upsert_by_zooportal_id(zooportal_id: str, defaults: dict) -> tuple:
    """update_or_create Dog по zooportal_id. Возвращает (dog, created)."""
    from ..models import Dog
    return Dog.objects.using('dogs_db').update_or_create(
        zooportal_id=zooportal_id, defaults=defaults
    )


def find_by_zoo_hash_for_update(zoo_hash: str) -> "Dog | None":
    """
    Ищет Dog по zoo_hash с select_for_update (внутри atomic).
    Используется для Zoo hash merge при создании новой Zoo-записи.
    """
    from ..models import Dog
    return (
        Dog.objects
        .using('dogs_db')
        .select_for_update(nowait=False)
        .filter(zoo_hash=zoo_hash)
        .first()
    )


def update_photo_yadisk(dog_pk: int, path: str, url: str = None) -> None:
    """Записывает photo_yadisk_path и опционально photo_yadisk_url."""
    from ..models import Dog
    upd = {'photo_yadisk_path': path}
    if url:
        upd['photo_yadisk_url'] = url
    Dog.objects.using('dogs_db').filter(pk=dog_pk).update(**upd)

def count_dogs_by_photo_hash(min_count: int = 5, top: int = 20) -> list:
    """
    Группировка собак по photo_hash: [{'photo_hash': ..., 'count': N}, ...].
    Частые хэши = кандидаты в дефолтные заглушки сайтов
    (одно серое фото у сотни собак). Хэш с аномальным count
    переносится вручную в config.yadisk.DEFAULT_PHOTO_HASHES.
    """
    from django.db.models import Count
    from ..models import Dog
    return list(
        Dog.objects.using('dogs_db')
        .exclude(photo_hash__isnull=True)
        .values('photo_hash')
        .annotate(count=Count('id'))
        .filter(count__gte=min_count)
        .order_by('-count')[:top]
    )


def get_dogs_by_photo_hash(hashes: list) -> list:
    """
    Собаки с заданными photo_hash (id + путь на ЯД).
    Для очистки уже залитых заглушек: удалить файл с ЯД и обнулить пути.
    """
    from ..models import Dog
    if not hashes:
        return []
    return list(
        Dog.objects.using('dogs_db')
        .filter(photo_hash__in=list(hashes))
        .only('id', 'photo_yadisk_path', 'photo_yadisk_url')
    )


def get_duplicate_candidates(sex: int, year_of_birth: int = None,
                             year_window: int = 1, exclude_pk: int = None,
                             limit: int = 200) -> list:
    """
    Кандидаты на дубль: тот же пол, год рождения в окне ±window.
    Предфильтр (blocking) — режет выборку до десятков, сравнение имён уже в Python.
    """
    from ..models import Dog
    if not sex:
        return []
    qs = Dog.objects.using('dogs_db').filter(sex=sex)
    if year_of_birth:
        qs = qs.filter(
            year_of_birth__gte=year_of_birth - year_window,
            year_of_birth__lte=year_of_birth + year_window,
        )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return list(
        qs.only('id', 'registered_name', 'sex', 'year_of_birth',
                'sire_name', 'dam_name')[:limit]
    )


def get_by_ofa_appnum(appnum: str):
    """Возвращает Dog по точному ofa_appnum или None."""
    if not appnum:
        return None
    from ..models import Dog
    return Dog.objects.using('dogs_db').filter(ofa_appnum=appnum).first()


def get_by_registration_number(reg_num: str):
    """Возвращает первую Dog с таким registration_number (не unique-поле)."""
    if not reg_num:
        return None
    from ..models import Dog
    return (Dog.objects.using('dogs_db')
            .filter(registration_number=reg_num)
            .order_by('id')  # детерминированный выбор первого
            .first())


def upsert_ofa_dog(appnum: str, fields: dict):
    """
    UPSERT по ofa_appnum.
    - Если записи нет — создаёт.
    - Если есть и она stub — апгрейдит до full (заполняет пустые поля).
    - Если есть и full — обновляет только пустые поля (не затирает).
    Возвращает объект Dog.
    """
    from ..models import Dog
    if not appnum:
        raise ValueError("upsert_ofa_dog: appnum обязателен")

    dog = Dog.objects.using('dogs_db').filter(ofa_appnum=appnum).first()

    if dog is None:
        # При создании sex обязателен (NOT NULL), но у стаба его может не быть → 0
        fields.setdefault('sex', 0)
        fields.setdefault('ofa_appnum', appnum)
        dog = Dog.objects.using('dogs_db').create(**fields)
        logger.info(f"OFA: создана Dog appnum={appnum} source={fields.get('source')}")
        return dog

    # Апгрейд: заполняем только пустые поля, не затирая существующие
    update = {}
    for key, val in fields.items():
        if val in (None, "", 0) and key != 'source':
            continue
        if key == 'source':
            # Стаб -> full всегда разрешено; full -> stub запрещено
            if dog.source != 'ofa-full' and val == 'ofa-full':
                update['source'] = 'ofa-full'
            continue
        if not getattr(dog, key, None):
            update[key] = val

    if update:
        Dog.objects.using('dogs_db').filter(pk=dog.pk).update(**update)
        for k, v in update.items():
            setattr(dog, k, v)
        logger.debug(f"OFA: обновлена Dog id={dog.id} appnum={appnum}: {list(update.keys())}")
    return dog


def link_parents(dog_pk: int, sire_pk=None, dam_pk=None) -> None:
    """Проставляет FK sire/dam. Заполняет только если пустые — не перезаписывает."""
    from ..models import Dog
    if not dog_pk or (not sire_pk and not dam_pk):
        return
    dog = Dog.objects.using('dogs_db').filter(pk=dog_pk).only('id', 'sire_id', 'dam_id').first()
    if not dog:
        return
    update = {}
    if sire_pk and not dog.sire_id:
        update['sire_id'] = sire_pk
    if dam_pk and not dog.dam_id:
        update['dam_id'] = dam_pk
    if update:
        Dog.objects.using('dogs_db').filter(pk=dog_pk).update(**update)
