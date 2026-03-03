from django.contrib import admin

# dogs_module/admin.py
"""Django Admin — панель управления импортом."""

import logging
from django import forms
from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.urls import path

from .models import ImportTaskProxy
from .tasks.tasks_zooportal import (
    import_zooportal_dog_task,
    import_zooportal_page_task,
    import_zooportal_range_task,
    import_hybrid_page_task,
    import_hybrid_range_task, import_hybrid_dog_task,
)
from .tasks.tasks_breedarchive import (
    fetch_breedarchive_dog_task,
    sync_breedarchive_recent_task,
    sync_breedarchive_browse_task,
)

logger = logging.getLogger(__name__)


# ── Формы ─────────────────────────────────────────────────────────────────────

class ZooportalDogForm(forms.Form):
    zooportal_id = forms.CharField(label='Zooportal ID', max_length=20,
                                   widget=forms.TextInput(attrs={'placeholder': '17516431'}))

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
    uuid         = forms.CharField(label='UUID', max_length=100)
    force_update = forms.BooleanField(label='Принудительно обновить', required=False)

class BreedarchiveRecentForm(forms.Form):
    pages_count  = forms.IntegerField(label='Страниц', min_value=1, max_value=10, initial=1)
    start_page   = forms.IntegerField(label='С страницы', min_value=0, max_value=9, initial=0)
    is_full_sync = forms.BooleanField(label='Полная синхронизация', required=False)

class BreedarchiveBrowseForm(forms.Form):
    recent_days = forms.IntegerField(label='За последние дней', min_value=1, max_value=30, initial=1)

class HybridPageForm(forms.Form):
    page_num    = forms.IntegerField(label='Страница', min_value=1, initial=1)
    max_dogs    = forms.IntegerField(label='Макс. собак', min_value=1, max_value=11, initial=11)
    delay       = forms.FloatField(label='Задержка (сек)', min_value=0.5, initial=2.0)
    generations = forms.IntegerField(label='Поколений', min_value=1, max_value=5, initial=5)

class HybridRangeForm(forms.Form):
    start_page              = forms.IntegerField(label='С страницы', min_value=1, initial=1)
    end_page                = forms.IntegerField(label='По страницу', min_value=1, initial=2)
    max_dogs_per_page       = forms.IntegerField(label='Собак / стр', min_value=1, max_value=11, initial=11)
    delay                   = forms.FloatField(label='Задержка (сек)', min_value=0.5, initial=2.0)
    generations             = forms.IntegerField(label='Поколений', min_value=1, max_value=5, initial=5)
    countdown_between_pages = forms.IntegerField(label='Пауза (сек)', min_value=1, initial=5)


# ── Admin ─────────────────────────────────────────────────────────────────────

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
            # Пересобираем формы с данными POST для отображения ошибок
            forms_map = self._build_forms(request.POST, action)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Панель импорта',
            'task_result': task_result,
            'sections': [
                {
                    'label':  'Zooportal (доп. инфа из Breedarchive)',
                    'badge':  'zoo',
                    'cards':  [
                        ('zoo_dog',   'Одна собака по ID',    forms_map['zoo_dog']),
                        ('zoo_page',  'Страница поиска',      forms_map['zoo_page']),
                        ('zoo_range', 'Диапазон страниц',     forms_map['zoo_range']),
                    ],
                },
                {
                    'label':  'BreedArchive',
                    'badge':  'ba',
                    'cards':  [
                        ('ba_dog',    'Одна собака по UUID',  forms_map['ba_dog']),
                        ('ba_recent', 'Последние обновления', forms_map['ba_recent']),
                        ('ba_browse', 'Browse (Playwright)',  forms_map['ba_browse']),
                    ],
                },
                {
                    'label':  'Гибрид Zoo→BA (ищется по Zooportal, доп. инфа из Zooportal)',
                    'badge':  'hybrid',
                    'cards':  [
                        ('hybrid_page',  'Страница (полные предки из BA)',   forms_map['hybrid_page']),
                        ('hybrid_range', 'Диапазон (полные предки из BA)',   forms_map['hybrid_range']),
                        ('hybrid_dog', 'Одна собака по ID (Zoo→BA)', forms_map['hybrid_dog']),
                    ],
                },
            ],
        }
        return TemplateResponse(request, 'admin/dogs_module/import_panel.html', context)

    def _build_forms(self, post_data=None, active_action=None):
        """Строит словарь форм, передавая POST-данные только активной форме."""
        def _post(prefix):
            return post_data if post_data and active_action == prefix else None

        return {
            'zoo_dog':      ZooportalDogForm(     _post('zoo_dog'),      prefix='zoo_dog'),
            'zoo_page':     ZooportalPageForm(    _post('zoo_page'),     prefix='zoo_page'),
            'zoo_range':    ZooportalRangeForm(   _post('zoo_range'),    prefix='zoo_range'),
            'ba_dog':       BreedarchiveDogForm(  _post('ba_dog'),       prefix='ba_dog'),
            'ba_recent':    BreedarchiveRecentForm(_post('ba_recent'),   prefix='ba_recent'),
            'ba_browse':    BreedarchiveBrowseForm(_post('ba_browse'),   prefix='ba_browse'),
            'hybrid_page':  HybridPageForm(       _post('hybrid_page'),  prefix='hybrid_page'),
            'hybrid_range': HybridRangeForm(      _post('hybrid_range'), prefix='hybrid_range'),
            'hybrid_dog': HybridDogForm(_post('hybrid_dog'), prefix='hybrid_dog'),
        }

    def _dispatch(self, request, action: str) -> dict:
        handlers = {
            'zoo_dog':      self._zoo_dog,
            'zoo_page':     self._zoo_page,
            'zoo_range':    self._zoo_range,
            'ba_dog':       self._ba_dog,
            'ba_recent':    self._ba_recent,
            'ba_browse':    self._ba_browse,
            'hybrid_page':  self._hybrid_page,
            'hybrid_range': self._hybrid_range,
            'hybrid_dog': self._hybrid_dog,
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
        return {'task_id': task.id, 'message': f"Импорт BA uuid={d['uuid']} запущен"}

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
        task = sync_breedarchive_browse_task.apply_async(args=[form.cleaned_data['recent_days']])
        return {'task_id': task.id, 'message': 'Парсинг BA browse запущен'}

    def _hybrid_page(self, request):
        form = HybridPageForm(request.POST, prefix='hybrid_page')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_hybrid_page_task.apply_async(kwargs=d, countdown=1)
        return {'task_id': task.id, 'message': f"Гибридный импорт страницы {d['page_num']} запущен"}

    def _hybrid_range(self, request):
        form = HybridRangeForm(request.POST, prefix='hybrid_range')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_hybrid_range_task.apply_async(kwargs=d, countdown=1)
        return {'task_id': task.id, 'message': f"Гибридный импорт страниц {d['start_page']}–{d['end_page']} запущен"}

    def _hybrid_dog(self, request):
        form = HybridDogForm(request.POST, prefix='hybrid_dog')
        if not form.is_valid():
            return {'error': str(form.errors)}
        d = form.cleaned_data
        task = import_hybrid_dog_task.apply_async(
            kwargs={'zooportal_id': d['zooportal_id'], 'generations': d['generations']},
            countdown=1,
        )
        return {'task_id': task.id, 'message': f"Гибридный импорт собаки {d['zooportal_id']} запущен"}

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

class HybridDogForm(forms.Form):
    zooportal_id = forms.CharField(
        label='Zooportal ID', max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '17516431'}),
    )
    generations = forms.IntegerField(label='Поколений BA', min_value=1, max_value=5, initial=5)