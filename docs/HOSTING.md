# Хостинг «Анималити» (Django + PostgreSQL)

## Бесплатные варианты (2026)

| Платформа | Django | PostgreSQL | Медиа-файлы | Минусы |
|-----------|--------|------------|-------------|--------|
| **[Render](https://render.com)** | Web Service (Python) | Бесплатная БД (ограничения) | Диск эфемерный — нужен S3/Cloudinary | Сон после ~15 мин без трафика, холодный старт |
| **[Neon](https://neon.tech)** + Render | Только приложение на Render | Отдельно Neon (щедрый free tier) | Как выше | Два сервиса, зато БД не «засыпает» так же |
| **[Fly.io](https://fly.io)** | Docker / Dockerfile | Postgres addon | Volume или внешнее хранилище | Сложнее настройка, лимиты по кредитам |
| **[Railway](https://railway.app)** | Да | Да | Volume | Мало бесплатных кредитов в месяц |

**Рекомендация для вашего проекта:** **Render (приложение) + Neon (PostgreSQL)** или всё на **Render**, если хватит лимитов.

Не подходят для «бесплатно Django+Postgres из коробки»:
- **PythonAnywhere** — на free только MySQL, не PostgreSQL.
- **Vercel / Netlify** — не для классического Django с БД.

Для аудитории в РФ: Render и Neon обычно открываются без VPN; оплата не нужна на free tier. Если понадобится платный российский VPS — Timeweb / Selectel / Beget (от ~200–300 ₽/мес), но настройка вручную (nginx, gunicorn, postgres).

---

## Что понадобится перед деплоем

1. **Репозиторий на GitHub** (без `.env` — только `.env.example`).
2. **`requirements.txt`** с `gunicorn`, `whitenoise`, `psycopg[binary]`, `python-dotenv`.
3. **`DEBUG=False`**, свой **`SECRET_KEY`**, **`ALLOWED_HOSTS`** с доменом Render.
4. **`collectstatic`** + **WhiteNoise** для CSS/JS.
5. **Медиа** (`media/`) — на бесплатном Render диск сбрасывается; для фото животных лучше позже подключить **Cloudinary** или S3-совместимое хранилище.
6. Переменные окружения на хостинге (те же имена, что в `.env.example`):
   - `PG_*` или `DATABASE_URL` (если настроим парсинг)
   - `MAILRU_EMAIL_*`
   - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`

---

## Следующий шаг

Когда выберете платформу (например, Render), напишите в чат — подготовим `Dockerfile` / `render.yaml`, `gunicorn`, WhiteNoise и пошаговый деплой с вашим репозиторием.
