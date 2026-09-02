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

### Нормализация и дедупликация

Перед сохранением общий слой очищает HTML и пробелы, канонизирует URL (включая
удаление tracking-параметров), приводит валюты к ISO-кодам и разбирает бюджетные
диапазоны. Fingerprint строится по нормализованным заголовку и описанию без бюджета,
поэтому изменение цены не создаёт новую каноническую карточку.

Cross-source дубли ищутся консервативно: сначала по canonical URL, затем по точному
fingerprint, затем по очень высокой схожести заголовка при обязательной высокой
схожести описания. Одинакового заголовка самого по себе недостаточно. Все source-записи
сохраняются; дубль получает `duplicate_of_id`, указывающий на первую каноническую
opportunity. Для пользовательской выдачи следует выбирать записи с
`duplicate_of_id IS NULL`.

### Первый публичный источник: Jobicy

Первым реальным источником выбран [Jobicy Public Jobs API](https://jobicy.com/jobs-rss-feed).
Это официальный read-only JSON endpoint `https://jobicy.com/api/v2/remote-jobs`, который
не требует регистрации или API-ключа и возвращает стабильный `id`, канонический URL,
название, HTML-описание, дату публикации и зарплатные поля. Источник охватывает
удалённые вакансии и контрактные возможности; это пилотный источник для проверки
pipeline, а не специализированная фриланс-биржа.

Правила использования Jobicy требуют сохранять атрибуцию и каноническую ссылку,
не выдавать объявления за собственные и не выполнять автоматический опрос чаще
одного раза в час. IT Radar сохраняет исходный Jobicy URL; планировщик с частым
опросом в текущем задании не реализуется.

Ручной запуск после старта PostgreSQL и применения миграций:

```powershell
python -m app.collectors.cli jobicy --count 20 --tag python
```

Доступны также фильтры `--geo` и `--industry`. CLI выводит JSON со статусом run,
числом полученных и новых карточек и возможной частичной ошибкой.

### Дополнительные публичные источники

- [Remote OK](https://remoteok.com/api) — официальный публичный JSON feed без
  авторизации. При отображении записи необходимо указывать Remote OK и сохранять
  прямую follow-ссылку на исходную карточку.
- [We Work Remotely](https://weworkremotely.com/remote-job-rss-feed) — официальный
  публичный RSS. Используется programming feed; WWR просит указывать источник и
  оставлять ссылку на исходное объявление.

Оба источника используют тот же `CollectorAdapter` и проходят через общий
`CollectorService`, нормализацию и cross-source дедупликацию. Ручной запуск:

```powershell
python -m app.collectors.cli remoteok --count 20 --tag python
python -m app.collectors.cli weworkremotely --count 20
python -m app.collectors.cli all
```

Команда `all` запускает только включённые источники. Доступность и сетевые таймауты
настраиваются без изменения кода:

```dotenv
IT_RADAR_JOBICY_ENABLED=true
IT_RADAR_JOBICY_TIMEOUT_SECONDS=30
IT_RADAR_REMOTEOK_ENABLED=true
IT_RADAR_REMOTEOK_TIMEOUT_SECONDS=30
IT_RADAR_WEWORKREMOTELY_ENABLED=true
IT_RADAR_WEWORKREMOTELY_TIMEOUT_SECONDS=30
```

Каждый запуск создаёт отдельную строку `collection_runs`, связанную с конкретным
`source_id`, и сохраняет `status`, `fetched_count`, `new_count` и `error`. CLI также
возвращает эту статистику отдельно для каждого источника.

## AI-классификация

`AIClassifierService` принимает любую реализацию протокола `AIProvider`. Первая
реализация `OpenAICompatibleProvider` использует Responses API и строгий JSON Schema;
`MockAIProvider` позволяет полностью тестировать pipeline без сети и API-ключа.

Перед вызовом провайдера сервис вычисляет hash значимых полей заказа. Уже сохранённая
попытка с теми же заказом, `prompt_version` и hash повторно в AI не отправляется.
Успешный структурированный ответ и неуспешная попытка сохраняются в `ai_analyses` с
моделью, версией prompt и временем анализа. Ошибка провайдера или невалидный JSON
помечает только текущую запись как `failed` и не останавливает пакет.

Настройки OpenAI-compatible endpoint задаются через окружение:

```dotenv
IT_RADAR_AI_API_KEY=
IT_RADAR_AI_BASE_URL=https://api.openai.com/v1
IT_RADAR_AI_MODEL=gpt-5-mini
IT_RADAR_AI_PROMPT_VERSION=v1
IT_RADAR_AI_TIMEOUT_SECONDS=60
```

API-ключ не обязателен для тестов и не должен сохраняться в репозитории.

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
- Адаптер официального Jobicy Public Jobs API и CLI для ручного импорта.
- Нормализация Jobicy ID, заголовка, HTML-описания, даты, ссылки и salary/budget text.
- Обезличенный снимок структуры ответа Jobicy и parser-тесты необязательных полей.
- Общая нормализация HTML, пробелов, URL, валют и бюджетных диапазонов.
- Cross-source дедупликация по URL, fingerprint и консервативной схожести текста.
- Связь `duplicate_of_id`, сохраняющая исходные записи каждого источника.
- Адаптеры Remote OK JSON и We Work Remotely RSS без source-specific логики в pipeline.
- Registry источников с env-переключателями enabled/disabled и отдельными таймаутами.
- Команда запуска всех enabled-источников и статистика collection run по каждому из них.
- Абстракция AI-провайдера, OpenAI-compatible Responses API и offline mock-провайдер.
- Строгая схема AI-анализа, версионирование prompt и идемпотентность по hash входа.
- Таблица `ai_analyses`, сохраняющая успешные результаты и изолированные ошибки.
