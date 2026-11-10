import base64
import binascii
import hashlib
import hmac
import json
import time

from django.conf import settings

ACCESS = 'access'
REFRESH = 'refresh'


class TokenError(Exception):
    """Токен недійсний: підроблений, пошкоджений, прострочений або не того типу."""


def _b64_encode(data):

    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _b64_decode(text):

    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def _sign(message):
    key = settings.SECRET_KEY.encode()
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def _lifetime(token_type):
    if token_type == ACCESS:
        return getattr(settings, 'JWT_ACCESS_LIFETIME_SECONDS', 5 * 60)
    return getattr(settings, 'JWT_REFRESH_LIFETIME_SECONDS', 7 * 24 * 3600)


def create_token(user, token_type):
    now = int(time.time())
    header = {'alg': 'HS256', 'typ': 'JWT'}
    payload = {
        'user_id': user.pk,
        'type': token_type,
        'iat': now,                              # коли створено
        'exp': now + _lifetime(token_type),      # коли перестає діяти
    }
    signing_input = '.'.join(
        _b64_encode(json.dumps(part, separators=(',', ':')).encode())
        for part in (header, payload)
    )
    return signing_input + '.' + _b64_encode(_sign(signing_input))


def decode_token(token, token_type):
    try:
        header_part, payload_part, signature_part = token.split('.')
        header = json.loads(_b64_decode(header_part))
        payload = json.loads(_b64_decode(payload_part))
        signature = _b64_decode(signature_part)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise TokenError('Токен пошкоджений або має неправильний формат.')

    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise TokenError('Токен пошкоджений або має неправильний формат.')

    if header.get('alg') != 'HS256':
        raise TokenError('Непідтримуваний алгоритм підпису токена.')

    expected = _sign(header_part + '.' + payload_part)
    if not hmac.compare_digest(signature, expected):
        raise TokenError('Підпис токена недійсний.')

    expires_at = payload.get('exp')
    if not isinstance(expires_at, int) or expires_at <= time.time():
        raise TokenError('Термін дії токена закінчився.')

    if payload.get('type') != token_type:
        raise TokenError('Токен не підходить для цієї дії (неправильний тип).')

    if not isinstance(payload.get('user_id'), int):
        raise TokenError('Токен пошкоджений або має неправильний формат.')
    return payload