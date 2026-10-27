from django.db import models
from django.core.validators import MinValueValidator

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Назва категорії")
    description = models.TextField(blank=True, null=True, verbose_name="Опис")

    def __str__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Бренд / Виробник")
    country = models.CharField(max_length=100, blank=True, null=True, verbose_name="Країна")

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Назва товару")
    description = models.TextField(blank=True, null=True, verbose_name="Опис товару")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="Ціна"
    )
    stock = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Кількість на складі"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Категорія"
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Бренд"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name