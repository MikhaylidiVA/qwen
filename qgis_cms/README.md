# QGIS CMS Pro 🗺️

Современная веб-GIS платформа с возможностями QGIS, работающая через облачный PostgreSQL с PostGIS.

## ✨ Возможности

### 🌍 GIS Функционал
- **Работа с векторными данными**: точки, линии, полигоны
- **PostGIS интеграция**: полноценная поддержка пространственных данных
- **Импорт/Экспорт**: GeoJSON, CSV с WKT геометриями
- **Пространственный анализ**: буферные зоны, пересечения
- **Интерактивная карта**: Leaflet.js с OpenStreetMap

### 👥 Управление пользователями
- **Ролевая модель**: Admin, Editor, Viewer
- **Аутентификация**: JWT токены
- **Настройки**: тема (light/dark), центр карты, зум
- **Аудит**: логирование всех действий

### 📊 Администрирование
- **Dashboard**: статистика по пользователям, слоям, объектам
- **Мониторинг**: активность за 7 дней
- **Управление слоями**: публичные/приватные
- **Логи аудита**: кто, что и когда сделал

## 🏗️ Архитектура

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│    Backend       │────▶│  PostgreSQL     │
│   (Leaflet.js)  │◀────│    (FastAPI)     │◀────│  + PostGIS      │
│   HTML/CSS/JS   │     │   Python 3.9+    │     │   Spatial DB    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## 🚀 Быстрый старт

### 1. Подготовка БД

```bash
# Создайте БД и включите PostGIS
createdb qgis_cms
psql -d qgis_cms -c "CREATE EXTENSION postgis;"
```

### 2. Настройка переменных окружения

```bash
export DB_USER=postgres
export DB_PASS=your_password
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=qgis_cms
export SECRET_KEY=your_secret_key
```

### 3. Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

### 4. Запуск сервера

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Открыть фронтенд

Просто откройте `frontend/index.html` в браузере или разместите на веб-сервере.

## 📁 Структура проекта

```
qgis_cms/
├── backend/
│   ├── main.py              # FastAPI приложение (358 строк)
│   └── requirements.txt     # Python зависимости
├── frontend/
│   └── index.html          # SPA приложение (708 строк)
├── README.md               # Этот файл
└── INSTRUCTION_BEGET.md    # Инструкция для Beget.com
```

## 🔌 API Endpoints

### Аутентификация
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/register` | Регистрация нового пользователя |
| POST | `/token` | Получение JWT токена (login) |
| GET | `/users/me` | Информация о текущем пользователе |
| PUT | `/users/me/settings` | Обновление настроек профиля |

### Слои
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/layers` | Список доступных слоев |
| POST | `/layers` | Создание нового слоя |
| DELETE | `/layers/{id}` | Удаление слоя |

### Объекты (Features)
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/layers/{id}/features` | Получить все объекты слоя |
| POST | `/layers/{id}/features` | Добавить объект |
| PUT | `/features/{id}` | Обновить объект |
| DELETE | `/features/{id}` | Удалить объект |

### Инструменты
| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/import/geojson/{id}` | Импорт GeoJSON файла |
| GET | `/export/csv/{id}` | Экспорт слоя в CSV |
| POST | `/analysis/buffer/{id}` | Построение буферных зон |

### Администрирование
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/dashboard/stats` | Статистика системы |
| GET | `/audit/logs` | Логи действий пользователей |

## 💻 Примеры использования

### Создание точки через API

```bash
curl -X POST "http://localhost:8000/layers/1/features" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "geometry": {"type": "Point", "coordinates": [37.61, 55.75]},
    "properties": {"name": "Москва", "type": "city"}
  }'
```

### Буферный анализ

```bash
curl -X POST "http://localhost:8000/analysis/buffer/1?distance=1000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Экспорт в CSV

```bash
curl "http://localhost:8000/export/csv/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o layer_data.csv
```

## 🔒 Безопасность

- **JWT аутентификация** с истекающим токеном (7 дней)
- **Ролевой доступ** (RBAC)
- **Bcrypt хеширование** паролей
- **CORS настройки** для защиты от CSRF
- **Валидация данных** через Pydantic

## 🎨 Темы оформления

Приложение поддерживает две темы:

**Light Theme** (по умолчанию):
- Светлый фон
- Синие акценты
- Темный текст

**Dark Theme**:
- Темный фон
- Приглушенные цвета
- Светлый текст

Переключение в настройках пользователя.

## 📦 Зависимости

### Backend
- FastAPI 0.104+
- SQLAlchemy 2.0+
- GeoAlchemy2 (PostGIS)
- Shapely (геометрии)
- Passlib (bcrypt)
- Python-Jose (JWT)
- Pandas (экспорт)

### Frontend
- Leaflet.js 1.9+ (карты)
- OpenStreetMap (тайлы)
- Google Fonts (Inter)
- Vanilla JS (без фреймворков)

## 🐛 Решение проблем

### PostGIS не найден
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

### Ошибки CORS
Проверьте настройки middleware в `main.py`.

### Токен не работает
Убедитесь, что SECRET_KEY совпадает при генерации и проверке.

## 📄 Лицензия

MIT License

## 👥 Авторы

QGIS CMS Team - 2024

---

**Версия**: 2.0  
**Последнее обновление**: Декабрь 2024
