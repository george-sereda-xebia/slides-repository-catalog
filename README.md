# Slides Repository Catalog

Автоматический каталог презентаций из папки `Reusable_Assets/` с превью всех слайдов.

## Quick Start

```bash
# Собрать каталог
./build.sh

# Просмотреть каталог
./view.sh
```

Откроется каталог на http://localhost:8000

## Что делает

1. Сканирует `Reusable_Assets/` и все подпапки
2. Находит все .pptx файлы
3. Конвертирует каждый слайд в PNG (через LibreOffice)
4. Генерирует HTML каталог с поиском и превью

## Требования

- Python 3.11+
- LibreOffice (для конвертации слайдов)

```bash
# macOS
brew install libreoffice

# Ubuntu
sudo apt-get install libreoffice
```

## Установка

```bash
# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

## Структура проекта

```
.
├── Reusable_Assets/         # Папка с презентациями (источник)
├── site/                    # Сгенерированный каталог (выход)
│   ├── index.html          # Главная страница
│   └── assets/             # Превью слайдов
├── src/                     # Код генератора
│   ├── build_catalog.py    # Главный скрипт
│   ├── local_client.py     # Работа с локальными файлами
│   └── slides_renderer.py  # Конвертация PPTX → PNG
├── templates/
│   └── index.html          # Шаблон каталога
├── build.sh                # Скрипт сборки
└── view.sh                 # Скрипт просмотра
```

## Ручной запуск

```bash
source venv/bin/activate
export SOURCE_MODE=local
python3 src/build_catalog.py
```

## GitHub Actions

Добавьте в GitHub Secrets:
- `SOURCE_MODE=local`

Workflow автоматически запустится по расписанию (каждый час, 6 AM - 8 PM UTC).

## License

MIT
