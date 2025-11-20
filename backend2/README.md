# НКП Сибирский Хаски - MVP API

Полнофункциональный REST API для Национального клуба породы Сибирский хаски с централизованным контент-справочником, личным кабинетом членов клуба и админ-панелью.

## 🚀 Быстрый старт

```bash
# 1. Запустить все сервисы
make up

# 2. Создать суперпользователя (опционально, если сиды не загружены) #TODO: Не работает
make superuser

# 3. Загрузить тестовые данные
make seed
```

API будет доступен по адресу: **http://localhost:8000/api/**

## 📚 Документация API

- **Swagger UI**: http://localhost:8000/api/schema/swagger-ui/
- **ReDoc**: http://localhost:8000/api/schema/redoc/
- **OpenAPI Schema - Скачать файл**: http://localhost:8000/api/schema/

## 🏗️ Архитектура

### Технологии

- **Backend**: Django 5 + Django REST Framework
- **БД**: MongoDB
- **Кэш/Очереди**: Redis
- **Фоновые задачи (оповещения и тд..)**: Celery + Celery Beat
- **Контейнеризация**: Docker Compose
- **Web-сервер**: Nginx + Gunicorn

### Структура проекта

```
nkp_husky/
├── docker-compose.yml      # Оркестрация сервисов
├── Dockerfile             # Образ приложения
├── Makefile              # Команды управления
├── requirements.txt      # Python зависимости
├── .env.example         # Пример конфигурации
├── manage.py           # Django CLI
├── nkp_project/       # Настройки Django
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── core/             # Основное приложение
│   ├── models.py          # MongoEngine модели
│   ├── serializers.py     # DRF сериализаторы
│   ├── views.py          # API endpoints
│   ├── permissions.py    # Права доступа
│   ├── urls.py
│   ├── admin.py
│   └── management/
│       └── commands/
│           └── seed_data.py  # Тестовые данные
└── celery_tasks/    # Celery задачи
    └── tasks.py
```

## 🗄️ Модели данных (MongoDB коллекции)

### Контент-справочник (главная фича!)

**ContentDictionary** - централизованное хранилище всех текстов сайта
- `key` - уникальный ключ (например: `HOME_TITLE`)
- `value` - текст (Markdown/HTML)
- `page` - раздел сайта
- `locale` - язык (по умолчанию `ru`)

Все тексты на сайте подтягиваются из справочника через ключи!

### Пользователи и роли

**User** - пользователи системы
- Роли: `admin_roles`, `section_admin`, `presidium`, `member_physical`, `member_legal`
- Членство в НКП: `is_nkp_member`, `membership_type`
- Профиль: phone, city, avatar

### Публичный контент

- **News** - новости клуба
- **Page** - CMS страницы
- **Gallery** - фотогалереи
- **Event** - мероприятия и выставки
- **EventReport** - отчеты о мероприятиях
- **Judge** - судьи
- **Seminar** - семинары

### О клубе

- **ClubDocument** - документы (устав, положения)
- **BoardMember** - члены Президиума
- **MembershipPlan** - планы членства

### О породе

- **BreedStandard** - стандарты FCI
- **BreedArticle** - статьи о породе

### Личный кабинет

- **Kennel** - питомники
- **Dog** - собаки
- **Litter** - пометы
- **Application** - заявления членов
- **Achievement** - достижения на выставках
- **MembershipPayment** - история взносов

### Преференции

- **MemberBenefit** - льготы для членов
- **ProtectedMaterial** - закрытые материалы

### Системные

- **ContentRevision** - история изменений контента
- **SiteMonitor** - мониторинг сайтов питомников
- **AuditLog** - журнал аудита

## 🔌 API Endpoints

### Аутентификация

```
POST   /api/auth/login/      # Вход
POST   /api/auth/logout/     # Выход
GET    /api/me/              # Профиль
PUT    /api/me/profile/      # Обновление профиля
```

### Публичные API

```
GET    /api/home/                    # Главная страница
GET    /api/dict/                    # Контент-справочник
GET    /api/dict/by_key/?key=...    # Получить по ключу
GET    /api/news/                    # Новости
GET    /api/pages/{slug}/            # Страница по slug
GET    /api/galleries/               # Галереи
GET    /api/galleries/highlights/    # Избранные
GET    /api/events/                  # Мероприятия
GET    /api/event-reports/           # Отчеты
GET    /api/judges/                  # Судьи
GET    /api/club/documents/          # Документы клуба
GET    /api/club/board/              # Президиум
GET    /api/breed/standards/         # Стандарты породы
GET    /api/breed/articles/          # Статьи о породе
```

### Личный кабинет (требует авторизации)

```
GET    /api/me/dogs/              # Мои собаки
POST   /api/me/dogs/              # Добавить собаку
GET    /api/me/dogs/champions/    # Чемпионы
GET    /api/me/kennels/           # Мои питомники
POST   /api/me/kennels/           # Добавить питомник
GET    /api/me/litters/           # Мои пометы
POST   /api/me/litters/           # Анонсировать помет
GET    /api/me/applications/      # Мои заявления
POST   /api/me/applications/      # Подать заявление
GET    /api/me/achievements/      # Мои достижения
```

## 🎯 Фильтры и параметры

### Новости
```
GET /api/news/?featured=true&tag=выставки
```

### События
```
GET /api/events/?from_date=2025-01-01&to_date=2025-12-31&type=exhibition
```

### Контент-справочник
```
GET /api/dict/?page=home
GET /api/dict/?key=TITLE
```

### Статьи о породе
```
GET /api/breed/articles/?category=history
```

## 🔐 Роли и права доступа

### Роли пользователей

1. **admin_roles** - Администратор ролей (управление пользователями)
2. **section_admin** - Администратор раздела (управление контентом)
3. **presidium** - Член Президиума НКП
4. **member_physical** - Член НКП (физ. лицо)
5. **member_legal** - Член НКП (юр. лицо/клуб)

### Права доступа

- **Публичные API** - доступны всем
- **Личный кабинет** - только авторизованным
- **Закрытые материалы** - только членам НКП (`is_nkp_member=True`)
- **Админ-панель** - только администраторам

## 💾 Контент-справочник - как редактировать тексты

### Ключевая идея

**Все тексты на сайте хранятся в одной коллекции** `ContentDictionary` и подтягиваются по ключам!

### Примеры ключей

```python
LOGO_TEXT = "НКП СХ"
HOME_TITLE = "Добро пожаловать в НКП Сибирский Хаски"
HOME_SUBTITLE = "Объединяем любителей породы"
FOOTER_EMAIL = "info@nkp-husky.ru"
CLUB_HISTORY = "История создания клуба..."
```

### Редактирование через API

```bash
# Получить все тексты главной страницы
GET /api/dict/?page=home

# Получить конкретный текст
GET /api/dict/by_key/?key=HOME_TITLE

# В админке: изменить value для ключа HOME_TITLE
# → текст на сайте изменится автоматически!
```

### Преимущества

- ✅ Менять текст без правки кода
- ✅ История изменений (ContentRevision)
- ✅ Поиск и массовое редактирование
- ✅ Поддержка локализации

## 🔧 Makefile команды

```bash
make up          # Запустить все сервисы
make down        # Остановить сервисы
make restart     # Перезапустить
make logs        # Показать логи
make shell       # Django shell
make superuser   # Создать суперпользователя
make seed        # Загрузить тестовые данные
make test        # Запустить тесты
make clean       # Очистить volumes
```

## 📦 Docker сервисы

```yaml
web          # Django + Gunicorn (порт 8000)
mongodb      # MongoDB (порт 27017)
redis        # Redis (порт 6379)
celery       # Celery worker
celery_beat  # Celery scheduler
nginx        # Nginx (порт 80)
```

## 🔄 Celery задачи

### Периодические задачи

- **monitor_kennel_sites** - мониторинг сайтов питомников (каждый день в 2:00)
- **send_event_reminders** - напоминания о мероприятиях (понедельник в 10:00)

### Асинхронные задачи

- **send_email_task** - отправка email

## 🧪 Тестовые данные

После выполнения `make seed` создаются:

- **Django admin**: `admin@example.com` / `admin123`
- **Член НКП**: `member@example.com`
- **50+ записей** в контент-справочнике
- **3 новости** (2 избранные)
- **2 галереи** (избранные для главной)
- **3 мероприятия** (предстоящие)
- **2 отчета** о мероприятиях
- **1 судья**
- **1 семинар**
- **3 документа** клуба
- **1 член Президиума**
- **1 стандарт породы FCI**
- **1 статья** о породе

## 🔒 Безопасность

- ✅ CSRF защита для форм
- ✅ Rate limiting (100 req/hour для анонимов, 1000 для пользователей)
- ✅ Session-based аутентификация
- ✅ Валидация загружаемых файлов
- ✅ Журнал аудита (AuditLog)
- ✅ CORS настройки

## 📝 Переменные окружения (.env)

```bash
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# MongoDB
MONGODB_HOST=mongodb
MONGODB_NAME=nkp_husky

# Redis
REDIS_HOST=redis

# Celery
CELERY_BROKER_URL=redis://redis:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password
```

## 🚀 Деплой в production

1. Изменить `DEBUG=False` в .env
2. Установить надежный `SECRET_KEY`
3. Настроить `ALLOWED_HOSTS`
4. Использовать PostgreSQL для Django auth (вместо SQLite)
5. Настроить SSL сертификаты в nginx
6. Настроить S3 для медиа-файлов
7. Регулярные бэкапы MongoDB (?)

## 📊 Мониторинг и логи

```bash
# Логи приложения
docker-compose logs -f web

# Логи Celery
docker-compose logs -f celery

# Логи MongoDB
docker-compose logs -f mongodb

# Подключение к MongoDB
docker-compose exec mongodb mongosh nkp_husky
```

## 🧩 Расширение функционала

### Добавление нового раздела

1. Создать модель в `core/models.py`
2. Создать сериализатор в `core/serializers.py`
3. Создать ViewSet в `core/views.py`
4. Добавить роут в `core/urls.py`
5. Добавить ключи в контент-справочник

### Добавление фоновой задачи

1. Создать задачу в `celery_tasks/tasks.py`
2. Добавить расписание в `nkp_project/celery.py`

## 🎨 Фронтенд интеграция

API готов для подключения любого фронтенда:
- React
- Vue.js
- Angular
- Next.js
- Mobile apps (iOS/Android)

Все тексты можно получить через `/api/dict/`

## 📄 Лицензия

MIT License

## 👥 Контакты

- Email: sherba.ru@icloud.com
- Telegram: @KreoManser