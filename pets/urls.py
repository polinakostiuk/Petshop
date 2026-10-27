from django.urls import path
from .views import CategoryListAPIView,CategoryDetailAPIView,BrandListAPIView,ProductListAPIView

urlpatterns = [
    path('categories', CategoryListAPIView.as_view(), name='category-list'),
    path('categories/<int:pk>', CategoryDetailAPIView.as_view(), name='category-detail'),
    path('brands', BrandListAPIView.as_view(), name='brand-list'),
    path('products', ProductListAPIView.as_view(), name='product-list'),
]