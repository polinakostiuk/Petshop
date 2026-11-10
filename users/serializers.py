from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

UserModel = get_user_model()


class RegisterSerializer(serializers.Serializer):

    username = serializers.CharField(
        max_length=150, validators=[UnicodeUsernameValidator()]
    )
    first_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    last_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    email = serializers.EmailField(max_length=254)

    password = serializers.CharField(
        max_length=128, write_only=True, trim_whitespace=False
    )
    password_confirmation = serializers.CharField(
        max_length=128, write_only=True, trim_whitespace=False
    )

    def validate_username(self, value):
        if UserModel.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                'Користувач з таким іменем вже існує.'
            )
        return value

    def validate_email(self, value):
        if UserModel.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                'Користувач з таким email вже існує.'
            )
        return value.lower()

    def validate_password(self, value):
        data = self.initial_data
        user = User(
            username=str(data.get('username', '')),
            email=str(data.get('email', '')),
            first_name=str(data.get('first_name', '')),
            last_name=str(data.get('last_name', '')),
        )
        try:
            validate_password(value, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages))
        return value

    def validate_password_confirmation(self, value):
        if value != self.initial_data.get('password'):
            raise serializers.ValidationError('Паролі не збігаються.')
        return value

    def create(self, validated_data):
        validated_data.pop('password_confirmation')
        return UserModel.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserModel
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_staff', 'date_joined',
        ]
        read_only_fields = fields