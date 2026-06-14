
class DogsRouter:
    """
    Всё что принадлежит приложению dogs
    → направляется в dogs_db (PostgreSQL)

    Всё остальное (core, auth, admin)
    → идёт в default БД (SQLite)
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
        if (obj1._meta.app_label in self.route_app_labels or
                obj2._meta.app_label in self.route_app_labels):
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'dogs_db'
        return 'default'