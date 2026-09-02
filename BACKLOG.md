# IT Radar backlog после MVP v0.1.0

Приоритеты будут уточняться по результатам использования MVP первыми тестовыми
пользователями. Ниже — продуктовые направления, а не обещанный порядок релизов.

## Web UI

- Лента возможностей с фильтрами, поиском, сортировкой и сохранёнными представлениями.
- Редактор профиля и весов matching без доступа к серверной конфигурации.
- Просмотр raw/normalized/AI данных и объяснений score.
- Административная панель источников, runs, ошибок и ручных перезапусков.
- Responsive интерфейс и доступность.

## Multi-user onboarding

- Telegram onboarding с пошаговым созданием индивидуального профиля.
- Регистрация через web, привязка Telegram и управление несколькими профилями.
- Персональные timezone, расписание, порог score и язык.
- Команды pause/resume, feedback и скрытие нерелевантных заказов.
- Импорт навыков из резюме/профиля с явным подтверждением пользователя.

## Payments

- Тарифы Free/Pro/Team и feature entitlements.
- Интеграция платёжного провайдера, invoices, refunds и webhook reconciliation.
- Trial, лимиты источников/AI/digest и grace period.
- Учёт налогов, валют и юридических требований целевых рынков.

## Analytics

- Воронка collect → classify → match → delivered → opened → applied.
- Качество источников, precision matching и пользовательский feedback loop.
- Стоимость AI на заказ/источник/пользователя и budget alerts.
- Cohort retention, digest engagement и A/B-тесты весов matching.
- Privacy-aware product analytics и сроки хранения событий.

## Additional sources

- Новые официальные API/RSS источники с review условий использования.
- Source health score, schema-change detection и quarantining сломанных адаптеров.
- Incremental cursors/ETag/Last-Modified вместо полного опроса.
- Нормализация валют через версионированные курсы.
- Расширенная entity resolution заказчиков и cross-source дедупликация.

## Notifications

- Email, Slack, Teams, web push и webhook delivery.
- Transactional outbox, delivery attempts, dead-letter queue и replay.
- Digest grouping, quiet hours, realtime high-score alerts и weekly summary.
- Пользовательские шаблоны и локализация сообщений.
- Tracking открытия/перехода только с явным согласием.

## SaaS security

- Tenant isolation на уровне данных, authorization policies и security tests.
- SSO/OIDC, MFA, RBAC и service accounts.
- Secret manager вместо env-файлов, rotation и short-lived credentials.
- Encryption in transit/at rest, audit log и tamper-resistant events.
- Rate limiting, abuse prevention, dependency/container scanning и signed images.
- Backups с регулярным restore drill, RPO/RTO и disaster recovery plan.
- GDPR/data export/deletion, retention policies и vendor risk review.
- Threat model, incident response runbook и независимый security review.
