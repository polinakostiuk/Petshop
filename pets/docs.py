from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema

from .serializers import ErrorSerializer


def error(description, message):
    return OpenApiResponse(
        response=ErrorSerializer,
        description=description,
        examples=[OpenApiExample('Приклад', value={'error': message})],
    )


UNAUTHORIZED = error(
    '401: немає access-токена, він прострочений або неправильний.',
    'Потрібна авторизація. Увійдіть і передайте access-токен '
    'у заголовку Authorization: Bearer <токен>.',
)
FORBIDDEN = error(
    '403: користувач увійшов, але він не адміністратор.',
    'Недостатньо прав: цю дію може виконати лише адміністратор.',
)
BAD_DATA = OpenApiResponse(
    response=ErrorSerializer,
    description='400: некоректні дані або зламаний JSON.',
    examples=[OpenApiExample(
        'Порожня назва',
        value={
            'error': 'Некоректні дані.',
            'details': {'name': ['Це поле не може бути порожнім.']},
        },
    )],
)


def not_found(message):
    return error('404: об\'єкта з таким id не існує.', message)


def list_docs(tag, serializer, list_summary, create_summary,
              create_example=None):
    return {
        'get': extend_schema(
            tags=[tag],
            summary=list_summary,
            description='Доступно всім, токен не потрібен. '
                        'Об\'єкти відсортовані за id.',
            responses={200: serializer(many=True)},
        ),
        'post': extend_schema(
            tags=[tag],
            summary=create_summary,
            description='Лише для адміністратора (потрібен access-токен).',
            request=serializer,
            examples=[create_example] if create_example else None,
            responses={
                201: serializer,
                400: BAD_DATA,
                401: UNAUTHORIZED,
                403: FORBIDDEN,
            },
        ),
    }


def detail_docs(tag, serializer, one_summary, update_summary,
                delete_summary, not_found_message, conflict_message=None,
                update_example=None):
    delete_responses = {
        204: OpenApiResponse(description='Видалено, тіла відповіді немає.'),
        401: UNAUTHORIZED,
        403: FORBIDDEN,
        404: not_found(not_found_message),
    }
    if conflict_message:
        delete_responses[409] = error(
            '409: об\'єкт не можна видалити, бо до нього прив\'язані товари.',
            conflict_message,
        )
    return {
        'get': extend_schema(
            tags=[tag],
            summary=one_summary,
            description='Доступно всім, токен не потрібен.',
            responses={
                200: serializer,
                404: not_found(not_found_message),
            },
        ),
        'put': extend_schema(
            tags=[tag],
            summary=update_summary,
            description='Лише для адміністратора. PUT замінює об\'єкт повністю: '
                        'усі обов\'язкові поля треба передати знову. '
                        'Часткового оновлення (PATCH) немає, відповідь 405.',
            request=serializer,
            examples=[update_example] if update_example else None,
            responses={
                200: serializer,
                400: BAD_DATA,
                401: UNAUTHORIZED,
                403: FORBIDDEN,
                404: not_found(not_found_message),
            },
        ),
        'delete': extend_schema(
            tags=[tag],
            summary=delete_summary,
            description='Лише для адміністратора.',
            responses=delete_responses,
        ),
    }


PRODUCT_EXAMPLE = OpenApiExample(
    'Новий товар',
    value={
        'name': 'Сухий корм для собак, 2 кг',
        'description': 'Повноцінний корм для дорослих собак середніх порід',
        'price': '349.90',
        'stock': 25,
        'category': 1,
        'brand': 1,
    },
    request_only=True,
)