from django.apps import AppConfig


class DogsModuleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dogs_module'

    def ready(self):
        pass
