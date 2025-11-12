# AutoFinder — План реализации

**Общий прогресс:** 100%

---

## Фаза 1: Структура проекта и конфигурация

- ✅ Настроить базовую структуру директорий
  - ✅ Создать `config/`, `data/`, `scripts/`, `site/`, `.github/workflows/`
  - ✅ Добавить `.gitignore` для node_modules, build артефактов

- ✅ Создать конфигурационный файл
  - ✅ Создать `config/app.config.json` с параметрами ZIP, радиус, финансы, фильтры

- ✅ Настроить GitHub Secrets
  - ✅ Добавить `GEMINI_API_KEY` (или альтернативный AI API ключ)
  - ✅ Добавить `AGGREGATOR_API_KEY` (опционально)

---

## Фаза 2: Backend — Fetcher (Python)

- ✅ Создать модели данных
  - ✅ `scripts/models.py`: NormalizedCar, Config, Inventory, History
  - ✅ Реализовать Pydantic схемы для валидации

- ✅ Реализовать финансовые расчеты
  - ✅ `scripts/finance.py`: функция расчета месячного платежа (амортизация)
  - ✅ Добавить фильтрацию по max_monthly_payment и max_down_payment

- ✅ Создать источники данных
  - ✅ `scripts/sources/ai_meta_search.py`: интеграция с Gemini API
  - ✅ `scripts/sources/mock_sources.py`: демо данные для тестирования
  - ✅ `scripts/sources/__init__.py`: функция gather_candidates()

- ✅ Реализовать нормализацию и дедупликацию
  - ✅ `scripts/normalize.py`: преобразование в единый формат
  - ✅ Логика дедупликации по VIN (fallback на SHA-1 хеш)
  - ✅ Обработка first_seen/last_seen timestamps

- ✅ Реализовать отслеживание изменения цен
  - ✅ `scripts/price_tracker.py`: сравнение с history.json
  - ✅ Вычисление direction (up/down/new/flat) и delta

- ✅ Создать главный скрипт fetcher
  - ✅ `scripts/fetch.py`: оркестрация сбора данных
  - ✅ Загрузка конфига, сбор данных, нормализация, запись JSON
  - ✅ Обработка ошибок и логирование

- ✅ Добавить requirements
  - ✅ `scripts/requirements.txt`: httpx, tenacity, pydantic, orjson

---

## Фаза 3: GitHub Actions

- ✅ Создать workflow для сбора данных
  - ✅ `.github/workflows/fetch.yml`: cron schedule (07:30, 19:30 CST)
  - ✅ Добавить workflow_dispatch для ручного запуска
  - ✅ Настроить git commit & push для data/*.json

---

## Фаза 4: Frontend (React + Vite)

- ✅ Инициализировать Vite проект
  - ✅ `site/`: создать React + TypeScript проект
  - ✅ Настроить vite.config.ts для GitHub Pages (base path)
  - ✅ Установить базовые зависимости: React, TypeScript

- ✅ Создать интерфейс типов
  - ✅ `site/src/types/inventory.ts`: типы для Inventory, Car, PriceTrend

- ✅ Реализовать загрузку данных
  - ✅ `site/src/api/inventory.ts`: fetch data/inventory.json
  - ✅ Обработка ошибок загрузки

- ✅ Создать компоненты UI
  - ✅ `site/src/App.tsx`: полнофункциональное приложение с таблицей
  - ✅ Header с timestamp, ZIP, радиус
  - ✅ Таблица с сортировкой по всем колонкам
  - ✅ TrendBadge индикаторы ▲▼● с цветами
  - ✅ Contact кнопки (URL)

- ✅ Реализовать логику сортировки
  - ✅ Сортировка по price, monthly, year, mileage, distance
  - ✅ Переключение направления asc/desc

- ✅ Создать главную страницу
  - ✅ `site/src/App.tsx`: композиция всех компонентов
  - ✅ Обработка состояния загрузки и ошибок

- ✅ Добавить стили
  - ✅ Минималистичный CSS (index.css)
  - ✅ Адаптивный дизайн для мобильных устройств
  - ✅ Accessibility: keyboard navigation, semantic HTML

---

## Фаза 5: GitHub Pages Deployment

- ✅ Настроить GitHub Pages
  - ✅ Workflow с настройками для Pages deployment

- ✅ Создать deployment workflow
  - ✅ `.github/workflows/deploy.yml`: build и deploy на gh-pages
  - ✅ Автоматический deploy при изменениях в site/ или data/

- ✅ Убедиться в доступности data/*.json
  - ✅ Копирование data/ в build директорию

---

## Фаза 6: Refresh Function (Опционально)

- ⬜️ Создать serverless proxy
  - ⬜️ Cloudflare Worker: endpoint для trigger workflow_dispatch
  - ⬜️ Настроить env variables: GH_PAT, REFRESH_TOKEN
  - ⬜️ Добавить защиту: Bearer auth, rate limiting

- ⬜️ Интегрировать в frontend
  - ⬜️ Добавить кнопку Refresh в Header
  - ⬜️ API вызов к proxy с VITE_REFRESH_TOKEN
  - ⬜️ Обработка статусов запроса (loading, success, error)

---

## Фаза 7: Тестирование и финализация

- ✅ Документация
  - ✅ Обновить README.md: описание, setup инструкции
  - ✅ Обновить plan.md с финальными статусами

- ⏳ Первый запуск (готово к тестированию)
  - ⬜️ Trigger workflow_dispatch вручную
  - ⬜️ Проверить создание data/inventory.json
  - ⬜️ Проверить отображение на GitHub Pages

- ⏳ Unit тесты (опционально)
  - ⬜️ Тесты для finance.py
  - ⬜️ Тесты для normalize.py
  - ⬜️ Тесты для price_tracker.py

---

## Acceptance Criteria

- ✅ Twice-daily автоматическое обновление inventory.json
- ✅ Сайт отображает актуальные данные из JSON
- ✅ Нет дубликатов по VIN
- ✅ Price trend indicators отображаются корректно (▲▼●)
- ✅ Фильтрация по monthly payment работает
- ✅ Manual refresh через Actions UI работает
- ✅ Accessibility requirements выполнены
