# Custom WebUI

Русскоязычная сборка и рабочий репозиторий для кастомизации, аудита безопасности и локального деплоя **Open WebUI v0.9.6**.

[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-v0.9.6-111827?style=for-the-badge)](https://github.com/open-webui/open-webui)
[![Frontend](https://img.shields.io/badge/SvelteKit-Svelte%205-ff3e00?style=for-the-badge)](https://svelte.dev/)
[![Backend](https://img.shields.io/badge/FastAPI-Python-009688?style=for-the-badge)](https://fastapi.tiangolo.com/)
[![Deploy](https://img.shields.io/badge/Deploy-Docker%20Compose-2496ed?style=for-the-badge)](https://docs.docker.com/compose/)

## Что это

Проект содержит полный исходный код Open WebUI в каталоге `upstream/` и отдельные файлы для локального запуска, hardened-сборки, документации и заметок по безопасности.

Основная идея: держать Open WebUI закрепленным на конкретной версии, вносить изменения аккуратно и не терять контроль над безопасностью, лицензией и деплоем.

## Статус

| Направление | Состояние |
| --- | --- |
| Upstream | `open-webui/open-webui` |
| Версия | `v0.9.6` |
| Ветка исходников | `custom-ui-v0.9.6` |
| Frontend | SvelteKit, Svelte 5, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Деплой | Docker Compose |
| Локальный порт | `127.0.0.1:3000` |

## Что уже добавлено

- Семантический аудит безопасности поверх штатного audit middleware Open WebUI.
- Read-only административная роль `security_curator`, в интерфейсе отображается как `Куратор ИБ`.
- Административные security endpoints:
  - `/api/v1/admin/security/audit/status`
  - `/api/v1/admin/security/versions`
- Hardened Dockerfile и compose-профиль для CVE-remediated образа.
- Отчеты проверок безопасности в `reports/security/`.
- Документация по архитектуре, решениям и текущим ограничениям в `docs/ai-memory/`.

## Структура

```text
.
├── deploy/              # Docker Compose и hardened Dockerfile
├── docs/ai-memory/      # журнал задач, решения, архитектура, TODO
├── notes/               # заметки по безопасности и кастомизации UI
├── reports/security/    # npm audit и Trivy отчеты
└── upstream/            # исходный код Open WebUI v0.9.6
```

## Быстрый запуск

Создайте локальный `.env` из шаблона:

```bash
cd deploy
cp .env.example .env
```

Запустите Open WebUI:

```bash
docker compose --env-file .env up -d
```

Откройте:

```text
http://127.0.0.1:3000
```

Остановить контейнер:

```bash
docker compose --env-file .env down
```

## Сборка кастомного образа

После изменений в `upstream/` собирайте локальный образ:

```bash
cd deploy
docker compose --env-file .env -f docker-compose.yml -f docker-compose.custom.yml build
docker compose --env-file .env -f docker-compose.yml -f docker-compose.custom.yml up -d
```

Hardened-вариант:

```bash
cd deploy
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.custom.yml \
  -f docker-compose.hardened.yml \
  build
```

## Разработка

Frontend:

```bash
cd upstream
npm install
npm run dev
```

Backend:

```bash
cd upstream/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -U
sh dev.sh
```

Проверки:

```bash
cd upstream
npm run check
npm run test:frontend
npm run build
```

Таргетированные backend-тесты аудита и RBAC:

```bash
cd upstream
docker run --rm \
  -e WEBUI_SECRET_KEY=test-secret-key-for-audit-tests \
  -v "$PWD:/app" \
  -w /app \
  --entrypoint sh \
  open-webui-custom:v0.9.6-ui-hardened \
  -c 'PYTHONPATH=/app/backend pytest -q /app/test/test_security_audit.py'
```

## Безопасность

Этот проект не рассчитан на прямую публикацию Open WebUI в интернет.

Рекомендуемый минимум:

- держать сервис за VPN, zero-trust proxy или authenticated reverse proxy;
- не использовать floating `main` для production;
- хранить `.env`, ключи, cookies, базы данных и секреты вне репозитория;
- после создания первого администратора выключить открытый signup;
- держать новых пользователей в роли `pending` по умолчанию;
- ограничить API keys и passthrough endpoints;
- аккуратно включать инструменты, functions, pipelines, terminal, Jupyter и code execution;
- перед production-деплоем заново проверить GitHub advisories, npm audit и Trivy.

## Лицензия и брендинг

Open WebUI `v0.6.6+` содержит требования к сохранению брендинга. В этом форке нельзя удалять, скрывать, перекрашивать, уменьшать или переносить брендинг Open WebUI без подтвержденного правового основания, письменного разрешения или enterprise-лицензии.

Код в `upstream/` сохраняет лицензии и уведомления upstream-проекта. Корневая лицензия относится к дополнительным материалам этого репозитория, если иное не указано явно.

## Важные ссылки

- Upstream: https://github.com/open-webui/open-webui
- Документация Open WebUI: https://docs.openwebui.com/
- Development docs: https://docs.openwebui.com/getting-started/advanced-topics/development/
- Hardening docs: https://docs.openwebui.com/getting-started/advanced-topics/hardening/
- License docs: https://docs.openwebui.com/license/
