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
            ],
        }
        return TemplateResponse(request, 'admin/dogs_module/import_panel.html', context)

    def _build_forms(self, post_data=None, active_action=None):
        def _post(prefix):
            return post_data if post_data and active_action == prefix else None

        return {
            'zoo_dog':           ZooportalDogForm(            _post('zoo_dog'),           prefix='zoo_dog'),
            'zoo_page':          ZooportalPageForm(           _post('zoo_page'),          prefix='zoo_page'),
            'zoo_range':         ZooportalRangeForm(          _post('zoo_range'),         prefix='zoo_range'),
            'ba_dog':            BreedarchiveDogForm(         _post('ba_dog'),            prefix='ba_dog'),
            'ba_dog_full':       BreedarchiveFullPedigreeForm(_post('ba_dog_full'),       prefix='ba_dog_full'),
            'ba_recent':         BreedarchiveRecentForm(      _post('ba_recent'),         prefix='ba_recent'),
            'ba_browse':         BreedarchiveBrowseForm(      _post('ba_browse'),         prefix='ba_browse'),
            'hybrid_full_dog':   HybridFullDogForm(          _post('hybrid_full_dog'),   prefix='hybrid_full_dog'),
            'hybrid_full_page':  HybridFullPageForm(         _post('hybrid_full_page'),  prefix='hybrid_full_page'),
            'hybrid_full_range': HybridFullRangeForm(        _post('hybrid_full_range'), prefix='hybrid_full_range'),
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

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ══════════════════════════════════════════════════════════════════════════════
# РЕГИСТРАЦИЯ Dog с actions
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Dog)
class DogAdmin(admin.ModelAdmin):
    list_display    = ('registered_name', 'uuid', 'sex', 'year_of_birth', 'source')
    search_fields   = ('registered_name', 'uuid', 'call_name')
    list_filter     = ('sex', 'source', 'year_of_birth')
    actions         = [sync_full_pedigree_action, sync_hybrid_full_pedigree_action]
    readonly_fields = (
        'uuid', 'zooportal_id', 'zoo_hash', 'source',
        'dam', 'sire', 'coi', 'incomplete_pedigree',
    )
