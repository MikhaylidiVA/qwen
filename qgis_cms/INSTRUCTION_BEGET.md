# QGIS CMS Pro - Инструкция по развертыванию на Beget.com

## 📋 Обзор системы

QGIS CMS Pro - это современная веб-GIS платформа с возможностями, аналогичными QGIS:
- ✅ Работа с пространственными данными через PostGIS
- ✅ Ролевая модель (Admin, Editor, Viewer)
- ✅ Создание и редактирование слоев
- ✅ Добавление точек на карту
- ✅ Импорт GeoJSON и экспорт CSV
- ✅ Пространственный анализ (буферные зоны)
- ✅ Аудит действий пользователей
- ✅ Настройки пользователя (тема, центр карты)
- ✅ Dashboard со статистикой

## 🚀 Пошаговая инструкция для Beget.com

### Шаг 1: Создание базы данных PostgreSQL

1. Войдите в панель управления Beget
2. Перейдите в раздел **PostgreSQL**
3. Нажмите **"Создать базу данных"**
4. Заполните:
   - Имя БД: `qgis_cms`
   - Пользователь: создайте нового (например, `qgis_user`)
   - Пароль: запишите надежный пароль
5. Сохраните данные подключения

### Шаг 2: Установка расширения PostGIS

1. Откройте **phpMyAdmin** в панели Beget
2. Выберите вашу базу данных `qgis_cms`
3. Перейдите на вкладку **SQL**
4. Выполните команду:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```
5. Убедитесь, что выполнено успешно (должно появиться сообщение о создании)

### Шаг 3: Подготовка файлов проекта

Скачайте файлы из папки `/workspace/qgis_cms/`:

```
qgis_cms/
├── backend/
│   ├── main.py           # Backend на FastAPI
│   └── requirements.txt  # Python зависимости
└── frontend/
    └── index.html        # Frontend приложение
```

### Шаг 4: Настройка Backend

#### 4.1. Отредактируйте `main.py`

Найдите строки с конфигурацией БД и замените на ваши данные от Beget:

```python
DB_USER = "ваш_пользователь"
DB_PASS = "ваш_пароль"
DB_HOST = "адрес_сервера_beget"  # обычно вида xxxxx.beget.tech
DB_PORT = 5432
DB_NAME = "qgis_cms"
SECRET_KEY = "смените_на_случайную_строку"
```

#### 4.2. Альтернативно используйте переменные окружения

В панели Beget → Python → Переменные окружения добавьте:
- `DB_USER`
- `DB_PASS`
- `DB_HOST`
- `DB_NAME`
- `SECRET_KEY`

### Шаг 5: Загрузка файлов на хостинг

#### Вариант A: Через FTP

1. Подключитесь к FTP (данные в письме от Beget)
2. Создайте структуру папок:
```
/your_site/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   └── index.html
└── public/  (для статики)
```

#### Вариант B: Через файловый менеджер Beget

1. Панель Beget → Файловый менеджер
2. Перейдите в папку вашего сайта
3. Создайте папки `backend` и `frontend`
4. Загрузите файлы

### Шаг 6: Настройка Python приложения

1. В панели Beget перейдите в раздел **Python**
2. Нажмите **"Добавить приложение"**
3. Настройте:
   - **Путь к приложению**: `/backend/main.py`
   - **Домен**: выберите ваш домен
   - **Python версия**: 3.9 или выше
   - **Точка входа**: `app` (FastAPI приложение)
   
4. В поле **Зависимости** укажите содержимое `requirements.txt`:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
geoalchemy2==0.14.2
shapely==2.0.2
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
pandas==2.1.3
python-multipart==0.0.6
```

5. Нажмите **"Установить"**

### Шаг 7: Настройка фронтенда

Откройте `frontend/index.html` и найдите строку:

```javascript
const API_URL = window.location.hostname === 'localhost' ? 'http://localhost:8000' : '';
```

Замените на ваш домен:

```javascript
const API_URL = 'https://your-domain.beget.tech';
```

Или оставьте пустую строку, если фронтенд и бэкенд на одном домене.

### Шаг 8: Настройка .htaccess (если нужно)

Создайте файл `.htaccess` в корне сайта для проксирования запросов:

```apache
RewriteEngine On

# API запросы на Python приложение
RewriteRule ^api/(.*)$ /backend/$1 [P,L]

# Статика - фронтенд
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ /frontend/index.html [L,QSA]
```

### Шаг 9: Первый запуск и проверка

1. В панели Python нажмите **"Запустить"**
2. Проверьте логи на наличие ошибок
3. Откройте ваш сайт в браузере

### Шаг 10: Регистрация первого администратора

1. Откройте сайт
2. Нажмите **"Register"**
3. Создайте учетную запись с ролью `admin` (через API или измените в БД):

```sql
-- В phpMyAdmin выполните:
UPDATE users SET role = 'admin' WHERE username = 'ваше_имя';
```

## 🔧 Дополнительные настройки

### Настройка CORS

Если возникают ошибки CORS, в `main.py` измените:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Оптимизация производительности

Для production в `main.py` измените:

```python
# Включите pool соединений
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

# Отключите логирование SQL
engine = create_engine(DATABASE_URL, echo=False)
```

### Безопасность

1. Смените `SECRET_KEY` на случайную строку
2. Используйте HTTPS (Beget предоставляет SSL)
3. Ограничьте CORS только вашим доменом
4. Регулярно обновляйте зависимости

## 📊 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/register` | Регистрация пользователя |
| POST | `/token` | Получение токена (login) |
| GET | `/users/me` | Текущий пользователь |
| PUT | `/users/me/settings` | Обновление настроек |
| GET | `/layers` | Список слоев |
| POST | `/layers` | Создание слоя |
| DELETE | `/layers/{id}` | Удаление слоя |
| GET | `/layers/{id}/features` | Получить объекты |
| POST | `/layers/{id}/features` | Добавить объект |
| PUT | `/features/{id}` | Обновить объект |
| DELETE | `/features/{id}` | Удалить объект |
| POST | `/import/geojson/{id}` | Импорт GeoJSON |
| GET | `/export/csv/{id}` | Экспорт CSV |
| POST | `/analysis/buffer/{id}` | Буферный анализ |
| GET | `/dashboard/stats` | Статистика (admin) |
| GET | `/audit/logs` | Логи аудита (admin) |

## 🐛 Решение проблем

### Ошибка подключения к БД
- Проверьте данные подключения в `main.py`
- Убедитесь, что PostgreSQL запущен
- Проверьте права доступа пользователя

### PostGIS не работает
- Выполните `CREATE EXTENSION postgis;` вручную
- Проверьте версию PostgreSQL (нужна 12+)

### Ошибки CORS
- Настройте `allow_origins` в middleware
- Проверьте протокол (HTTP vs HTTPS)

### Приложение не запускается
- Проверьте логи в панели Python
- Убедитесь, что все зависимости установлены
- Проверьте путь к точке входа

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в панели Beget
2. Протестируйте API через Swagger (`/docs`)
3. Убедитесь, что PostGIS установлен корректно

---

**Версия**: 2.0  
**Лицензия**: MIT  
**Автор**: QGIS CMS Team
