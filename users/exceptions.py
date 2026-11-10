from rest_framework.exceptions import NotAuthenticated
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):

    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, NotAuthenticated):
        message = (
            'Потрібна авторизація. Увійдіть і передайте access-токен '
            'у заголовку Authorization: Bearer <токен>.'
        )
    elif isinstance(response.data, dict) and 'detail' in response.data:
        message = str(response.data['detail'])
    else:
        return response

    response.data = {'error': message}
    return response