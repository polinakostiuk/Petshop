import logging

from rest_framework.permissions import SAFE_METHODS, BasePermission

logger = logging.getLogger(__name__)


class IsAdminOrReadOnly(BasePermission):


    message = 'Недостатньо прав: цю дію може виконати лише адміністратор.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        allowed = bool(user and user.is_authenticated and user.is_staff)
        if not allowed:
            who = user.username if user.is_authenticated else 'anonymous'
            logger.warning('%s %s заборонено для %s',
                           request.method, request.path, who)
        return allowed