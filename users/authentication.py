import logging

from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .tokens import ACCESS, TokenError, decode_token

logger = logging.getLogger(__name__)


class JWTAuthentication(BaseAuthentication):

    def authenticate(self, request):
        header = request.headers.get('Authorization')
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            logger.warning('%s: неправильний формат заголовка Authorization',
                           request.path)
            raise AuthenticationFailed(
                'Невірний заголовок Authorization. '
                'Очікується формат: Bearer <access-токен>.'
            )

        try:
            payload = decode_token(parts[1], ACCESS)
        except TokenError as error:
            logger.warning('%s: токен відхилено: %s', request.path, error)
            raise AuthenticationFailed(str(error))

        user = get_user_model().objects.filter(
            pk=payload['user_id'], is_active=True
        ).first()
        if user is None:
            logger.warning('%s: токен виданий неіснуючому користувачу id=%s',
                           request.path, payload['user_id'])
            raise AuthenticationFailed('Користувача з цього токена не знайдено.')
        return user, parts[1]

    def authenticate_header(self, request):
        return 'Bearer'