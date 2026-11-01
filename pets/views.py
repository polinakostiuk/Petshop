from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Brand, Category, Product
from .serializers import BrandSerializer, CategorySerializer, ProductSerializer


def error_response(message, http_status, details=None):
    body = {'error': message}
    if details is not None:
        body['details'] = details
    return Response(body, status=http_status)


def read_json(request):
    try:
        return request.data
    except ParseError:
        return None


class BaseListAPIView(APIView):
    queryset = None
    serializer_class = None

    def get(self, request):
        objects = self.queryset.order_by('id')
        serializer = self.serializer_class(objects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = read_json(request)
        if data is None:
            return error_response(
                'Некоректний JSON.', status.HTTP_400_BAD_REQUEST
            )
        serializer = self.serializer_class(data=data)
        if not serializer.is_valid():
            return error_response(
                'Некоректні дані.',
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BaseDetailAPIView(APIView):
    queryset = None
    serializer_class = None
    # "{pk}" is replaced with the id from the URL
    not_found_message = ''
    # "{name}" and "{count}" are replaced with the object name and the number
    # of products that block the deletion. Empty -> nothing blocks deletion.
    delete_conflict_message = ''

    def get_object(self, pk):
        return self.queryset.filter(pk=pk).first()

    def not_found(self, pk):
        message = self.not_found_message.format(pk=pk)
        return error_response(message, status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        obj = self.get_object(pk)
        if obj is None:
            return self.not_found(pk)
        return Response(
            self.serializer_class(obj).data, status=status.HTTP_200_OK
        )

    def put(self, request, pk):
        obj = self.get_object(pk)
        if obj is None:
            return self.not_found(pk)
        data = read_json(request)
        if data is None:
            return error_response(
                'Некоректний JSON.', status.HTTP_400_BAD_REQUEST
            )
        serializer = self.serializer_class(obj, data=data)
        if not serializer.is_valid():
            return error_response(
                'Некоректні дані.',
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if obj is None:
            return self.not_found(pk)
        try:
            obj.delete()
        except ProtectedError:
            if not self.delete_conflict_message:
                raise
            message = self.delete_conflict_message.format(
                name=obj.name, count=obj.products.count()
            )
            return error_response(message, status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryListAPIView(BaseListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CategoryDetailAPIView(BaseDetailAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    not_found_message = 'Категорію з id={pk} не знайдено.'
    delete_conflict_message = (
        'Неможливо видалити категорію «{name}»: '
        'до неї належить товарів - {count}.'
    )


class BrandListAPIView(BaseListAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer


class BrandDetailAPIView(BaseDetailAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    not_found_message = 'Бренд з id={pk} не знайдено.'
    delete_conflict_message = (
        'Неможливо видалити бренд «{name}»: '
        'з ним пов\'язано товарів - {count}.'
    )


class ProductListAPIView(BaseListAPIView):
    queryset = Product.objects.select_related('category', 'brand')
    serializer_class = ProductSerializer


class ProductDetailAPIView(BaseDetailAPIView):
    queryset = Product.objects.select_related('category', 'brand')
    serializer_class = ProductSerializer
    not_found_message = 'Товар з id={pk} не знайдено.'