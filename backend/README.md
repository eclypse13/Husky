# НКП Сибирский Хаски - MVP API

Полнофункциональный REST API для Национального клуба породы Сибирский хаски с централизованным контент-справочником, личным кабинетом членов клуба, модулем породного архива и предиктивной аналитикой, а также админ-панелью.

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
- **ML Service Docs (FastAPI Swagger)**: http://localhost:8001/docs

## 🏗️ Архитектура

### Технологии

- **Backend**: Django 5 + Django REST Framework
- **БД (контент)**: MongoDB — справочник текстов, новости, страницы, личный кабинет членов клуба
- **БД (породный архив)**: PostgreSQL — родословные, медицинские данные, выставочные результаты
- **БД (системные данные)**: SQLite — auth, sessions, admin Django
- **ML-сервис**: FastAPI + CatBoost — прогнозирование наследственных рисков вязки
- **Браузерная автоматизация**: Playwright — парсинг Zooportal.pro и browse-страниц BreedArchive
- **Кэш/Очереди**: Redis (брокер Celery + многоуровневый кэш)
- **Фоновые задачи**: Celery + Celery Beat
- **Мониторинг очередей**: Flower
- **Хранилище фотографий**: Яндекс.Диск (REST API)
- **Контейнеризация**: Docker Compose
- **Web-сервер**: Nginx + Gunicorn
- **Frontend**: React 19 + TypeScript + Vite + D3.js + TanStack React Query

### Структура проекта

```
nkp_husky/
├── docker-compose.yml      # Оркестрация сервисов
├── Dockerfile              # Образ Django-приложения
├── Makefile                 # Команды управления
├── requirements.txt         # Python зависимости
├── .env.example              # Пример конфигурации
├── manage.py                 # Django CLI
├── nkp_project/               # Настройки Django
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   ├── db_routers.py            # Маршрутизация SQLite / PostgreSQL
│   └── wsgi.py
├── core/                          # Контентное приложение (MongoDB)
│   ├── models.py                     # MongoEngine модели
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   ├── urls.py
│   ├── admin.py
│   └── management/commands/seed_data.py
├── dogs_module/                    # Породный архив (PostgreSQL)
│   ├── models.py                       # Dog, Title, MedicalRecord, ShowEvent...
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── repositories/                       # Слой доступа к данным
│   │   ├── dog_repository.py
│   │   ├── medical_record_repository.py
│   │   └── show_repository.py
│   ├── services/                            # Бизнес-логика
│   │   ├── integration.py                       # Слияние Zoo + BA
│   │   ├── duplicate_service.py
│   │   ├── coi_service.py
│   │   ├── ofa_service.py
│   │   ├── show_service.py
│   │   ├── stats_service.py
│   │   ├── ml_client.py
│   │   ├── ml_dog_service.py
│   │   ├── pedigree_service.py
│   │   ├── feature_builder.py
│   │   ├── ancestor_features.py
│   │   ├── dataset_builder.py
│   │   └── synthetic_generator.py
│   ├── parsers/                              # Транспортный слой внешних источников
│   │   ├── breedarchive.py
│   │   ├── zooportal.py
│   │   ├── zooportal_shows.py
│   │   └── ofa.py
│   ├── domain/                                # Доменная логика
│   │   ├── health_codes.py
│   │   ├── recommendation.py
│   │   └── coi_interpretation.py
│   ├── utils/                                  # Утилиты нормализации
│   │   ├── text.py
│   │   ├── titles.py
│   │   ├── parser_utils.py
│   │   ├── dog_matcher.py
│   │   └── coi_calculator.py
│   ├── tasks/                                   # Celery-задачи
│   │   ├── tasks_zooportal.py
│   │   ├── tasks_breedarchive.py
│   │   ├── tasks_ofa.py
│   │   ├── tasks_shows.py
│   │   ├── tasks_coi.py
│   │   ├── tasks_photos.py
│   │   └── tasks_ml.py
│   └── config/
│       └── matching.py
├── ml_service/                          # ML-микросервис (FastAPI, отдельный контейнер)
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py                       # FEATURE_COLS, TARGETS
│   │   ├── routers/breeding.py
│   │   ├── schemas/breeding.py
│   │   └── services/
│   │       ├── predictor.py
│   │       ├── trainer.py
│   │       └── model_store.py
│   ├── Dockerfile
│   └── requirements.txt
└── celery_tasks/                          # Контентные Celery-задачи (core)
    └── tasks.py
```

## 🗄️ Модели данных

### MongoDB-коллекции (приложение core)

#### Контент-справочник (главная фича!)

**ContentDictionary** - централизованное хранилище всех текстов сайта
- `key` - уникальный ключ (например: `HOME_TITLE`)
- `value` - текст (Markdown/HTML)
- `page` - раздел сайта
- `locale` - язык (по умолчанию `ru`)

Все тексты на сайте подтягиваются из справочника через ключи!

#### Пользователи и роли

**User** - пользователи системы
- Роли: `admin_roles`, `section_admin`, `presidium`, `member_physical`, `member_legal`
- Членство в НКП: `is_nkp_member`, `membership_type`
- Профиль: phone, city, avatar

#### Публичный контент

- **News** - новости клуба
- **Page** - CMS страницы
- **Gallery** - фотогалереи
- **Event** - мероприятия и выставки
- **EventReport** - отчеты о мероприятиях
- **Judge** - судьи; детализированный профиль вынесен в отдельную модель **JudgeDetails**
- **Seminar** - семинары

#### О клубе

- **ClubDocument** - документы (устав, положения)
- **BoardMember** - члены Президиума
- **MembershipPlan** - планы членства
- **FastLink** - быстрые ссылки главной страницы

#### О породе

- **BreedStandard** - стандарты FCI
- **BreedArticle** - статьи о породе

#### Ездовой спорт

- **Season** - спортивный сезон
- **Race** - гонка

#### Президент клуба

- **President** - президент клуба
- **PresidentBadge** - бейджи президента
- **PresidentAchievement** - достижения президента

#### Личный кабинет

- **Kennel** - питомники
- **Application** - заявления членов
- **MembershipPayment** - история взносов

#### Преференции

- **MemberBenefit** - льготы для членов
- **ProtectedMaterial** - закрытые материалы

#### Системные

- **ContentRevision** - история изменений контента
- **SiteMonitor** - мониторинг сайтов питомников
- **AuditLog** - журнал аудита

---

### PostgreSQL-таблицы (приложение dogs_module)

Маршрутизация между SQLite и PostgreSQL выполняется через `DogsRouter` (`nkp_project/db_routers.py`): все модели `dogs_module` автоматически направляются в базу `dogs_db`, остальные — в `default` (SQLite).

#### Породный архив

**Dog** - центральная сущность модуля
- Генеалогия: `sire`, `dam` (self-FK, `on_delete=SET_NULL`) — родословная произвольной глубины через рекурсивную самосвязь
- Внешние идентификаторы: `uuid` (BreedArchive), `zooportal_id`, `ofa_appnum`, `zoo_hash` (SHA-256 для дедупликации)
- Денормализованные поля: `sire_name`, `dam_name` — для случаев, когда родительская запись ещё не импортирована
- Здоровье: `coi`, `coi_updated_on`, `health_info_general`, `health_info_genetic` (JSON)
- Аудит дедупликации: `conflicts` (JSON), `has_conflicts` (bool)
- Индексы: по `uuid`, `zooportal_id`, `zoo_hash`, составной `(sex, year_of_birth)`

**Breeder / Owner** - заводчики и владельцы (M2M через `DogBreederLink` / `DogOwnerLink`)

**Title** - выставочные титулы (`short_name`, `country`, `is_prefix`, `winner_year`); unique по `(dog, short_name, country)`

**MedicalRecord** - структурированные результаты тестов OFA; unique по `(dog, ofa_number)` при непустом номере

**MergeLog** - журнал слияния дубликатов (resolved_fields, old/new values, conflicts)

#### Выставочный учёт

**ShowEvent** - мероприятие: `zooportal_show_id` (unique), `show_type` (ПК / КЧК / специализированная / спорт / World/Euro Dog Show / без рейтинга), `multiplier`

**ShowResult** - результат участника: `grade`, `place`, `titles_won`, `rating_points`, `catalog_count`; unique по `(event, dog)`; `dog` со стратегией `SET_NULL`

## 🔌 API Endpoints

### Аутентификация

```
POST   /api/auth/login/      # Вход
POST   /api/auth/logout/     # Выход
GET    /api/me/              # Профиль
PUT    /api/me/profile/      # Обновление профиля
```

### Публичные API (контент)

```
GET    /api/home/                    # Главная страница
GET    /api/dogs/hero/               # Собака-звезда для hero-карточки на главной странице
GET    /api/dict/                    # Контент-справочник
GET    /api/dict/by_key/?key=...     # Получить по ключу
GET    /api/news/                    # Новости
GET    /api/pages/{slug}/            # Страница по slug
GET    /api/galleries/               # Галереи
GET    /api/galleries/highlights/    # Избранные
GET    /api/events/                  # Мероприятия
GET    /api/event-reports/           # Отчеты
GET    /api/judges/                  # Судьи
GET    /api/judge-details/           # Детализированные профили судей
GET    /api/club/documents/          # Документы клуба
GET    /api/club/board/              # Президиум
GET    /api/club/stats/              # Статистика клуба
GET    /api/breed/standards/         # Стандарты породы
GET    /api/breed/articles/          # Статьи о породе
GET    /api/sports-seasons/          # Спортивные сезоны
GET    /api/sports-races/            # Гонки ездового спорта
GET    /api/sports-races/{id}/results/  # Результаты конкретной гонки (из JSON-файла)
GET    /api/president/active/        # Действующий президент клуба
GET    /api/activity-feed/           # Лента активности (Telegram-новости)
GET    /api/site-banner/             # Настройки баннера сайта
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

### Породный архив (dogs_module) — публичные

```
GET    /api/dogs/                                   # Список собак (поиск, фильтры, пагинация)
GET    /api/dogs/{id}/                               # Профиль собаки
GET    /api/dogs/{id}/pedigree/                       # Родословное дерево
POST   /api/dogs/{id}/calculate_coi/                   # Расчёт коэффициента инбридинга
GET    /api/breeders/                                   # Заводчики
GET    /api/owners/                                      # Владельцы
GET    /api/titles/                                       # Титулы
GET    /api/medical-records/                                 # Медицинские записи
GET    /api/shows/                                             # Выставочные мероприятия
GET    /api/dogs/stats/population/                                # Популяционная аналитика
```

### Импорт данных (BreedArchive)

```
POST   /api/dogs/import/breedarchive/dog/                  # Импорт одной собаки (5 поколений)
POST   /api/dogs/import/breedarchive/dog/full-pedigree/       # Полное дерево предков
POST   /api/dogs/import/breedarchive/recent/                     # Последние обновления
POST   /api/dogs/import/breedarchive/browse/                       # Обход browse-страницы (Playwright)
```

### Импорт данных (Zooportal.pro)

```
POST   /api/dogs/import/zooportal/dog/             # Импорт одной собаки
POST   /api/dogs/import/zooportal/page/              # Импорт страницы листинга
POST   /api/dogs/import/zooportal/range/               # Импорт диапазона страниц
```

### Гибридный импорт (Zoo + BreedArchive)

```
POST   /api/dogs/import/hybrid/dog/
POST   /api/dogs/import/hybrid/full/dog/                # + полная глубина родословной BA
POST   /api/dogs/import/hybrid/full/page/
POST   /api/dogs/import/hybrid/full/range/
```

### Медицинские данные (OFA)

```
POST   /api/dogs/import/ofa/dog/                  # Импорт по одной собаке
POST   /api/dogs/import/ofa/bulk/reg/                # Пакетный импорт по рег. номеру
POST   /api/dogs/import/ofa/bulk/name/                 # Пакетный импорт по имени
POST   /api/dogs/import/ofa/abnormal/                    # Импорт аномальных случаев + предки
POST   /api/dogs/import/ofa/crawl/                          # Обход от известного appnum
GET    /api/dogs/import/ofa/stats/siberian-husky/            # Агрегированная статистика породы
GET    /api/dogs/health/search/                                 # Поиск медицинских тестов
GET    /api/dogs/health/registries/                              # Список реестров
GET    /api/dogs/health/stats/                                    # Статистика по тестам
GET    /api/dogs/health/records/                                    # Записи конкретной собаки
```

### Коэффициент инбридинга и прогнозирование вязки

```
POST   /api/dogs/coi/recalculate/         # Массовый пересчёт COI
POST   /api/dogs/breeding/predict/          # Прогноз рисков для пары (ML + правила)
```

### Выставки и породный рейтинг

```
POST   /api/dogs/import/shows/list/                  # Импорт списка мероприятий за дату
POST   /api/dogs/import/shows/results/                  # Импорт результатов мероприятия
POST   /api/dogs/import/shows/range/                      # Импорт диапазона дат
POST   /api/dogs/import/shows/full/                          # Полный конвейер импорта
POST   /api/dogs/import/shows/results/range/                   # Импорт результатов за период
POST   /api/dogs/shows/recalculate-ratings/                       # Пересчёт рейтинга
POST   /api/dogs/shows/link-results/                                 # Разрешение ожидающих результатов
```

### Фотографии (Яндекс.Диск)

```
GET    /api/dogs/photos/stats/                              # Статистика хранилища
POST   /api/dogs/photos/upload/bulk/                           # Пакетная загрузка BA (из БД)
POST   /api/dogs/photos/upload/{dog_id}/                          # Загрузка для одной собаки
POST   /api/dogs/photos/sync-from-yadisk/                            # Обратная синхронизация
POST   /api/dogs/photos/fetch-zoo/{dog_id}/                             # Загрузка фото Zoo (Playwright)
POST   /api/dogs/photos/fetch-zoo/bulk/
DELETE /api/dogs/photos/delete/{dog_id}/
POST   /api/dogs/photos/backfill-hashes/                                   # Заполнение хэшей (исторические данные)
POST   /api/dogs/photos/backfill-hashes-from-source/
POST   /api/dogs/photos/cleanup-placeholders/                                 # Очистка заглушек
```

### Telegram-бот

Автоматическая агрегация новостей из Telegram-канала клуба (`pyTelegramBotAPI`), публикация в ленту активности сайта (`/api/activity-feed/`) через общий файловый том между контейнерами `web` и `telegram_bot`.

### Мониторинг фоновых задач

```
GET    /api/dogs/import/status/{task_id}/    # Статус Celery-задачи
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

### Собаки
```
GET /api/dogs/?sex=1&q=Storm&per_page=8
```

### Породный рейтинг
```
GET /api/dogs/rating/?nomination=main&year=2026
```
Номинации: `main`, `junior`, `veteran`, `working`.

## 🔐 Роли и права доступа

### Роли пользователей

1. **admin_roles** - Администратор ролей (управление пользователями)
2. **section_admin** - Администратор раздела (управление контентом)
3. **presidium** - Член Президиума НКП
4. **member_physical** - Член НКП (физ. лицо)
5. **member_legal** - Член НКП (юр. лицо/клуб)

### Права доступа

- **Публичные API** - доступны всем (включая `/api/dogs/`, родословные, аналитику и рейтинг)
- **Личный кабинет** - только авторизованным
- **Закрытые материалы** - только членам НКП (`is_nkp_member=True`)
- **Импорт/обучение ML-моделей** - только администраторам
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

## 🐕 Модуль породного архива (dogs_module)

### Интеграция с внешними источниками

Сбор данных реализован тремя независимыми парсерами, инкапсулирующими взаимодействие с конкретной платформой:

- **BreedArchive** — структурированный REST API (`httpx`), дерево предков с заданной глубиной, дополнительно browse-страница через Playwright
- **Zooportal.pro** — полностью динамический SPA, требует Playwright (headless Chromium) с ожиданием `networkidle`; защита от хотлинкинга фотографий обходится в рамках авторизованной сессии браузера
- **OFA** — гибридная модель: HTTP-сессия с cookie, поиск через POST, медицинские данные через CSV-экспорт (избегает блокировки за серийный скрейпинг страниц)

Промежуточное кэширование результатов парсинга — Redis (отдельная логическая БД `parsers`).

### Нормализация и дедупликация

- Унификация имён, дат, окрасов, пола, регистрационных номеров и кодов стран
- Снятие титульных аффиксов (пробельный и точечный форматы: `CH`, `JCH.RUS`, `GrCH.RKF`)
- Поиск дублей: блокировка по полу/году + сходство имён по алгоритму Яро — Винклера (`rapidfuzz`, с fallback на чистый Python)
- Три вердикта: `merge` (автослияние с записью в `MergeLog`), `flag` (ручная верификация), `different`

### Коэффициент инбридинга (COI)

Метод путей Райта (формула Фалюса), BFS-обход предков с пакетной загрузкой по поколениям — O(N) запросов вместо O(2^N). Глубина 1–10 поколений (стандарт FCI — 5).

### Породный рейтинг

Очки за титулы × весовой коэффициент типа выставки (ПК / КЧК / специализированная / World·Euro Dog Show) + бонус за BOB. Расчётный период: 1 декабря — 30 ноября. Четыре номинации: основная, юниоры, ветераны, рабочая.

### Популяционная аналитика

Единый кэшируемый (Redis, TTL 6 ч) эндпоинт: общая сводка, распределение по полу/году/стране/окрасу, топ питомников и производителей, гистограмма COI по 6 диапазонам, полнота заполнения данных.

### Фотографии (Яндекс.Диск)

Дедупликация по SHA-256-хэшу содержимого файла, фильтрация заглушек, двухшаговая публикация с получением пути в хранилище, обратная синхронизация при рассинхроне БД ↔ хранилище.

### ML-сервис прогнозирования наследственных рисков

Независимый микросервис FastAPI + CatBoost (контейнер `ml_service`)

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
web                 # Django + Gunicorn (порт 8000)
mongodb              # MongoDB (порт 27017) — контент
postgres              # PostgreSQL (порт 5433) — dogs_module
redis                  # Redis (порт 6379) — брокер + кэш
celery                   # Celery worker: queues=celery,ofa,ba,coi,photos (concurrency=4)
celery-playwright          # Celery worker: queue=playwright (concurrency=1, строго 1 браузер)
celery_beat                  # Celery scheduler
flower                         # Мониторинг очередей (порт 5555)
nginx                            # Nginx (порт 80) — статика + проксирование API
nginx-proxy                        # Обратный прокси + автогенерация конфигурации
acme-companion                        # Автоматический выпуск/обновление SSL (Let's Encrypt)
telegram_bot                            # Telegram-бот клуба
ml_service                                # FastAPI + CatBoost (порт 8001) — прогнозирование вязки
```

## 🔄 Celery задачи

Фоновые задачи разделены по специализированным очередям между двумя воркерами.

### Основной воркер (`celery`, concurrency=3)

| Очередь  | Назначение |
|----------|-----------|
| `celery` | Диспетчеры импорта, ML-обучение/инференс, контентные задачи |
| `ofa`    | HTTP-взаимодействие с реестром OFA |
| `ba`     | HTTP/REST к BreedArchive (включая browse через Playwright — антибот не требуется) |
| `coi`    | Вычислительно интенсивный пересчёт коэффициента инбридинга |
| `photos` | Загрузка/синхронизация фотографий на Яндекс.Диск |

### Воркер для загрузки медиа (фото с Яндекс.Диск) (`celery-photos`, concurrency=1)

| Очередь  | Назначение |
|----------|-----------|
| `photos` | Загрузка/синхронизация фотографий на Яндекс.Диск |

### Playwright-воркер (`celery-playwright`, concurrency=1)

| Очередь      | Назначение |
|--------------|-----------|
| `playwright` | Браузерная автоматизация Zooportal.pro — строго 1 процесс, иначе блокировка по IP |

### Периодические задачи (Celery Beat) (постоянные)
- **monitor_kennel_sites** — мониторинг сайтов питомников (каждый день в 2:00)
- **send_event_reminders** — напоминания о мероприятиях (понедельник в 10:00)
- **refresh_cookies** — обновление сессионных cookie BA/Zoo (каждые 20 часов)

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
- ✅ Session-based аутентификация (+ Token для API-интеграций)
- ✅ Валидация загружаемых файлов
- ✅ Журнал аудита (AuditLog)
- ✅ CORS настройки
- ✅ Принцип «лучше пропуск, чем ошибочное соответствие» при сопоставлении медицинских данных OFA

## 📝 Переменные окружения (.env)

```bash
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# MongoDB (контент)
MONGODB_HOST=mongodb
MONGODB_NAME=nkp_husky

# PostgreSQL (dogs_module)
DOGS_DB_NAME=dogs_db
DOGS_DB_USER=dogs_user
DOGS_DB_PASSWORD=your-password
DOGS_DB_HOST=postgres
DOGS_DB_PORT=5432

# Redis
REDIS_HOST=redis

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ML-сервис
ML_SERVICE_URL=http://ml_service:8001

# Яндекс.Диск
YANDEX_DISK_TOKEN=your-oauth-token

# BreedArchive / Zooportal (сессионные данные парсеров)
BA_LOGIN=your-login
BA_PASSWORD=your-password
ZOO_LOGIN=your-login
ZOO_PASSWORD=your-password

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password
```

## 🚀 Деплой в production

1. Изменить `DEBUG=False` в .env
2. Установить надежный `SECRET_KEY`
3. Настроить `ALLOWED_HOSTS`
4. SQLite используется только для auth/sessions/admin Django; PostgreSQL уже применяется как промышленная СУБД для dogs_module
5. Настроить SSL сертификаты в nginx (автоматизировано через acme-companion)
6. Объём хранилища Яндекс.Диска контролировать через `/api/dogs/photos/stats/`
7. Регулярные бэкапы MongoDB и PostgreSQL
8. Переобучение ML-моделей по мере накопления реальных медицинских данных (`/api/dogs/coi/recalculate/`, `train_ml_model_task`)

## 📊 Мониторинг и логи

```bash
# Логи приложения
docker-compose logs -f web

# Логи Celery (основной воркер)
docker-compose logs -f celery

# Логи Celery (celery-photos воркер)
docker-compose logs -f celery-photos

# Логи Playwright-воркера
docker-compose logs -f celery-playwright

# Логи ML-сервиса
docker-compose logs -f ml_service

# Логи MongoDB / PostgreSQL
docker-compose logs -f mongodb
docker-compose logs -f postgres

# Подключение к MongoDB
docker-compose exec mongodb mongosh nkp_husky

# Подключение к PostgreSQL
docker-compose exec postgres psql -U dogs_user -d dogs_db

# Мониторинг очередей Celery
# http://localhost:5555 (Flower)
```

## 🧩 Расширение функционала

### Добавление нового раздела (контент, MongoDB)

1. Создать модель в `core/models.py`
2. Создать сериализатор в `core/serializers.py`
3. Создать ViewSet в `core/views.py`
4. Добавить роут в `core/urls.py`
5. Добавить ключи в контент-справочник

### Добавление нового источника данных (dogs_module)

1. Создать парсер в `dogs_module/parsers/`
2. Добавить сервисный слой обработки в `dogs_module/services/`
3. Создать Celery-задачу в `dogs_module/tasks/`, назначить очередь в `CELERY_TASK_ROUTES` (settings.py)
4. Добавить маршрут в `dogs_module/urls.py`

### Добавление новой нозологии в ML-модуль

1. Добавить группу в `dogs_module/domain/health_codes.py` (`REGISTRY_GROUPS`, `GROUP_SCORES`)
2. При наличии достаточного объёма реальных данных — добавить цель в `ml_service/app/config.py` (`TARGETS`)
3. Иначе — добавить rule-based таблицу риска в `ml_service/app/services/predictor.py`

### Добавление фоновой задачи

1. Создать задачу в `celery_tasks/tasks.py` (контент) или `dogs_module/tasks/` (породный архив)
2. Добавить расписание в `nkp_project/celery.py`
3. При необходимости — назначить специализированную очередь в `CELERY_TASK_ROUTES`

## 🎨 Фронтенд интеграция

Разработан клиент на React + TypeScript (Vite)

API готов для подключения и любого другого фронтенда:
- Vue.js
- Angular
- Next.js
- Mobile apps (iOS/Android)

Все тексты можно получить через `/api/dict/`, все данные породного архива — через `/api/dogs/`.

## 📄 Лицензия

MIT License

## 👥 Контакты

- Email: sherba.ru@icloud.com
- Telegram: @KreoManser