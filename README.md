# 🍕 FridgeBot — AI-кулинарный помощник

Телеграм-бот, который анализирует фото холодильника и предлагает 3 рецепта из доступных продуктов. Работает на базе Claude Vision API.

## Быстрый старт

### 1. Получи токены

**Telegram Bot Token:**
1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Напиши `/newbot` и следуй инструкциям
3. Скопируй полученный токен

**Anthropic API Key:**
1. Зайди на [console.anthropic.com](https://console.anthropic.com)
2. Создай API ключ в разделе API Keys

### 2. Установи зависимости

```bash
git clone <repo>
cd fridge_bot

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Настрой окружение

```bash
cp .env.example .env
# Открой .env и вставь свои токены
```

### 4. Запусти бота

```bash
python bot.py
```

## Структура проекта

```
fridge_bot/
├── bot.py            # Telegram handlers
├── claude_client.py  # Запросы к Claude Vision API
├── prompts.py        # Системный и пользовательский промпты
├── requirements.txt
├── .env.example
└── README.md
```

## Функциональность

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкция |
| `/help` | Советы по использованию |
| `/diet` | Выбор диетических предпочтений |
| 📸 Фото | Анализ + 3 рецепта |

**Кнопки у рецептов:**
- ♻️ Другие рецепты — попросить прислать фото повторно
- ❤️ Сохранить — сохранить рецепт (можно расширить до БД)

## Деплой на сервер (Railway)

```bash
# Установи Railway CLI
npm install -g @railway/cli

railway login
railway new
railway up

# Добавь переменные окружения в Railway Dashboard
```

## Расширение функциональности

- **База данных** (SQLite/PostgreSQL) — сохранение любимых рецептов
- **История** — `/history` для просмотра прошлых рецептов
- **Webhook** вместо polling для продакшена
- **Inline-режим** — делиться рецептами в других чатах
