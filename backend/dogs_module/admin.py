# dogs_module/admin.py
"""Django Admin — панель управления импортом."""

import logging
from django import forms
from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.urls import path

from .models import Dog, ImportTaskProxy
from .tasks.tasks_zooportal import (
    import_zooportal_dog_task,
    import_zooportal_page_task,
    import_zooportal_range_task,
)
from .tasks.tasks_breedarchive import (
    fetch_breedarchive_dog_task,
    fetch_full_pedigree_task,
    sync_breedarchive_recent_task,
    sync_breedarchive_browse_task,
    import_hybrid_full_dog_task,
    import_hybrid_full_page_task,
    import_hybrid_full_range_task,
)
from .tasks.tasks_shows import (
    import_show_list_task,
    import_show_results_task,
    import_show_date_range_task,
    import_results_for_date_range_task,
    import_shows_full_task,
    process_pending_results_task,
    recalculate_ratings_task,
)
from .tasks.tasks_photos import (
    photo_upload_one,
    photo_upload_bulk,
    photo_fetch_zoo_via_playwright,
    photo_fetch_zoo_bulk,
    photo_sync_yadisk_to_db,
    photo_stats,
)
from .tasks.tasks_ofa import (
    fetch_ofa_dog_task,
    fetch_ofa_bulk_by_name_task,
    fetch_ofa_bulk_by_reg_task,
    refresh_ofa_sh_breed_stats,
)
from .tasks.tasks_ml import (
    train_ml_model_task,
    predict_breeding_task,
)
from .tasks.tasks_coi import recalculate_all_coi_task

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ФОРМЫ
# ══════════════════════════════════════════════════════════════════════════════

class ZooportalDogForm(forms.Form):
    zooportal_id = forms.CharField(
        label='Zooportal ID', max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '17516431'}),
    )

class ZooportalPageForm(forms.Form):
    page_num = forms.IntegerField(label='Страница', min_value=1, initial=1)
    max_dogs = forms.IntegerField(label='Макс. собак', min_value=1, max_value=11, initial=11)
    delay    = forms.FloatField(label='Задержка (сек)', min_value=0.5, initial=2.0)

class ZooportalRangeForm(forms.Form):
    start_page              = forms.IntegerField(label='С страницы', min_value=1, initial=1)
    end_page                = forms.IntegerField(label='По страницу', min_value=1, initial=2)
    max_dogs_per_page       = forms.IntegerField(label='Собак / стр', min_value=1, max_value=11, initial=11)
    countdown_between_pages = forms.IntegerField(label='Пауза (сек)', min_value=1, initial=5)

class BreedarchiveDogForm(forms.Form):
    """5 поколений — быстро."""
    uuid         = forms.CharField(label='UUID', max_length=100)
    force_update = forms.BooleanField(label='Принудительно обновить', required=False)

class BreedarchiveFullPedigreeForm(forms.Form):
    """Все поколения до конца — медленно, но полно."""
    uuid         = forms.CharField(
        label='UUID', max_length=100,
        widget=forms.TextInput(attrs={'placeholder': '55dd8870-84fd-...'}),
    )
    force_update = forms.BooleanField(label='Принудительно обновить', required=False)

class BreedarchiveRecentForm(forms.Form):
    pages_count  = forms.IntegerField(label='Страниц', min_value=1, max_value=10, initial=1)
    start_page   = forms.IntegerField(label='С страницы', min_value=0, max_value=9, initial=0)
    is_full_sync = forms.BooleanField(label='Полная синхронизация', required=False)

class BreedarchiveBrowseForm(forms.Form):
    recent_days = forms.IntegerField(label='За последние дней', min_value=1, max_value=30, initial=1)

class HybridFullDogForm(forms.Form):
    """Zoo страница + BA полное дерево всех предков — одна собака."""
    zooportal_id = forms.CharField(
        label='Zooportal ID', max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '17516431'}),
    )
    generations  = forms.IntegerField(
        label='Поколений Zoo (fallback)', min_value=1, max_value=5, initial=5,
    )
    force_update = forms.BooleanField(label='Сбросить BA-кеш', required=False)

class HybridFullPageForm(forms.Form):
    """Zoo страница + BA полное дерево всех предков — целая страница Zoo."""
    page_num    = forms.IntegerField(label='Страница Zoo', min_value=1, initial=1)
    max_dogs    = forms.IntegerField(label='Макс. собак', min_value=1, max_value=11, initial=11)
    delay       = forms.FloatField(label='Задержка (сек)', min_value=0.5, initial=2.0)
    generations = forms.IntegerField(
        label='Поколений Zoo (fallback)', min_value=1, max_value=5, initial=5,
    )

class HybridFullRangeForm(forms.Form):
    """Zoo страница + BA полное дерево всех предков — диапазон страниц Zoo."""
    start_page              = forms.IntegerField(label='С страницы', min_value=1, initial=1)
    end_page                = forms.IntegerField(label='По страницу', min_value=1, initial=2)
    max_dogs_per_page       = forms.IntegerField(label='Собак / стр', min_value=1, max_value=11, initial=11)
    delay                   = forms.FloatField(label='Задержка (сек)', min_value=0.5, initial=2.0)
    generations             = forms.IntegerField(
        label='Поколений Zoo (fallback)', min_value=1, max_value=5, initial=5,
    )
    countdown_between_pages = forms.IntegerField(
        label='Пауза между стр. (сек)', min_value=1, initial=60,
        help_text='Рекомендуется ≥60с — каждая страница может работать часами',
    )


class ShowImportListForm(forms.Form):
    date = forms.CharField(
        max_length=20,
        label='Дата (DD.MM.YYYY)',
        help_text='Например: 01.03.2026',
    )


class ShowImportResultsForm(forms.Form):
    show_id = forms.CharField(
        max_length=50,
        label='ID выставки (zooportal_show_id)',
    )
    import_missing_dogs = forms.BooleanField(
        required=False,
        initial=True,
        label='Импортировать отсутствующих собак',
    )


class ShowImportDateRangeForm(forms.Form):
    date_from = forms.CharField(
        max_length=20,
        label='Дата начала (DD.MM.YYYY)',
        help_text='Например: 01.01.2026',
    )
    date_to = forms.CharField(
        max_length=20,
        label='Дата конца (DD.MM.YYYY)',
        help_text='Например: 31.03.2026',
    )


class ShowImportResultsRangeForm(forms.Form):
    date_from = forms.CharField(
        max_length=20,
        label='Дата начала (DD.MM.YYYY)',
    )
    date_to = forms.CharField(
        max_length=20,
        required=False,
        label='Дата конца (необязательно)',
    )
    only_without_results = forms.BooleanField(
        required=False,
        initial=True,
        label='Только без результатов',
    )
    import_missing_dogs = forms.BooleanField(
        required=False,
        initial=True,
        label='Импортировать отсутствующих собак',
    )


class ShowImportFullForm(forms.Form):
    date_from = forms.CharField(
        max_length=20,
        label='Дата начала (DD.MM.YYYY)',
        help_text='Полный цикл: список → результаты → собаки → рейтинг',
    )
    date_to = forms.CharField(
        max_length=20,
        required=False,
        label='Дата конца (необязательно)',
    )


class ShowRecalculateRatingsForm(forms.Form):
    year = forms.IntegerField(
        required=False,
        label='Год (необязательно)',
        help_text='Пусто = текущий рейтинговый год',
    )


# ── Формы для фото / Яндекс.Диск ─────────────────────────────────────────────

class PhotoStatsForm(forms.Form):
    """
    Показывает сколько собак с photo_url, сколько уже загружено на Яндекс.Диск,
    сколько осталось. Запрос выполняется синхронно — результат виден сразу.
    """
    pass


class PhotoSyncYaDiskToDbForm(forms.Form):
    """
    Сканирует папку disk:/dogs/photos/ на Яндекс.Диске.
    По имени файла (12345.jpg → dog_id=12345) обновляет поле photo_yadisk_path
    в БД для собак у которых оно пустое.
    Используй если загружал фото вручную или пути сбросились после восстановления.
    """
    pass


class PhotoUploadBulkForm(forms.Form):
    """
    Скачивает фото с BreedArchive и загружает на Яндекс.Диск.
    Сравнивает размер файла — не перекачивает если фото не изменилось.
    Первый прогон: оставьте галку «Только без фото». Обновление: снимите её.
    """
    id_from = forms.IntegerField(
        label='Dog ID с', min_value=1, initial=1,
        help_text='Начать с этого ID (для батчевой обработки)',
    )
    id_to = forms.IntegerField(
        label='Dog ID по', required=False,
        help_text='Пусто = до конца базы',
    )
    limit = forms.IntegerField(
        label='Батч (собак)', min_value=1, max_value=2000, initial=500,
        help_text='Сколько собак обработать за один запуск. 500 ≈ 4 мин',
    )
    delay = forms.FloatField(
        label='Задержка (сек)', min_value=0.1, initial=0.5,
        help_text='Пауза между задачами. 0.5с достаточно для BA',
    )
    only_without_yadisk = forms.BooleanField(
        label='Только без фото на ЯД', required=False, initial=True,
        help_text='✓ = только новые (первый прогон). Снять = проверить все и обновить изменившиеся',
    )


class PhotoSingleDogForm(forms.Form):
    """
    Загружает фото одной конкретной собаки на Яндекс.Диск.
    Автоматически выбирает метод: Zoo — через Playwright браузер,
    BreedArchive — прямой HTTP запрос.
    """
    dog_id = forms.IntegerField(
        label='Dog ID',
        widget=forms.NumberInput(attrs={'placeholder': '12345'}),
        help_text='ID собаки из таблицы Dog (PostgreSQL)',
    )


class PhotoZooBulkForm(forms.Form):
    """
    Загружает фото с Zooportal через браузер (Playwright).
    Нужен браузер потому что Zooportal блокирует прямые HTTP запросы к фото.
    Каждая задача открывает страницу собаки и скачивает фото из той же сессии.
    Медленнее BA — используй небольшие батчи и бо́льшую задержку.
    """
    id_from = forms.IntegerField(
        label='Dog ID с', min_value=1, initial=1,
        help_text='Начать с этого ID',
    )
    id_to = forms.IntegerField(
        label='Dog ID по', required=False,
        help_text='Пусто = до конца базы',
    )
    limit = forms.IntegerField(
        label='Батч (собак)', min_value=1, max_value=100, initial=50,
        help_text='Рекомендуется 50–100. Каждая задача запускает отдельный браузер',
    )
    delay = forms.FloatField(
        label='Задержка (сек)', min_value=5.0, initial=10.0,
        help_text='Минимум 5с между задачами — браузер требует памяти',
    )

# ── Формы OFA ─────────────────────────────────────────────


class OFADogForm(forms.Form):
    """
    Поиск и импорт OFA тестов для одной собаки.
    Принимает dog_id из нашей БД — сервис сам возьмёт имя и рег.номер.
    """
    dog_id = forms.IntegerField(
        label='Dog ID',
        widget=forms.NumberInput(attrs={'placeholder': '12345'}),
        help_text='ID собаки из нашей БД. Имя и рег.номер берутся автоматически.',
    )


class OFABulkByNameForm(forms.Form):
    """
    Массовый импорт OFA по кличке — для собак у которых нет рег.номера AKC.
    Парсит сайт OFA по имени, верифицирует по полу и году рождения.
    """
    id_from          = forms.IntegerField(label='Dog ID с', min_value=1, initial=1)
    id_to            = forms.IntegerField(label='Dog ID по', required=False,
                                          help_text='Пусто = до конца базы')
    limit            = forms.IntegerField(label='Батч (собак)', min_value=1, max_value=500, initial=100)
    delay            = forms.FloatField(label='Задержка (сек)', min_value=0.5, initial=1.5,
                                        help_text='Пауза между запросами к OFA. Не ставить < 1с')
    only_without_ofa = forms.BooleanField(label='Только без OFA записей', required=False, initial=True)


class OFABulkByRegForm(forms.Form):
    """
    Массовый импорт OFA по регистрационному номеру AKC.
    Быстрее чем поиск по имени — номер уникален, совпадение гарантировано.
    """
    id_from          = forms.IntegerField(label='Dog ID с', min_value=1, initial=1)
    id_to            = forms.IntegerField(label='Dog ID по', required=False,
                                          help_text='Пусто = до конца базы')
    limit            = forms.IntegerField(label='Батч (собак)', min_value=1, max_value=500, initial=100)
    delay            = forms.FloatField(label='Задержка (сек)', min_value=0.5, initial=1.5)
    only_without_ofa = forms.BooleanField(label='Только без OFA записей', required=False, initial=True)

# ── Формы ML ─────────────────────────────────────────────
class MLTrainForm(forms.Form):
    """
    Обучение ML модели на данных из БД.
    Синтетика помогает при малом количестве реальных данных (< 1000 записей).
    После обучения модели автоматически сохраняются — predict начнёт использовать
    новые версии без перезапуска сервиса.
    """
    augment     = forms.BooleanField(
        label='Добавить синтетические данные', required=False, initial=True,
        help_text='Рекомендуется при < 3000 реальных записей в датасете',
    )
    n_synthetic = forms.IntegerField(
        label='Кол-во синтетических записей', min_value=100, max_value=5000, initial=1000,
        help_text='Оптимум = 1000. Больше не всегда лучше — см. ROC-AUC в логах',
    )


class MLPredictForm(forms.Form):
    """
    Тестовый запрос предсказания для пары собак.
    Используется для проверки что ML сервис работает и модели загружены.
    """
    sire_id = forms.IntegerField(
        label='Кобель (Sire) Dog ID',
        widget=forms.NumberInput(attrs={'placeholder': '12345'}),
    )
    dam_id = forms.IntegerField(
        label='Сука (Dam) Dog ID',
        widget=forms.NumberInput(attrs={'placeholder': '67890'}),
    )

# ── Формы COI ─────────────────────────────────────────────

class COIRecalculateForm(forms.Form):
    """
    Массовый пересчёт COI (коэффициент инбридинга) для всех собак в БД.
    Пересчёт только пустых занимает ~5–30 мин. Полный пересчёт — до 1 часа.
    Стандарт FCI = 5 поколений. Для точности используй 10.
    """
    generations = forms.IntegerField(
        label='Поколений', min_value=1, max_value=10, initial=5,
        help_text='5 = стандарт FCI, 10 = максимальная точность',
    )
    only_missing = forms.BooleanField(
        label='Только пустые (coi IS NULL)', required=False, initial=True,
        help_text='Снять галку = полный пересчёт всех собак',
    )
    use_ancestor_coi = forms.BooleanField(
        label='Учитывать COI предков (1 + F_A)', required=False, initial=False,
        help_text='Даёт +0.1–2% точности при сильном инбридинге. Требует что предки уже посчитаны',
    )

# ══════════════════════════════════════════════════════════════════════════════
# ACTIONS ДЛЯ МОДЕЛИ DOG
# ══════════════════════════════════════════════════════════════════════════════

@admin.action(description="🐾 BA: загрузить полную родословную (все поколения)")
def sync_full_pedigree_action(modeladmin, request, queryset):
    dispatched = skipped = 0
    for idx, dog in enumerate(queryset):
        if not dog.uuid:
            skipped += 1
            continue
        fetch_full_pedigree_task.apply_async(args=[str(dog.uuid)], countdown=idx * 3)
        dispatched += 1
    if dispatched:
        modeladmin.message_user(
            request,
            f"✅ Запущено {dispatched} задач полной синхронизации родословной.",
            messages.SUCCESS,
        )
    if skipped:
        modeladmin.message_user(
            request,
            f"⚠️ Пропущено {skipped} собак без UUID.",
            messages.WARNING,
        )


@admin.action(description="🔀 Hybrid Full: Zoo→BA все поколения (по zooportal_id)")
def sync_hybrid_full_pedigree_action(modeladmin, request, queryset):
    dispatched = skipped = 0
    for idx, dog in enumerate(queryset):
        if not dog.zooportal_id:
            skipped += 1
            continue
        import_hybrid_full_dog_task.apply_async(
            kwargs={'zooportal_id': dog.zooportal_id, 'generations': 5},
            countdown=idx * 10,
        )
        dispatched += 1
    if dispatched:
        modeladmin.message_user(
            request,
            f"✅ Запущено {dispatched} задач гибридного импорта (все поколения).",
            messages.SUCCESS,
        )
    if skipped:
        modeladmin.message_user(
            request,
            f"⚠️ Пропущено {skipped} собак без zooportal_id.",
            messages.WARNING,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN: Панель импорта
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(ImportTaskProxy)
class ImportPanelAdmin(admin.ModelAdmin):

    def get_urls(self):
        return [
            path(
                '',
                self.admin_site.admin_view(self.import_panel_view),
                name='dogs_module_importtaskproxy_changelist',
            ),
        ] + super().get_urls()

    def import_panel_view(self, request):
        task_result = None
        forms_map = self._build_forms()

        if request.method == 'POST':
            action = request.POST.get('action')
            task_result = self._dispatch(request, action)
            if task_result and not task_result.get('error'):
                messages.success(request, task_result.get('message', 'Задача запущена'))
            elif task_result and task_result.get('error'):
                messages.error(request, task_result['error'])
            forms_map = self._build_forms(request.POST, action)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Панель импорта',
            'task_result': task_result,
            'sections': [
                {
                    'label': 'Zooportal — только базовая информация из Breedarchive для корневой собаки',
                    'badge': 'zoo',
                    'cards': [
                        ('zoo_dog',   'Одна собака по ID',  forms_map['zoo_dog']),
                        ('zoo_page',  'Страница поиска',    forms_map['zoo_page']),
                        ('zoo_range', 'Диапазон страниц',   forms_map['zoo_range']),
                    ],
                },
                {
                    'label': 'BreedArchive',
                    'badge': 'ba',
                    'cards': [
                        ('ba_dog',      'По UUID (5 поколений)', forms_map['ba_dog']),
                        ('ba_dog_full', 'По UUID (все предки)',  forms_map['ba_dog_full']),
                        ('ba_recent',   'Последние обновления', forms_map['ba_recent']),
                        ('ba_browse',   'Browse (все предки)',   forms_map['ba_browse']),
                    ],
                },
                {
                    'label': 'Гибрид Zoo→BA (все поколения)',
                    'badge': 'hybrid_full',
                    'cards': [
                        ('hybrid_full_dog',   'Одна собака — все предки',   forms_map['hybrid_full_dog']),
                        ('hybrid_full_page',  'Страница Zoo — все предки',  forms_map['hybrid_full_page']),
                        ('hybrid_full_range', 'Диапазон Zoo — все предки',  forms_map['hybrid_full_range']),
                    ],
                },
                {
                    'label': '📷 Фотографии — Яндекс.Диск',
                    'badge': 'photos',
                    'cards': [
                        (
                            'photo_stats',
                            'Статистика',
                            forms_map['photo_stats'],
                        ),
                        (
                            'photo_bulk',
                            'Загрузить фото на ЯД (BreedArchive)',
                            forms_map['photo_bulk'],
                        ),
                        (
                            'photo_single',
                            'Загрузить фото одной собаки',
                            forms_map['photo_single'],
                        ),
                        (
                            'photo_zoo_bulk',
                            'Загрузить Zoo фото через браузер',
                            forms_map['photo_zoo_bulk'],
                        ),
                        (
                            'photo_yadisk_to_db',
                            'Восстановить пути в БД по файлам на ЯД',
                            forms_map['photo_yadisk_to_db'],
                        ),
                    ],
                },
                {
                    'label': 'Выставки НКП',
                    'badge': 'shows',
                    'cards': [
                        (
                            'show_list',
                            'Сохранить список выставок за дату',
                            forms_map['show_list'],
                        ),
                        (
                            'show_results',
                            'Скачать результаты одной выставки по ID',
                            forms_map['show_results'],
                        ),
                        (
                            'show_date_range',
                            'Сохранить список выставок за период дат',
                            forms_map['show_date_range'],
                        ),
                        (
                            'show_results_range',
                            'Скачать результаты для всех выставок из БД за период (только те у кого нет результатов)',
                            forms_map['show_results_range'],
                        ),
                        (
                            'show_full',
                            'Полный импорт за период: список → результаты → импорт собак → рейтинг (запустить и забыть)',
                            forms_map['show_full'],
                        ),
                        (
                            'show_pending',
                            'Привязать отложенные результаты (для собак которые не были в БД на момент парсинга)',
                            forms_map['show_pending'],
                        ),
                        (
                            'show_recalculate',
                            'Пересчитать рейтинговые баллы всех собак за год',
                            forms_map['show_recalculate'],
                        ),
                    ],
                },
                {
                    'label': 'OFA — медицинские тесты',
                    'badge': 'ofa',
                    'cards': [
                        ('ofa_dog', 'Импорт одной собаки по Dog ID', forms_map['ofa_dog']),
                        ('ofa_bulk_name', 'Массовый импорт по кличке', forms_map['ofa_bulk_name']),
                        ('ofa_bulk_reg', 'Массовый импорт по рег.номеру AKC', forms_map['ofa_bulk_reg']),
                        ('ofa_stats', 'Обновить статистику OFA в кэше', forms_map['ofa_stats']),
                    ],
                },
                {
                    'label': 'ML — прогноз вязки',
                    'badge': 'ml',
                    'cards': [
                        ('ml_train', 'Обучить модели', forms_map['ml_train']),
                        ('ml_predict', 'Тестовый запрос predict', forms_map['ml_predict']),
                        ('coi_recalculate', 'Пересчитать COI', forms_map['coi_recalculate']),
                    ],
                },

            ],
        }
        return TemplateResponse(request, 'admin/dogs_module/import_panel.html', context)

    def _build_forms(self, post_data=None, active_action=None):
        def _post(prefix):
            return post_data if post_data and active_action == prefix else None

        return {
            'zoo_dog': ZooportalDogForm(_post('zoo_dog'), prefix='zoo_dog'),
            'zoo_page': ZooportalPageForm(_post('zoo_page'), prefix='zoo_page'),
            'zoo_range': ZooportalRangeForm(_post('zoo_range'), prefix='zoo_range'),
            'ba_dog': BreedarchiveDogForm(_post('ba_dog'), prefix='ba_dog'),
            'ba_dog_full': BreedarchiveFullPedigreeForm(_post('ba_dog_full'), prefix='ba_dog_full'),
            'ba_recent': BreedarchiveRecentForm(_post('ba_recent'), prefix='ba_recent'),
            'ba_browse': BreedarchiveBrowseForm(_post('ba_browse'), prefix='ba_browse'),
            'hybrid_full_dog': HybridFullDogForm(_post('hybrid_full_dog'), prefix='hybrid_full_dog'),
            'hybrid_full_page': HybridFullPageForm(_post('hybrid_full_page'), prefix='hybrid_full_page'),
            'hybrid_full_range': HybridFullRangeForm(_post('hybrid_full_range'), prefix='hybrid_full_range'),
            'show_list': ShowImportListForm(_post('show_list'), prefix='show_list'),
            'show_results': ShowImportResultsForm(_post('show_results'), prefix='show_results'),
            'show_date_range': ShowImportDateRangeForm(_post('show_date_range'), prefix='show_date_range'),
            'show_results_range': ShowImportResultsRangeForm(_post('show_results_range'), prefix='show_results_range'),
            'show_full': ShowImportFullForm(_post('show_full'), prefix='show_full'),
            'show_pending': forms.Form(_post('show_pending'), prefix='show_pending'),
            'show_recalculate': ShowRecalculateRatingsForm(_post('show_recalculate'), prefix='show_recalculate'),
            'photo_stats':        PhotoStatsForm(_post('photo_stats'),            prefix='photo_stats'),
            'photo_bulk':         PhotoUploadBulkForm(_post('photo_bulk'),        prefix='photo_bulk'),
            'photo_single':       PhotoSingleDogForm(_post('photo_single'),       prefix='photo_single'),
            'photo_zoo_bulk':     PhotoZooBulkForm(_post('photo_zoo_bulk'),       prefix='photo_zoo_bulk'),
            'photo_yadisk_to_db': PhotoSyncYaDiskToDbForm(_post('photo_yadisk_to_db'), prefix='photo_yadisk_to_db'),
            'ofa_dog': OFADogForm(_post('ofa_dog'), prefix='ofa_dog'),
            'ofa_bulk_name': OFABulkByNameForm(_post('ofa_bulk_name'), prefix='ofa_bulk_name'),
            'ofa_bulk_reg': OFABulkByRegForm(_post('ofa_bulk_reg'), prefix='ofa_bulk_reg'),
            'ofa_stats': forms.Form(_post('ofa_stats'), prefix='ofa_stats'),
            'ml_train': MLTrainForm(_post('ml_train'), prefix='ml_train'),
            'ml_predict': MLPredictForm(_post('ml_predict'), prefix='ml_predict'),
            'coi_recalculate': COIRecalculateForm(_post('coi_recalculate'), prefix='coi_recalculate'),
        }

    def _dispatch(self, request, action: str) -> dict:
        handlers = {
            'zoo_dog':           self._zoo_dog,
            'zoo_page':          self._zoo_page,
            'zoo_range':         self._zoo_range,
            'ba_dog':            self._ba_dog,
            'ba_dog_full':       self._ba_dog_full,
            'ba_recent':         self._ba_recent,
            'ba_browse':         self._ba_browse,
            'hybrid_full_dog':   self._hybrid_full_dog,
            'hybrid_full_page':  self._hybrid_full_page,
            'hybrid_full_range': self._hybrid_full_range,
            'show_list':         self._show_list,
            'show_results':      self._show_results,
            'show_date_range':   self._show_date_range,
            'show_results_range': self._show_results_range,
            'show_full':         self._show_full,
            'show_pending':      self._show_pending,
            'show_recalculate':  self._show_recalculate,
            'photo_stats':        self._photo_stats,
            'photo_bulk':         self._photo_bulk,
            'photo_single':       self._photo_single,
            'photo_zoo_bulk':     self._photo_zoo_bulk,
            'photo_yadisk_to_db': self._photo_yadisk_to_db,
            'ofa_dog': self._ofa_dog,
            'ofa_bulk_name': self._ofa_bulk_name,
            'ofa_bulk_reg': self._ofa_bulk_reg,
            'ofa_stats': self._ofa_stats,
            'ml_train': self._ml_train,
            'ml_predict': self._ml_predict,
            'coi_recalculate': self._coi_recalculate,
        }
        handler = handlers.get(action)
        if not handler:
            return {'error': f'Неизвестное действие: {action}'}
        try:
            return handler(request)
        except Exception as e:
            logger.error(f"Admin dispatch ({action}): {e}")
            return {'error': str(e)}

    def _zoo_dog(self, request):
        form = ZooportalDogForm(request.POST, prefix='zoo_dog')
        if not form.is_valid():
            return {'error': str(form.errors)}
        zoo_id = form.cleaned_data['zooportal_id']
        task = import_zooportal_dog_task.apply_async(args=[zoo_id], countdown=1)
        return {'task_id': task.id, 'message': f"Импорт собаки {zoo_id} запущен"}

    def _zoo_page(self, request):
        form = ZooportalPageForm(request.POST, prefix='zoo_page')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_zooportal_page_task.apply_async(
            kwargs={'page_num': d['page_num'], 'max_dogs': d['max_dogs'], 'delay': d['delay']},
            countdown=1,
        )
        return {'task_id': task.id, 'message': f"Импорт страницы {d['page_num']} запущен"}

    def _zoo_range(self, request):
        form = ZooportalRangeForm(request.POST, prefix='zoo_range')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_zooportal_range_task.apply_async(kwargs=d, countdown=1)
        return {'task_id': task.id, 'message': f"Импорт страниц {d['start_page']}–{d['end_page']} запущен"}

    def _ba_dog(self, request):
        form = BreedarchiveDogForm(request.POST, prefix='ba_dog')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = fetch_breedarchive_dog_task.apply_async(args=[d['uuid'], d['force_update']])
        return {'task_id': task.id, 'message': f"Импорт BA (5 поколений) uuid={d['uuid']} запущен"}

    def _ba_dog_full(self, request):
        form = BreedarchiveFullPedigreeForm(request.POST, prefix='ba_dog_full')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = fetch_full_pedigree_task.apply_async(args=[d['uuid'], d['force_update']])
        return {'task_id': task.id, 'message': f"Загрузка полной родословной uuid={d['uuid']} запущена"}

    def _ba_recent(self, request):
        form = BreedarchiveRecentForm(request.POST, prefix='ba_recent')
        if not form.is_valid():
            return {'error': str(form.errors)}
        task = sync_breedarchive_recent_task.apply_async(kwargs=form.cleaned_data)
        return {'task_id': task.id, 'message': 'Синхронизация BA recent запущена'}

    def _ba_browse(self, request):
        form = BreedarchiveBrowseForm(request.POST, prefix='ba_browse')
        if not form.is_valid():
            return {'error': str(form.errors)}
        task = sync_breedarchive_browse_task.apply_async(
            args=[form.cleaned_data['recent_days']]
        )
        return {'task_id': task.id, 'message': 'Парсинг BA browse (все предки) запущен'}

    def _hybrid_full_dog(self, request):
        form = HybridFullDogForm(request.POST, prefix='hybrid_full_dog')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_hybrid_full_dog_task.apply_async(
            kwargs={
                'zooportal_id': d['zooportal_id'],
                'generations':  d['generations'],
                'force_update': d['force_update'],
            },
            countdown=1,
        )
        return {'task_id': task.id, 'message': f"Hybrid Full (все поколения) для {d['zooportal_id']} запущен"}

    def _hybrid_full_page(self, request):
        form = HybridFullPageForm(request.POST, prefix='hybrid_full_page')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_hybrid_full_page_task.apply_async(kwargs=d, countdown=1)
        return {'task_id': task.id, 'message': f"Hybrid Full страница {d['page_num']} (все поколения) запущена"}

    def _hybrid_full_range(self, request):
        form = HybridFullRangeForm(request.POST, prefix='hybrid_full_range')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_hybrid_full_range_task.apply_async(kwargs=d, countdown=1)
        return {
            'task_id': task.id,
            'message': f"Hybrid Full диапазон {d['start_page']}–{d['end_page']} (все поколения) запущен",
        }

    # ── Фото / Яндекс.Диск ───────────────────────────────────────────────────────

    def _photo_stats(self, request):
        """Статистика: сколько в БД, на ЯД, осталось."""
        result = photo_stats.apply_async()
        data = result.get(timeout=30)
        yd = data.get('yadisk', {})
        return {
            'message': (
                f"Всего собак: {data.get('total_dogs')} | "
                f"С photo_url: {data.get('dogs_with_photo_url')} | "
                f"На ЯД: {data.get('dogs_on_yadisk')} | "
                f"Осталось: {data.get('missing')} | "
                f"Файлов на disk:/dogs/photos/: {yd.get('files_on_disk', '?')}"
            )
        }

    def _photo_bulk(self, request):
        """Bulk загрузка BA/других фото на ЯД (HTTP, без Playwright)."""
        form = PhotoUploadBulkForm(request.POST, prefix='photo_bulk')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = photo_upload_bulk.apply_async(kwargs={
            'id_from':             d['id_from'],
            'id_to':               d.get('id_to'),
            'limit':               d['limit'],
            'delay':               d['delay'],
            'only_without_yadisk': d['only_without_yadisk'],
        }, countdown=1)
        return {
            'task_id': task.id,
            'message': f"Bulk загрузка до {d['limit']} фото на ЯД запущена (id {d['id_from']}–{d.get('id_to') or '∞'})",
        }

    def _photo_single(self, request):
        """Загрузка фото одной собаки — автоматически выбирает HTTP или Playwright."""
        form = PhotoSingleDogForm(request.POST, prefix='photo_single')
        if not form.is_valid():
            return {'error': str(form.errors)}
        dog_id = form.cleaned_data['dog_id']
        # photo_upload_one сам определит Zoo → Playwright или HTTP
        task = photo_upload_one.apply_async(kwargs={'dog_id': dog_id}, countdown=1)
        return {'task_id': task.id, 'message': f"Загрузка фото dog_id={dog_id} запущена"}

    def _photo_zoo_bulk(self, request):
        """Bulk загрузка Zoo фото через Playwright (медленно, надёжно)."""
        form = PhotoZooBulkForm(request.POST, prefix='photo_zoo_bulk')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = photo_fetch_zoo_bulk.apply_async(kwargs={
            'id_from': d['id_from'],
            'id_to':   d.get('id_to'),
            'limit':   d['limit'],
            'delay':   d['delay'],
        }, countdown=1)
        return {
            'task_id': task.id,
            'message': f"Zoo Playwright bulk: {d['limit']} собак запущено (пауза {d['delay']}с)",
        }

    def _photo_yadisk_to_db(self, request):
        """Сканирует ЯД и обновляет photo_yadisk_path в БД."""
        task = photo_sync_yadisk_to_db.apply_async(countdown=1)
        return {
            'task_id': task.id,
            'message': 'Синхронизация ЯД → БД запущена (сканируем disk:/dogs/photos/)',
        }

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _show_list(self, request):
        """Парсинг списка выставок за дату → сохранить ShowEvent."""
        form = ShowImportListForm(request.POST, prefix='show_list')
        if not form.is_valid():
            return {'error': str(form.errors)}
        date_str = form.cleaned_data['date']
        task = import_show_list_task.apply_async(args=[date_str], countdown=1)
        return {'task_id': task.id, 'message': f'Парсинг выставок за {date_str} запущен'}

    def _show_results(self, request):
        """Парсинг результатов одной выставки."""
        form = ShowImportResultsForm(request.POST, prefix='show_results')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_show_results_task.apply_async(
            args=[d['show_id']],
            kwargs={'import_missing_dogs': d['import_missing_dogs']},
            countdown=1,
        )
        return {'task_id': task.id, 'message': f'Парсинг результатов выставки {d["show_id"]} запущен'}

    def _show_date_range(self, request):
        """Парсинг списков выставок за диапазон дат."""
        form = ShowImportDateRangeForm(request.POST, prefix='show_date_range')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_show_date_range_task.apply_async(
            kwargs={'date_from': d['date_from'], 'date_to': d['date_to']},
            countdown=1,
        )
        return {
            'task_id': task.id,
            'message': f'Парсинг выставок {d["date_from"]} – {d["date_to"]} запущен',
        }

    def _show_results_range(self, request):
        """Парсинг результатов для выставок из БД за период."""
        form = ShowImportResultsRangeForm(request.POST, prefix='show_results_range')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_results_for_date_range_task.apply_async(
            kwargs={
                'date_from': d['date_from'],
                'date_to': d.get('date_to') or d['date_from'],
                'only_without_results': d['only_without_results'],
                'import_missing_dogs': d['import_missing_dogs'],
            },
            countdown=1,
        )
        return {
            'task_id': task.id,
            'message': f'Импорт результатов за {d["date_from"]} запущен',
        }

    def _show_full(self, request):
        """Полный импорт: список → результаты → собаки → рейтинг."""
        form = ShowImportFullForm(request.POST, prefix='show_full')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_shows_full_task.apply_async(
            kwargs={
                'date_from': d['date_from'],
                'date_to': d.get('date_to') or d['date_from'],
            },
            countdown=1,
        )
        return {
            'task_id': task.id,
            'message': f'Полный импорт выставок за {d["date_from"]} запущен. Задача может выполняться несколько часов.',
        }

    def _show_pending(self, request):
        """Обработать ожидающие результаты (собаки которые ещё не были в БД)."""
        task = process_pending_results_task.apply_async(args=[None], countdown=1)
        return {'task_id': task.id, 'message': 'Обработка ожидающих результатов запущена'}

    def _show_recalculate(self, request):
        """Пересчитать рейтинг для всех собак."""
        form = ShowRecalculateRatingsForm(request.POST, prefix='show_recalculate')
        if not form.is_valid():
            return {'error': str(form.errors)}
        year = form.cleaned_data.get('year')
        task = recalculate_ratings_task.apply_async(
            kwargs={'year': year},
            countdown=1,
        )
        year_label = str(year) if year else 'текущий'
        return {'task_id': task.id, 'message': f'Пересчёт рейтинга за {year_label} год запущен'}

    def _ofa_dog(self, request):
        """Импорт OFA тестов для одной собаки."""
        form = OFADogForm(request.POST, prefix='ofa_dog')
        if not form.is_valid():
            return {'error': str(form.errors)}
        dog_id = form.cleaned_data['dog_id']
        task = fetch_ofa_dog_task.apply_async(kwargs={'dog_id': dog_id}, countdown=1)
        return {'task_id': task.id, 'message': f'Импорт OFA для dog_id={dog_id} запущен'}

    def _ofa_bulk_name(self, request):
        """Массовый импорт OFA по кличке."""
        form = OFABulkByNameForm(request.POST, prefix='ofa_bulk_name')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = fetch_ofa_bulk_by_name_task.apply_async(kwargs=d, countdown=1)
        return {
            'task_id': task.id,
            'message': f'Bulk OFA по кличке: {d["limit"]} собак запущено (id {d["id_from"]}–{d.get("id_to") or "∞"})',
        }

    def _ofa_bulk_reg(self, request):
        """Массовый импорт OFA по рег.номеру AKC."""
        form = OFABulkByRegForm(request.POST, prefix='ofa_bulk_reg')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = fetch_ofa_bulk_by_reg_task.apply_async(kwargs=d, countdown=1)
        return {
            'task_id': task.id,
            'message': f'Bulk OFA по рег.номеру: {d["limit"]} собак запущено',
        }

    def _ofa_stats(self, request):
        """Сбросить кэш и обновить статистику OFA."""
        task = refresh_ofa_sh_breed_stats.apply_async(countdown=1)
        return {'task_id': task.id, 'message': 'Обновление статистики OFA запущено (кэш сброшен)'}

    def _ml_train(self, request):
        """Запустить обучение ML моделей."""
        form = MLTrainForm(request.POST, prefix='ml_train')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = train_ml_model_task.apply_async(
            kwargs={'augment': d['augment'], 'n_synthetic': d['n_synthetic']},
            countdown=1,
        )
        return {
            'task_id': task.id,
            'message': f'Обучение ML запущено (augment={d["augment"]}, synthetic={d["n_synthetic"]}). '
                       f'Проверь логи ML сервиса для ROC-AUC результатов.',
        }

    def _ml_predict(self, request):
        """Тестовый predict для пары собак."""
        form = MLPredictForm(request.POST, prefix='ml_predict')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = predict_breeding_task.apply_async(
            kwargs={'sire_id': d['sire_id'], 'dam_id': d['dam_id']},
            countdown=1,
        )
        return {
            'task_id': task.id,
            'message': f'Predict для пары sire={d["sire_id"]} × dam={d["dam_id"]} запущен. '
                       f'Результат смотри в Celery логах или через Swagger.',
        }

    def _coi_recalculate(self, request):
        """Массовый пересчёт COI."""
        form = COIRecalculateForm(request.POST, prefix='coi_recalculate')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = recalculate_all_coi_task.apply_async(
            kwargs={
                'generations': d['generations'],
                'only_missing': d['only_missing'],
                'use_ancestor_coi': d['use_ancestor_coi'],
            },
            countdown=1,
        )
        label = 'только пустых' if d['only_missing'] else 'всех собак'
        return {
            'task_id': task.id,
            'message': f'Пересчёт COI {label}, {d["generations"]} поколений запущен. '
                       f'Прогресс виден через GET /api/dogs/import/status/{{task_id}}/',
        }


# ══════════════════════════════════════════════════════════════════════════════
# РЕГИСТРАЦИЯ Dog с actions
# ══════════════════════════════════════════════════════════════════════════════

@admin.action(description="📷 ЯД: загрузить фото выбранных собак")
def upload_photos_to_yadisk_action(modeladmin, request, queryset):
    dispatched = no_url = 0
    for dog in queryset:
        if not dog.photo_url:
            no_url += 1
            continue
        if "zooportal" in (dog.photo_url or "") and dog.zooportal_id:
            photo_fetch_zoo_via_playwright.apply_async(
                kwargs={"dog_id": dog.id}, countdown=dispatched * 5
            )
        else:
            photo_upload_one.apply_async(
                kwargs={"dog_id": dog.id}, countdown=dispatched
            )
        dispatched += 1
    if dispatched:
        modeladmin.message_user(request, f"📷 Запущена загрузка {dispatched} фото на ЯД", messages.SUCCESS)
    if no_url:
        modeladmin.message_user(request, f"⚠️ У {no_url} собак нет photo_url", messages.WARNING)


@admin.register(Dog)
class DogAdmin(admin.ModelAdmin):
    list_display    = ('registered_name', 'uuid', 'sex', 'year_of_birth', 'source')
    search_fields   = ('registered_name', 'uuid', 'call_name')
    list_filter     = ('sex', 'source', 'year_of_birth')
    actions         = [sync_full_pedigree_action, sync_hybrid_full_pedigree_action, upload_photos_to_yadisk_action]
    readonly_fields = (
        'uuid', 'zooportal_id', 'zoo_hash', 'source',
        'dam', 'sire', 'coi', 'incomplete_pedigree',
    )
