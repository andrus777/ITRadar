# IT Radar

MVP-сервис для сбора, нормализации и последующего персонального отбора публичных
IT-заказов. На текущем этапе реализован только минимальный каркас приложения и
проверка его работоспособности.

## Требования

- Python 3.12+
- Docker с поддержкой `docker compose`

## Локальный запуск

Создайте виртуальное окружение и установите приложение с инструментами разработки:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Приложение доступно по адресу <http://localhost:8000>. Проверка состояния:

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

## Запуск через Docker Compose

При необходимости скопируйте `.env.example` в `.env` и измените локальные значения,
затем запустите PostgreSQL и приложение:

```bash
docker compose up --build
```

Если порт `8000` занят, задайте другой внешний порт в `.env`, например
`APP_PORT=18000`. Внутри контейнера приложение продолжит слушать порт `8000`.

Проверка состояния приложения:

```bash
curl http://localhost:8000/health
```

Остановка контейнеров без удаления данных PostgreSQL:

```bash
docker compose down
```

## Проверки качества

```bash
pytest
ruff check .
```

Интеграционный тест хранилища требует PostgreSQL и отдельного URL тестовой базы:

```powershell
$env:IT_RADAR_TEST_DATABASE_URL="postgresql+asyncpg://it_radar:it_radar@localhost:5432/it_radar"
pytest -m integration
```

## Миграции базы данных

Контейнер приложения автоматически выполняет `alembic upgrade head` перед запуском
Uvicorn. Для ручного управления миграциями используйте:

```bash
alembic upgrade head
alembic current
alembic downgrade -1
```

## Сборщики

Все источники реализуют единый `CollectorAdapter` с операциями `fetch()` и
`normalize()`. Эталонный `FixtureCollector` читает локальные JSON/HTML-файлы и
позволяет тестировать pipeline без доступа к интернету.

`CollectorService` выполняет полный цикл: создаёт `collection_run`, получает и
сохраняет сырой payload, нормализует карточки, идемпотентно сохраняет opportunities
и завершает run со статистикой. Ошибка отдельной карточки записывается в run и не
прерывает обработку остальных элементов. Транзакцией и вызовом `commit()` управляет
вызывающий слой.

## Конфигурация

Настройки приложения читаются из переменных окружения с префиксом `IT_RADAR_` и
необязательного файла `.env`. Пример доступен в `.env.example`. Секреты и рабочий
`.env` не должны попадать в репозиторий.

## Implemented

- Каркас пакетов для API, сборщиков, AI, matching, базы данных, сервисов, планировщика
  и Telegram-бота.
- Настройки на Pydantic Settings.
- FastAPI endpoint `GET /health`.
- Dockerfile и Docker Compose с PostgreSQL 16.
- Базовые pytest и Ruff.
- Async SQLAlchemy 2.x, asyncpg и Alembic.
- Модели `sources`, `raw_items`, `opportunities`, `collection_runs` с ограничениями
  уникальности и индексами.
- Репозитории и storage service для изоляции SQL от сборщиков и интерфейсов.
- Первая миграция и интеграционный тест идемпотентного сохранения заказа.
- Контракт `CollectorAdapter` и Pydantic-схемы сырых/нормализованных карточек.
- JSON/HTML `FixtureCollector` и `CollectorService` с учётом частичных ошибок.
- Идемпотентные повторные collection runs со статистикой новых записей и ошибок.
