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
