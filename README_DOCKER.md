# Docker Setup для Animal Shelter Project

Этот проект настроен для работы **как в Docker, так и локально** без изменений в коде.

## Режимы работы

### Локальная разработка (без Docker)
Проект работает как обычно с локальной SQL Server базой данных. Все настройки остаются прежними.

### Docker режим
Проект работает в Docker с разделением на три сервиса:
- **db** - SQL Server база данных
- **api** - Django REST API (порт 8000)
- **web** - Django веб-интерфейс (порт 8001)

## Требования

### Для локальной разработки:
- Python 3.11+
- SQL Server (локальный или удаленный)
- ODBC Driver 17 for SQL Server

### Для Docker:
- Docker
- Docker Compose

## Запуск проекта

### Локальная разработка (без Docker)

1. Активируйте виртуальное окружение:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Примените миграции:
```bash
python manage.py migrate
```

4. Запустите сервер:
```bash
python manage.py runserver
```

Проект будет доступен на http://localhost:8000/

### Docker режим

1. Убедитесь, что у вас установлены Docker и Docker Compose

2. Запустите все сервисы:
```bash
docker-compose up -d
```

3. Дождитесь инициализации базы данных (может занять 1-2 минуты). Проверить статус можно командой:
```bash
docker-compose logs db_init
```

4. Миграции Django применяются автоматически при запуске контейнеров api и web через docker-entrypoint.sh

5. Создайте суперпользователя (опционально):
```bash
docker-compose exec api python manage.py createsuperuser
```

## Доступ к сервисам

- **API**: http://localhost:8000/api/
- **API Swagger**: http://localhost:8000/api/swagger/
- **Web интерфейс**: http://localhost:8001/
- **SQL Server**: localhost:1433
  - Пользователь: `sa`
  - Пароль: `YourStrong@Passw0rd`

## Полезные команды

### Просмотр логов
```bash
docker-compose logs -f
```

### Остановка сервисов
```bash
docker-compose down
```

### Остановка с удалением volumes (удалит БД)
```bash
docker-compose down -v
```

### Пересборка образов
```bash
docker-compose build --no-cache
```

### Выполнение команд в контейнере
```bash
docker-compose exec api python manage.py <команда>
docker-compose exec web python manage.py <команда>
```

## Структура

- `Dockerfile` - образ для Django приложения
- `docker-compose.yml` - конфигурация всех сервисов
- `init_db.sql` - SQL скрипт для инициализации БД
- `requirements.txt` - Python зависимости

## Переключение между режимами

Проект автоматически определяет, работает ли он в Docker или локально:
- **Локально**: использует настройки из `settings.py` (KOLYAKApc\SQLEXPRESS, trusted_connection)
- **Docker**: использует переменные окружения из `docker-compose.yml` (db, sa, пароль)

Для локальной разработки просто запускайте `python manage.py runserver` как обычно.
Для Docker используйте `docker-compose up`.

## Примечания

- База данных инициализируется автоматически при первом запуске в Docker
- Данные БД сохраняются в Docker volume `db_data`
- Статические файлы и медиа сохраняются в volumes `static_volume` и `media_volume`
- Для продакшена рекомендуется изменить пароли и настройки безопасности
- Локальная разработка не требует Docker - все работает как раньше

