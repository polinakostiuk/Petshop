import logging

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from users.tokens import ACCESS, create_token

from .models import Brand, Category, Product

User = get_user_model()

LIST_URL = '/api/products'


def detail_url(pk):
    return f'/api/products/{pk}'


def valid_product(**changes):
    data = {
        'name': 'Нашийник',
        'description': 'Шкіряний нашийник',
        'price': '199.90',
        'stock': 7,
        'category': 2,
        'brand': 2,
    }
    data.update(changes)
    return data


def setUpModule():
    # Без цього логи сервера засмічували б вивід тестів
    logging.disable(logging.CRITICAL)


def tearDownModule():
    logging.disable(logging.NOTSET)


class CatalogTestCase(APITestCase):

    fixtures = ['catalog.json']

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            'admin', 'admin@example.com', 'Admin-pass-2026', is_staff=True
        )
        cls.user = User.objects.create_user(
            'anna', 'anna@example.com', 'Str0ng-pass-2026'
        )

    def login_as(self, user):
        token = create_token(user, ACCESS)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def login_admin(self):
        self.login_as(self.admin)


class ProductReadTests(CatalogTestCase):

    def test_list_is_public_and_sorted_by_id(self):
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p['id'] for p in response.data], [1, 2, 3])

    def test_list_item_has_names_and_decimal_price_as_string(self):
        first = self.client.get(LIST_URL).data[0]
        self.assertEqual(first['name'], 'Сухий корм для собак')
        self.assertEqual(first['price'], '349.90')
        self.assertEqual(first['category_name'], 'Корм')
        self.assertEqual(first['brand_name'], 'Acana')

    def test_list_makes_one_database_query(self):
        # select_related підтягує категорію й бренд тим самим запитом
        with self.assertNumQueries(1):
            self.client.get(LIST_URL)

    def test_get_one(self):
        response = self.client.get(detail_url(3))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], "М'яч Kong")
        self.assertEqual(response.data['stock'], 5)

    def test_get_missing_returns_404(self):
        response = self.client.get(detail_url(999999))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.data, {'error': 'Товар з id=999999 не знайдено.'}
        )


class ProductCreateTests(CatalogTestCase):

    def test_admin_creates_product(self):
        self.login_admin()
        response = self.client.post(LIST_URL, valid_product(), format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['category_name'], 'Іграшки')
        self.assertEqual(Product.objects.count(), 4)

    def test_stock_defaults_to_zero(self):
        self.login_admin()
        data = valid_product()
        del data['stock']
        response = self.client.post(LIST_URL, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['stock'], 0)

    def test_anonymous_gets_401(self):
        response = self.client.post(LIST_URL, valid_product(), format='json')
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.data)
        self.assertEqual(Product.objects.count(), 3)

    def test_regular_user_gets_403(self):
        self.login_as(self.user)
        response = self.client.post(LIST_URL, valid_product(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertIn('адміністратор', response.data['error'])
        self.assertEqual(Product.objects.count(), 3)

    def test_invalid_data_returns_400_with_details(self):
        self.login_admin()
        cases = {
            'порожня назва': ('name', valid_product(name='')),
            'надто довга назва': ('name', valid_product(name='а' * 201)),
            'ціна нуль': ('price', valid_product(price='0')),
            "від'ємна ціна": ('price', valid_product(price='-5')),
            'ціна не число': ('price', valid_product(price='abc')),
            "від'ємна кількість": ('stock', valid_product(stock=-1)),
            'немає категорії': ('category', valid_product(category=None)),
            'категорії не існує': ('category', valid_product(category=999)),
            'бренду не існує': ('brand', valid_product(brand=999)),
        }
        for title, (field, data) in cases.items():
            with self.subTest(title):
                response = self.client.post(LIST_URL, data, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data['error'], 'Некоректні дані.')
                self.assertIn(field, response.data['details'])
        self.assertEqual(Product.objects.count(), 3)

    def test_missing_required_field_returns_400(self):
        self.login_admin()
        data = valid_product()
        del data['price']
        response = self.client.post(LIST_URL, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('price', response.data['details'])

    def test_broken_json_returns_400(self):
        self.login_admin()
        response = self.client.post(
            LIST_URL, '{"name": ', content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {'error': 'Некоректний JSON.'})


class ProductUpdateTests(CatalogTestCase):

    def test_admin_updates_product(self):
        self.login_admin()
        response = self.client.put(
            detail_url(1), valid_product(name='Новий корм', price='10.00'),
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        product = Product.objects.get(pk=1)
        self.assertEqual(product.name, 'Новий корм')
        self.assertEqual(str(product.price), '10.00')
        # PUT оновлює існуючий запис, а не створює новий
        self.assertEqual(Product.objects.count(), 3)

    def test_invalid_data_does_not_change_product(self):
        self.login_admin()
        response = self.client.put(
            detail_url(1), valid_product(price='0'), format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('price', response.data['details'])
        self.assertEqual(Product.objects.get(pk=1).name, 'Сухий корм для собак')

    def test_missing_product_returns_404(self):
        self.login_admin()
        response = self.client.put(
            detail_url(999999), valid_product(), format='json'
        )
        self.assertEqual(response.status_code, 404)

    def test_broken_json_returns_400(self):
        self.login_admin()
        response = self.client.put(
            detail_url(1), 'не json', content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_anonymous_gets_401(self):
        response = self.client.put(detail_url(1), valid_product(), format='json')
        self.assertEqual(response.status_code, 401)

    def test_regular_user_gets_403(self):
        self.login_as(self.user)
        response = self.client.put(detail_url(1), valid_product(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Product.objects.get(pk=1).name, 'Сухий корм для собак')

    def test_patch_is_not_supported(self):
        self.login_admin()
        response = self.client.patch(
            detail_url(1), {'name': 'X'}, format='json'
        )
        self.assertEqual(response.status_code, 405)
        self.assertIn('error', response.data)


class ProductDeleteTests(CatalogTestCase):

    def test_admin_deletes_product(self):
        self.login_admin()
        response = self.client.delete(detail_url(1))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Product.objects.filter(pk=1).exists())
        # Повторне видалення того ж товару: його вже немає
        self.assertEqual(self.client.delete(detail_url(1)).status_code, 404)

    def test_missing_product_returns_404(self):
        self.login_admin()
        self.assertEqual(self.client.delete(detail_url(999999)).status_code, 404)

    def test_anonymous_gets_401(self):
        self.assertEqual(self.client.delete(detail_url(1)).status_code, 401)
        self.assertTrue(Product.objects.filter(pk=1).exists())

    def test_regular_user_gets_403(self):
        self.login_as(self.user)
        self.assertEqual(self.client.delete(detail_url(1)).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=1).exists())


class CategoryAndBrandDeleteTests(CatalogTestCase):

    def test_category_with_products_gives_409(self):
        self.login_admin()
        response = self.client.delete('/api/categories/1')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data['error'],
            'Неможливо видалити категорію «Корм»: до неї належить товарів - 2.',
        )
        self.assertTrue(Category.objects.filter(pk=1).exists())

    def test_brand_with_products_gives_409(self):
        self.login_admin()
        response = self.client.delete('/api/brands/1')
        self.assertEqual(response.status_code, 409)
        self.assertIn('Acana', response.data['error'])
        self.assertTrue(Brand.objects.filter(pk=1).exists())

    def test_empty_category_and_brand_can_be_deleted(self):
        self.login_admin()
        self.assertEqual(self.client.delete('/api/categories/3').status_code, 204)
        self.assertEqual(self.client.delete('/api/brands/3').status_code, 204)

    def test_category_and_brand_can_be_deleted_after_their_products(self):
        self.login_admin()
        # У категорії «Іграшки» і бренду Kong є лише товар 3
        self.assertEqual(self.client.delete('/api/categories/2').status_code, 409)
        self.assertEqual(self.client.delete('/api/brands/2').status_code, 409)
        self.client.delete(detail_url(3))
        self.assertEqual(self.client.delete('/api/categories/2').status_code, 204)
        self.assertEqual(self.client.delete('/api/brands/2').status_code, 204)

    def test_duplicate_category_name_gives_400(self):
        self.login_admin()
        response = self.client.post(
            '/api/categories', {'name': 'Корм'}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.data['details'])


class LoggingTests(CatalogTestCase):

    def setUp(self):
        # У цьому класі логи потрібні: вмикаємо їх назад
        logging.disable(logging.NOTSET)
        self.addCleanup(logging.disable, logging.CRITICAL)

    def test_creating_product_is_logged_as_info(self):
        self.login_admin()
        with self.assertLogs('pets', level='INFO') as logs:
            self.client.post(LIST_URL, valid_product(), format='json')
        self.assertTrue(any(
            line.startswith('INFO') and 'створено' in line and 'admin' in line
            for line in logs.output
        ))

    def test_missing_object_is_logged_as_warning(self):
        with self.assertLogs('pets', level='WARNING') as logs:
            self.client.get(detail_url(999999))
        self.assertTrue(any('не знайдено' in line for line in logs.output))

    def test_forbidden_attempt_is_logged_as_warning(self):
        self.login_as(self.user)
        with self.assertLogs('users', level='WARNING') as logs:
            self.client.delete(detail_url(1))
        self.assertTrue(any('anna' in line for line in logs.output))

    def test_token_is_not_written_to_logs(self):
        token = create_token(self.admin, ACCESS)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        with self.assertLogs('pets', level='DEBUG') as logs:
            self.client.post(LIST_URL, valid_product(), format='json')
        self.assertNotIn(token, '\n'.join(logs.output))


class ApiDocsTests(APITestCase):

    def test_schema_describes_products_and_jwt(self):
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, 200)
        text = response.content.decode()
        self.assertIn('/api/products', text)
        self.assertIn('/api/auth/login', text)
        self.assertIn('jwtAuth', text)

    def test_swagger_ui_and_redoc_open(self):
        self.assertEqual(self.client.get('/api/docs/').status_code, 200)
        self.assertEqual(self.client.get('/api/redoc/').status_code, 200)