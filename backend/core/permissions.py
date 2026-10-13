from rest_framework import permissions


class IsNKPMember(permissions.BasePermission):
    """Доступ только для членов НКП"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            from . import models_django as models
            user = models.User.objects.get(email=request.user.email)
            return user.is_nkp_member
        except Exception:
            return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Редактирование только своих объектов"""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.owner.email == request.user.email if hasattr(obj, 'owner') else True


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """
    Чтение — всем. Изменение/удаление — только автору объекта
    (по email) либо администратору (is_staff/superuser).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        owner = getattr(obj, 'owner', None)
        return bool(owner and owner.email == user.email)
