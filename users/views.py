from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from pets.views import error_response, read_json
from .serializers import (
    LoginSerializer,
    RefreshSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .tokens import ACCESS, REFRESH, TokenError, create_token, decode_token

def bad_json():
    return error_response('Некоректний JSON.', status.HTTP_400_BAD_REQUEST)


def bad_data(serializer):
    return error_response(
        'Некоректні дані.', status.HTTP_400_BAD_REQUEST, serializer.errors
    )



class RegisterAPIView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = read_json(request)
        if data is None:
            return bad_json()
        serializer = RegisterSerializer(data=data)
        if not serializer.is_valid():
            return bad_data(serializer)
        try:
            user = serializer.save()
        except IntegrityError:
            return error_response(
                'Некоректні дані.',
                status.HTTP_400_BAD_REQUEST,
                {'username': ['Користувач з таким іменем вже існує.']},
            )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = read_json(request)
        if data is None:
            return bad_json()
        serializer = LoginSerializer(data=data)
        if not serializer.is_valid():
            return bad_data(serializer)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return error_response(
                "Невірне ім'я користувача або пароль.",
                status.HTTP_401_UNAUTHORIZED,
            )
        return Response({
            'access': create_token(user, ACCESS),
            'refresh': create_token(user, REFRESH),
            'user': UserSerializer(user).data,
        })


class RefreshAPIView(APIView):


    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = read_json(request)
        if data is None:
            return bad_json()
        serializer = RefreshSerializer(data=data)
        if not serializer.is_valid():
            return bad_data(serializer)

        try:
            payload = decode_token(serializer.validated_data['refresh'], REFRESH)
        except TokenError as error:
            return error_response(str(error), status.HTTP_401_UNAUTHORIZED)

        user = get_user_model().objects.filter(
            pk=payload['user_id'], is_active=True
        ).first()
        if user is None:
            return error_response(
                'Користувача з цього токена не знайдено.',
                status.HTTP_401_UNAUTHORIZED,
            )
        return Response({'access': create_token(user, ACCESS)})


class MeAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)