from django.urls import path

from .views import (
    BrandDetailAPIView,
    BrandListAPIView,
    CategoryDetailAPIView,
    CategoryListAPIView,
    ProductDetailAPIView,
    ProductListAPIView,
)

urlpatterns = [
    path('categories', CategoryListAPIView.as_view(), name='category-list'),
    path(
        'categories/<int:pk>',
        CategoryDetailAPIView.as_view(),
        name='category-detail',
    ),
    path('brands', BrandListAPIView.as_view(), name='brand-list'),
    path('brands/<int:pk>', BrandDetailAPIView.as_view(), name='brand-detail'),
    path('products', ProductListAPIView.as_view(), name='product-list'),
    path(
        'products/<int:pk>',
        ProductDetailAPIView.as_view(),
        name='product-detail',
    ),
]