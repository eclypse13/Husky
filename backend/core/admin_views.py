from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import path, include
from django import forms
from django.db.models import Q
from . import models_django as models


class ContentDictionaryForm(forms.Form):
    key = forms.CharField(max_length=200, label='Ключ')
    value = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label='Значение')
    page = forms.CharField(max_length=100, required=False, label='Страница')
    locale = forms.CharField(max_length=10, required=False, label='Локаль')


class UserForm(forms.Form):
    email = forms.EmailField(label='Email')
    first_name = forms.CharField(max_length=100, required=False, label='Имя')
    last_name = forms.CharField(max_length=100, required=False, label='Фамилия')
    is_nkp_member = forms.BooleanField(required=False, label='Член НКП')
    membership_type = forms.ChoiceField(
        choices=[('', '---'), ('physical', 'Физ. лицо'), ('legal', 'Юр. лицо')],
        required=False,
        label='Тип членства'
    )
    phone = forms.CharField(max_length=20, required=False, label='Телефон')
    city = forms.CharField(max_length=100, required=False, label='Город')


class NewsForm(forms.Form):
    title_key = forms.CharField(max_length=200, label='Ключ заголовка')
    slug = forms.SlugField(required=False, label='Slug')
    tags = forms.CharField(required=False, label='Теги (через запятую)')
    is_featured = forms.BooleanField(required=False, label='Избранное')


def get_model_admin_urls(model, form_class, list_display=None, search_fields=None):
    """Генерирует URL patterns для админки модели"""

    model_name = model.__name__

    @staff_member_required
    def list_view(request):
        search = request.GET.get('search', '')
        objects = model.objects.all()

        if search and search_fields:
            query = None
            for field in search_fields:
                if query is None:
                    query = Q(**{f'{field}__icontains': search})
                else:
                    query |= Q(**{f'{field}__icontains': search})
            if query:
                objects = objects.filter(query)

        paginator = Paginator(objects, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'model_name': model_name,
            'objects': page_obj,
            'search': search,
            'list_display': list_display or ['__str__'],
        }
        return render(request, 'admin/model_list.html', context)

    @staff_member_required
    def add_view(request):
        model_name = model.__name__

        if request.method == 'POST':
            form = form_class(request.POST)
            if form.is_valid():
                obj_data = form.cleaned_data.copy()

                if 'tags' in obj_data and obj_data['tags']:
                    obj_data['tags'] = [tag.strip() for tag in obj_data['tags'].split(',')]

                obj = model(**obj_data)
                obj.save()

                messages.success(request, f'{model_name} успешно создан.')
                return redirect(f'nkp_admin:{model_name.lower()}_list')
        else:
            form = form_class()

        context = {
            'model_name': model_name,
            'form': form,
            'action': 'Добавить',
        }
        return render(request, 'admin/model_form.html', context)

    @staff_member_required
    def edit_view(request, id):
        model_name = model.__name__

        try:
            obj = model.objects.get(id=id)
        except model.DoesNotExist:
            messages.error(request, f'{model_name} не найден.')
            return redirect(f'nkp_admin:{model_name.lower()}_list')

        if request.method == 'POST':
            form = form_class(request.POST)
            if form.is_valid():
                for field, value in form.cleaned_data.items():
                    if field == 'tags' and value:
                        value = [tag.strip() for tag in value.split(',')]
                    setattr(obj, field, value)
                obj.save()

                messages.success(request, f'{model_name} успешно обновлен.')
                return redirect(f'nkp_admin:{model_name.lower()}_list')
        else:
            initial_data = {}
            for field in form_class.base_fields:
                if hasattr(obj, field):
                    value = getattr(obj, field)
                    if field == 'tags' and isinstance(value, list):
                        value = ', '.join(value)
                    initial_data[field] = value

            form = form_class(initial=initial_data)

        context = {
            'model_name': model_name,
            'form': form,
            'object': obj,
            'action': 'Редактировать',
        }
        return render(request, 'admin/model_form.html', context)

    @staff_member_required
    def delete_view(request, id):
        model_name = model.__name__

        try:
            obj = model.objects.get(id=id)
        except model.DoesNotExist:
            messages.error(request, f'{model_name} не найден.')
            return redirect(f'nkp_admin:{model_name.lower()}_list')

        if request.method == 'POST':
            obj.delete()
            messages.success(request, f'{model_name} успешно удален.')
            return redirect(f'nkp_admin:{model_name.lower()}_list')

        context = {
            'model_name': model_name,
            'object': obj,
        }
        return render(request, 'admin/model_confirm_delete.html', context)

    return [
        path('', list_view, name=f'{model_name.lower()}_list'),
        path('add/', add_view, name=f'{model_name.lower()}_add'),
        path('<id>/edit/', edit_view, name=f'{model_name.lower()}_edit'),
        path('<id>/delete/', delete_view, name=f'{model_name.lower()}_delete'),
    ]


@staff_member_required
def admin_dashboard(request):
    """Главная страница админки"""

    models_info = [
        {'name': 'ContentDictionary', 'count': models.ContentDictionary.objects.count(),
         'url': 'nkp_admin:contentdictionary_list'},
        {'name': 'User', 'count': models.User.objects.count(), 'url': 'nkp_admin:user_list'},
        {'name': 'News', 'count': models.News.objects.count(), 'url': 'nkp_admin:news_list'},
        {'name': 'Event', 'count': models.Event.objects.count(), 'url': 'nkp_admin:event_list'},
        {'name': 'Dog', 'count': models.Dog.objects.count(), 'url': 'nkp_admin:dog_list'},
        {'name': 'Kennel', 'count': models.Kennel.objects.count(), 'url': 'nkp_admin:kennel_list'},
    ]

    context = {
        'models_info': models_info,
    }
    return render(request, 'admin/dashboard.html', context)


def get_admin_urls():
    """Возвращает все URL patterns для админки"""

    urlpatterns = [
        path('', admin_dashboard, name='admin_dashboard'),
    ]

    models_config = [
        (models.ContentDictionary, ContentDictionaryForm, ['key', 'page', 'locale'], ['key', 'value']),
        (models.User, UserForm, ['email', 'first_name', 'last_name', 'is_nkp_member'], ['email', 'first_name', 'last_name']),
        (models.News, NewsForm, ['title_key', 'slug', 'is_featured'], ['title_key', 'slug', 'tags']),
        (models.Page, forms.Form, ['slug', 'title_key'], ['slug', 'title_key']),
        (models.Event, forms.Form, ['title_key', 'event_type', 'location'], ['title_key', 'location']),
        (models.Dog, forms.Form, ['name', 'registered_name', 'sex'], ['name', 'registered_name']),
        (models.Kennel, forms.Form, ['name', 'prefix'], ['name', 'prefix']),
        (models.Gallery, forms.Form, ['title_key', 'is_highlight'], ['title_key']),
        (models.Judge, forms.Form, ['name', 'rank'], ['name', 'rank']),
        (models.EventReport, forms.Form, [], []),
        (models.BreedStandard, forms.Form, ['title_key', 'fci_number'], ['title_key']),
        (models.BreedArticle, forms.Form, ['title_key', 'category'], ['title_key']),
        (models.ClubDocument, forms.Form, ['title_key', 'document_type'], ['title_key']),
        (models.BoardMember, forms.Form, ['name', 'position'], ['name']),
        (models.Application, forms.Form, ['application_type', 'status'], []),
        (models.Achievement, forms.Form, ['title', 'place'], ['title']),
    ]

    for model, form, list_display, search_fields in models_config:
        model_name = model.__name__.lower()
        urlpatterns.extend([
            path(
                f'{model_name}/',
                include(get_model_admin_urls(
                    model,
                    form,
                    list_display,
                    search_fields
                ))
            )
        ])

    return urlpatterns