class DogsRouter:
    """
    dogs_module -> dogs_db
    всё остальное -> default
    """

    route_app_labels = {'dogs_module'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'dogs_db'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'dogs_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db and obj2._state.db:
            if obj1._state.db == obj2._state.db:
                return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'dogs_db'
        return db == 'default'