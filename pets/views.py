import logging

from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.exceptions import ParseError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema_view

from users.permissions import IsAdminOrReadOnly

from .docs import PRODUCT_EXAMPLE, detail_docs, list_docs
from .models import Brand, Category, Product
from .serializers import BrandSerializer, CategorySerializer, ProductSerializer

logger = logging.getLogger(__name__)


def actor(request):
    user = request.user
    return user.username if user.is_authenticated else 'anonymous'


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
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        objects = self.queryset.order_by('id')
        serializer = self.serializer_class(objects, many=True)
        logger.debug('%s: список, об\'єктів - %s', request.path, len(objects))
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = read_json(request)
        if data is None:
            logger.warning('POST %s: некоректний JSON (%s)',
                           request.path, actor(request))
            return error_response(
                'Некоректний JSON.', status.HTTP_400_BAD_REQUEST
            )
        serializer = self.serializer_class(data=data)
        if not serializer.is_valid():
            logger.warning('POST %s: некоректні дані, поля з помилками: %s',
                           request.path, list(serializer.errors))
            return error_response(
                'Некоректні дані.',
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )
        obj = serializer.save()
        logger.info('POST %s: створено id=%s користувачем %s',
                    request.path, obj.pk, actor(request))
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BaseDetailAPIView(APIView):
    queryset = None
    serializer_class = None
    permission_classes = [IsAdminOrReadOnly]

    not_found_message = ''

    delete_conflict_message = ''

    def get_object(self, pk):
        return self.queryset.filter(pk=pk).first()

    def not_found(self, pk):
        message = self.not_found_message.format(pk=pk)
        logger.warning('%s: об\'єкт id=%s не знайдено', self.request.path, pk)
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
            logger.warning('PUT %s: некоректний JSON (%s)',
                           request.path, actor(request))
            return error_response(
                'Некоректний JSON.', status.HTTP_400_BAD_REQUEST
            )
        serializer = self.serializer_class(obj, data=data)
        if not serializer.is_valid():
            logger.warning('PUT %s: некоректні дані, поля з помилками: %s',
                           request.path, list(serializer.errors))
            return error_response(
                'Некоректні дані.',
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )
        serializer.save()
        logger.info('PUT %s: оновлено id=%s користувачем %s',
                    request.path, pk, actor(request))
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        obj = self.get_object(pk)
        if obj is None:
            return self.not_found(pk)
        try:
            obj.delete()
        except ProtectedError:
            if not self.delete_conflict_message:
                logger.error('DELETE %s: неочікувана ProtectedError, id=%s',
                             request.path, pk)
                raise
            message = self.delete_conflict_message.format(
                name=obj.name, count=obj.products.count()
            )
            logger.warning('DELETE %s: id=%s не видалено, є пов\'язані товари',
                           request.path, pk)
            return error_response(message, status.HTTP_409_CONFLICT)
        logger.info('DELETE %s: видалено id=%s користувачем %s',
                    request.path, pk, actor(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(**list_docs(
    'Категорії', CategorySerializer,
    'Список категорій', 'Створити категорію',
))
class CategoryListAPIView(BaseListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


@extend_schema_view(**detail_docs(
    'Категорії', CategorySerializer,
    'Одна категорія за id', 'Оновити категорію', 'Видалити категорію',
    'Категорію з id=999999 не знайдено.',
    'Неможливо видалити категорію «Корм»: до неї належить товарів - 1.',
))
class CategoryDetailAPIView(BaseDetailAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    not_found_message = 'Категорію з id={pk} не знайдено.'
    delete_conflict_message = (
        'Неможливо видалити категорію «{name}»: '
        'до неї належить товарів - {count}.'
    )


@extend_schema_view(**list_docs(
    'Бренди', BrandSerializer,
    'Список брендів', 'Створити бренд',
))
class BrandListAPIView(BaseListAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer


@extend_schema_view(**detail_docs(
    'Бренди', BrandSerializer,
    'Один бренд за id', 'Оновити бренд', 'Видалити бренд',
    'Бренд з id=999999 не знайдено.',
    'Неможливо видалити бренд «Acana»: з ним пов\'язано товарів - 1.',
))
class BrandDetailAPIView(BaseDetailAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    not_found_message = 'Бренд з id={pk} не знайдено.'
    delete_conflict_message = (
        'Неможливо видалити бренд «{name}»: '
        'з ним пов\'язано товарів - {count}.'
    )


@extend_schema_view(**list_docs(
    'Товари', ProductSerializer,
    'Список товарів', 'Створити товар',
    create_example=PRODUCT_EXAMPLE,
))
class ProductListAPIView(BaseListAPIView):
    queryset = Product.objects.select_related('category', 'brand')
    serializer_class = ProductSerializer


@extend_schema_view(**detail_docs(
    'Товари', ProductSerializer,
    'Один товар за id', 'Оновити товар', 'Видалити товар',
    'Товар з id=999999 не знайдено.',
    update_example=PRODUCT_EXAMPLE,
))
class ProductDetailAPIView(BaseDetailAPIView):
    queryset = Product.objects.select_related('category', 'brand')
    serializer_class = ProductSerializer
    not_found_message = 'Товар з id={pk} не знайдено.'