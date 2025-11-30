# from django.contrib import admin
# from django import forms
# from django.utils.encoding import force_str as force_text
# from django.contrib.admin.helpers import AdminForm
# from django.utils.translation import gettext_lazy as _
#
#
# class MongoModelForm(forms.ModelForm):
#     """Базовая форма для моделей MongoEngine"""
#
#     class Meta:
#         fields = '__all__'
#
#
# class MongoModelAdmin(admin.ModelAdmin):
#     """Базовый админ класс для MongoEngine моделей"""
#
#     def get_form(self, request, obj=None, **kwargs):
#         """
#         Создаем форму на лету для MongoEngine моделей
#         """
#
#         # Динамически создаем Meta класс
#         class Meta:
#             model = self.model
#             fields = '__all__'
#
#         # Динамически создаем форму класс
#         form_class = type(
#             f'{self.model.__name__}Form',
#             (MongoModelForm,),
#             {'Meta': Meta}
#         )
#
#         return form_class
#
#
# def register_mongo_model(model, admin_class=None):
#     """Регистрирует модель MongoEngine в админке"""
#     if admin_class is None:
#         admin_class = MongoModelAdmin
#
#     # Создаем кастомный admin класс для конкретной модели
#     class DynamicAdmin(admin_class):
#         def __init__(self, model, admin_site):
#             self.model = model
#             super().__init__(model, admin_site)
#
#     admin.site.register(model, DynamicAdmin)