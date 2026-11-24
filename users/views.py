import logging

from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from drf_spectacular.utils import (
    OpenApiExample,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from pets.docs import BAD_DATA, UNAUTHORIZED
from pets.docs import error as error_doc
from pets.views import error_response, read_json

from .serializers import (
    LoginSerializer,
    RefreshSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .tokens import ACCESS, REFRESH, TokenError, create_token, decode_token

logger = logging.getLogger(__name__)


def bad_json():
    return error_response('Некоректний JSON.', status.HTTP_400_BAD_REQUEST)


def bad_data(serializer):
    return error_response(
        'Некоректні дані.', status.HTTP_400_BAD_REQUEST, serializer.errors
    )

class RegisterAPIView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Авторизація'],
        summary='Реєстрація',
        description='Створює звичайного користувача (не адміністратора). '
                    'Токен не потрібен. Пароль зберігається лише у вигляді хешу.',
        request=RegisterSerializer,
        examples=[OpenApiExample(
            'Нова користувачка',
            value={
                'username': 'anna',
                'first_name': 'Анна',
                'last_name': 'Коваль',
                'email': 'anna@example.com',
                'password': 'Str0ng-pass-2026',
                'password_confirmation': 'Str0ng-pass-2026',
            },
            request_only=True,
        )],
        responses={201: UserSerializer, 400: BAD_DATA},
    )
    def post(self, request):
        data = read_json(request)
        if data is None:
            logger.warning('Реєстрація: некоректний JSON')
            return bad_json()
        serializer = RegisterSerializer(data=data)
        if not serializer.is_valid():
            logger.warning('Реєстрація відхилена, поля з помилками: %s',
                           list(serializer.errors))
            return bad_data(serializer)
        try:
            user = serializer.save()
        except IntegrityError:
            logger.warning('Реєстрація: ім\'я вже зайняте (гонка запитів)')
            return error_response(
                'Некоректні дані.',
                status.HTTP_400_BAD_REQUEST,
                {'username': ['Користувач з таким іменем вже існує.']},
            )
        logger.info('Зареєстровано користувача %s (id=%s)',
                    user.username, user.pk)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Авторизація'],
        summary='Вхід: отримати токени',
        description='Перевіряє ім\'я користувача й пароль і видає два токени: '
                    'access (живе 5 хвилин, передається в Authorization: '
                    'Bearer) та refresh (живе 7 днів, потрібен лише для '
                    'POST /api/auth/refresh).',
        request=LoginSerializer,
        examples=[OpenApiExample(
            'Вхід', value={'username': 'anna', 'password': 'Str0ng-pass-2026'},
            request_only=True,
        )],
        responses={
            200: inline_serializer('LoginResponse', fields={
                'access': serializers.CharField(),
                'refresh': serializers.CharField(),
                'user': UserSerializer(),
            }),
            400: BAD_DATA,
            401: error_doc('401: невірне ім\'я користувача або пароль.',
                       'Невірне ім\'я користувача або пароль.'),
        },
    )
    def post(self, request):
        data = read_json(request)
        if data is None:
            logger.warning('Вхід: некоректний JSON')
            return bad_json()
        serializer = LoginSerializer(data=data)
        if not serializer.is_valid():
            logger.warning('Вхід: не заповнено поля %s', list(serializer.errors))
            return bad_data(serializer)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            logger.warning('Невдала спроба входу для %s',
                           serializer.validated_data['username'])
            return error_response(
                "Невірне ім'я користувача або пароль.",
                status.HTTP_401_UNAUTHORIZED,
            )
        logger.info('Користувач %s увійшов (id=%s)', user.username, user.pk)
        return Response({
            'access': create_token(user, ACCESS),
            'refresh': create_token(user, REFRESH),
            'user': UserSerializer(user).data,
        })


class RefreshAPIView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Авторизація'],
        summary='Оновити access-токен',
        description='Обмінює refresh-токен на новий access-токен. '
                    'Викликається, коли захищений запит повернув 401.',
        request=RefreshSerializer,
        responses={
            200: inline_serializer('RefreshResponse', fields={
                'access': serializers.CharField(),
            }),
            400: BAD_DATA,
            401: error_doc('401: refresh-токен недійсний або прострочений.',
                       'Термін дії токена закінчився.'),
        },
    )
    def post(self, request):
        data = read_json(request)
        if data is None:
            logger.warning('Оновлення токена: некоректний JSON')
            return bad_json()
        serializer = RefreshSerializer(data=data)
        if not serializer.is_valid():
            logger.warning('Оновлення токена: не передано refresh')
            return bad_data(serializer)

        try:
            payload = decode_token(serializer.validated_data['refresh'], REFRESH)
        except TokenError as error:
            logger.warning('Оновлення токена відхилено: %s', error)
            return error_response(str(error), status.HTTP_401_UNAUTHORIZED)

        user = get_user_model().objects.filter(
            pk=payload['user_id'], is_active=True
        ).first()
        if user is None:
            logger.warning('Оновлення токена: користувача id=%s не знайдено',
                           payload['user_id'])
            return error_response(
                'Користувача з цього токена не знайдено.',
                status.HTTP_401_UNAUTHORIZED,
            )
        logger.info('Користувачу %s видано новий access-токен', user.username)
        return Response({'access': create_token(user, ACCESS)})


class MeAPIView(APIView):

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Авторизація'],
        summary='Мій профіль',
        description='Дані поточного користувача. Потрібен access-токен.',
        responses={200: UserSerializer, 401: UNAUTHORIZED},
    )
    def get(self, request):
        return Response(UserSerializer(request.user).data)