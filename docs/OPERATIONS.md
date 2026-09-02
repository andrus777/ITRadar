# IT Radar: эксплуатация

## Подготовка и запуск

1. Установите Docker с Compose plugin.
2. Скопируйте `.env.example` в `.env` и задайте PostgreSQL password, AI API key,
   Telegram token, profile ID и digest chat ID.
3. Запустите стек:

```powershell
docker compose up -d --build
docker compose ps
```

В стеке работают `db`, `app` и `scheduler`. Данные PostgreSQL находятся в named
volume `postgres_data` и сохраняются при обычных `restart`, `stop` и `down`. Команда
`docker compose down -v` удаляет volume и данные — не используйте её в production.

Проверки состояния:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
docker compose ps
```

`/health` проверяет соединение с БД. `/ready` дополнительно возвращает последний
`collection_run` каждого источника.

## Миграции

При старте API и scheduler автоматически выполняют `alembic upgrade head`. Ручная
проверка и применение:

```powershell
docker compose run --rm app alembic current
docker compose run --rm app alembic check
docker compose run --rm app alembic upgrade head
```

Перед downgrade или крупной миграцией обязательно создайте backup.

## Backup и восстановление PostgreSQL

Создать directory-format backup:

```powershell
cmd /c "docker compose exec -T db pg_dump -U it_radar -d it_radar -Fc > it_radar.dump"
```

Проверить, что файл создан и не пуст:

```powershell
Get-Item .\it_radar.dump
```

Восстановление перезаписывает объекты БД. Сначала остановите API и scheduler и
убедитесь, что выбран правильный backup:

```powershell
docker compose stop app scheduler
cmd /c "docker compose exec -T db pg_restore -U it_radar -d it_radar --clean --if-exists < it_radar.dump"
docker compose start app scheduler
```

Бинарный поток перенаправляется через `cmd.exe`, чтобы PowerShell его не преобразовал.

## Логи и диагностика

Приложение пишет JSON в stdout. Записи collection run содержат `run_id`, `source`,
`status` и `error`, поэтому их можно фильтровать средствами системы сбора логов.

```powershell
docker compose logs -f --tail 200 app scheduler
docker compose logs --since 1h scheduler
docker compose logs scheduler | Select-String '"source":"jobicy"'
docker compose logs scheduler | Select-String '"run_id"'
```

Последние результаты источников также доступны через `/ready`.

## Ручной pipeline

Запустить полный цикл collection → AI → matching → digest:

```powershell
docker compose run --rm scheduler python -m app.scheduler.cli run
```

Запустить только enabled-сборщики:

```powershell
docker compose run --rm scheduler python -m app.collectors.cli all
```

Retry сетевых ошибок ограничивается `IT_RADAR_HTTP_RETRY_ATTEMPTS`; задержка растёт
экспоненциально от `IT_RADAR_HTTP_RETRY_BACKOFF_SECONDS`. После исчерпания попыток
ошибка фиксируется в `collection_runs` и JSON-логах, а pipeline продолжает работу.

## Обновление и перезапуск

```powershell
git pull
docker compose up -d --build
docker compose ps
Invoke-RestMethod http://localhost:8000/ready
```

Перед обновлением создайте backup. Если контейнер перезапущен политикой
`unless-stopped`, проверьте `docker compose logs` и `/ready`, а не удаляйте volume.
