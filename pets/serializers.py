from rest_framework import serializers
from .models import Category, Brand, Product

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    brand_name = serializers.ReadOnlyField(source='brand.name')

    class Meta:
        model = Product
        fields = '__all__'



class ErrorSerializer(serializers.Serializer):

    error = serializers.CharField(help_text='Опис помилки')
    details = serializers.DictField(
        required=False,
        help_text='Лише для 400: список проблем по кожному полю',
    )