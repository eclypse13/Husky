from django.contrib import admin

# MongoEngine модели не регистрируются в Django Admin стандартным способом
# Для полноценной работы нужен django-mongoengine-admin или кастомная реализация

# Примечание: Django User уже зарегистрирован по умолчанию
# Не нужно его регистрировать повторно
