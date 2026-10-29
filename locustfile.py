from faker import Faker
from locust import HttpUser, task, SequentialTaskSet, TaskSet, constant_throughput
from locust.exception import StopUser
import random

fake = Faker('ru_RU')


def check_post(response, message):
    if response.status_code != 200 or message not in response.text:
        response.failure(f'Операция не выполнена: {message}')


def login(client):
    with client.post('/login', data={
        'phone': '+7(900)000-00-00',
        'password': '12345678'
    }, catch_response=True) as response:
        if response.status_code != 200 or not response.url.endswith('/requests'):
            response.failure('Не удалось войти в систему')
            raise StopUser()


class AdminTests(TaskSet):
    def on_start(self):
        login(self.client)

    @task(10)
    def requests_list(self):
        self.client.get('/requests')

    @task(7)
    def request_detail(self):
        self.client.get(f'/requests/{random.randint(1, 16)}', name='/requests/[id]')

    @task(4)
    def requests_filter(self):
        self.client.get('/requests', params={
            'status': random.choice(['new', 'estimated', 'agreed', 'assigned', 'done', 'paid'])
        }, name='/requests?status')

    @task(3)
    def requests_search(self):
        self.client.get('/requests', params={'q': fake.last_name()}, name='/requests?q')

    @task(2)
    def workers(self):
        self.client.get('/workers')

    @task(2)
    def services(self):
        self.client.get('/services')

    @task(1)
    def vehicles(self):
        self.client.get('/vehicles')

    @task(1)
    def analytics(self):
        self.client.get('/analytics')

    @task(1)
    def add_worker(self):
        worker_data = {
            'full_name': fake.name(),
            'phone': fake.numerify('+7(9##)###-##-##'),
            'position': 'driver',
            'license_cat': random.choice(['B', 'C']),
            'rank': random.randint(1, 7),
        }

        with self.client.post('/workers/save', data=worker_data, catch_response=True) as response:
            check_post(response, 'Работник добавлен')

    @task(1)
    def add_service(self):
        service_data = {
            'name': f'{random.choice(["Упаковка груза", "Доставка по городу", "Работа грузчика"])} {random.randint(1, 9999)}',
            'price': str(random.randint(100, 5000)),
            'unit': random.choice(['шт', 'км', 'ч', 'эт', 'м3', 'сут', 'кг']),
            'report_kind': random.choice(['arrival', 'photo', 'comment']),
        }

        with self.client.post('/services/save', data=service_data, catch_response=True) as response:
            check_post(response, 'Тариф добавлен')

    @task(1)
    def add_vehicle(self):
        letters = 'АВЕКМНОРСТУХ'
        vehicle_data = {
            'model': random.choice(['ГАЗель Next', 'Ford Transit', 'Mercedes Sprinter']),
            'plate_number': f'{random.choice(letters)}{random.randint(100, 999)}'
                            f'{random.choice(letters)}{random.choice(letters)}{random.choice([77, 78, 50])}',
            'capacity_kg': random.choice([1000, 1500, 3000, 5000]),
            'volume_m3': str(random.choice([9, 12, 16, 20])),
        }

        with self.client.post('/vehicles/save', data=vehicle_data, catch_response=True) as response:
            check_post(response, 'Автомобиль добавлен')

    @task(1)
    def add_estimate_item(self):
        item_data = {
            'service_id': random.randint(1, 8),
            'quantity': str(random.randint(1, 10)),
            'added_by': 'chief',
        }

        rid = random.randint(12, 15)
        with self.client.post(f'/requests/{rid}/estimate/add', data=item_data,
                              name='/requests/[id]/estimate/add', catch_response=True) as response:
            check_post(response, 'Позиция добавлена в расчёт')


class EstimateScenario(SequentialTaskSet):
    def on_start(self):
        login(self.client)
        self.rid = random.randint(12, 15)

    @task
    def open_list(self):
        self.client.get('/requests')

    @task
    def open_request(self):
        self.client.get(f'/requests/{self.rid}', name='/requests/[id]')

    @task
    def open_services(self):
        self.client.get('/services')

    @task
    def open_notifications(self):
        self.client.get('/notifications')

    @task
    def add_item(self):
        item_data = {
            'service_id': random.randint(1, 8),
            'quantity': str(random.randint(1, 5)),
            'added_by': 'chief',
        }

        with self.client.post(f'/requests/{self.rid}/estimate/add', data=item_data,
                              name='/requests/[id]/estimate/add', catch_response=True) as response:
            check_post(response, 'Позиция добавлена в расчёт')

    @task
    def check_request(self):
        self.client.get(f'/requests/{self.rid}', name='/requests/[id]')

    @task
    def open_clients(self):
        self.client.get('/clients')


class AdminUser(HttpUser):
    tasks = [AdminTests]
    wait_time = constant_throughput(1)
    weight = 3


class ScenarioUser(HttpUser):
    tasks = [EstimateScenario]
    wait_time = constant_throughput(1)
    weight = 1
