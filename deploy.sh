#!/bin/bash

# ——————————————————————————————————————————————————————————————
# СКРИПТ ДЕПЛОЯ TELEGRAM-БОТА НА СЕРВЕР
# ——————————————————————————————————————————————————————————————

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Конфигурация
SSH_KEY="privatekey-932873.pem"
SERVER_USER="ubuntu"
SERVER_HOST="81.94.159.247"
SERVER_PATH="/home/ubuntu/ad_bot"
GIT_REPO="https://github.com/n0t-today/telegram-ads-bot.git"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Деплой Telegram-бота для объявлений${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Проверка наличия SSH ключа
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ Ошибка: SSH ключ не найден: $SSH_KEY${NC}"
    echo -e "${YELLOW}Положите файл ключа в текущую директорию${NC}"
    exit 1
fi

# Установка прав на ключ
chmod 600 "$SSH_KEY"

echo -e "${YELLOW}🔧 Проверка подключения к серверу...${NC}"
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" "echo 'OK'" > /dev/null 2>&1; then
    echo -e "${RED}❌ Не удалось подключиться к серверу${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Подключение успешно${NC}"
echo ""

echo -e "${YELLOW}📦 Деплой на сервер...${NC}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" bash <<'ENDSSH'
set -e

SERVER_PATH="/home/ubuntu/ad_bot"
GIT_REPO="https://github.com/n0t-today/telegram-ads-bot.git"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Деплой на сервере"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Проверяем, существует ли директория
if [ -d "$SERVER_PATH" ]; then
    echo "📂 Директория существует, обновляем..."
    cd "$SERVER_PATH"
    
    # Останавливаем бота если запущен
    if sudo systemctl is-active --quiet ad_bot 2>/dev/null; then
        echo "⏸️  Останавливаем бота..."
        sudo systemctl stop ad_bot
    fi
    
    # Сохраняем config.py и базу данных
    if [ -f "config.py" ]; then
        echo "💾 Сохраняем конфигурацию..."
        cp config.py /tmp/config.py.backup
    fi
    
    if [ -f "bot_database.db" ]; then
        echo "💾 Сохраняем базу данных..."
        cp bot_database.db /tmp/bot_database.db.backup
    fi
    
    # Обновляем код
    echo "🔄 Обновляем код из Git..."
    git fetch origin
    git reset --hard origin/main || git reset --hard origin/master
    
    # Восстанавливаем config.py и базу
    if [ -f "/tmp/config.py.backup" ]; then
        echo "📥 Восстанавливаем конфигурацию..."
        cp /tmp/config.py.backup config.py
    fi
    
    if [ -f "/tmp/bot_database.db.backup" ]; then
        echo "📥 Восстанавливаем базу данных..."
        cp /tmp/bot_database.db.backup bot_database.db
    fi
else
    echo "📥 Клонируем репозиторий..."
    git clone "$GIT_REPO" "$SERVER_PATH"
    cd "$SERVER_PATH"
    
    echo "⚠️  ВАЖНО: Не забудьте настроить config.py!"
fi

# Установка/обновление зависимостей
echo "📦 Устанавливаем зависимости..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Создаем/обновляем systemd сервис
echo "🔧 Настраиваем systemd сервис..."
sudo tee /etc/systemd/system/ad_bot.service > /dev/null <<EOF
[Unit]
Description=Telegram Ads Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$SERVER_PATH
ExecStart=$SERVER_PATH/venv/bin/python $SERVER_PATH/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable ad_bot

# Запускаем бота
echo "🚀 Запускаем бота..."
sudo systemctl start ad_bot

# Проверяем статус
sleep 2
if sudo systemctl is-active --quiet ad_bot; then
    echo "✅ Бот успешно запущен!"
    echo ""
    echo "📊 Статус сервиса:"
    sudo systemctl status ad_bot --no-pager -l
else
    echo "❌ Ошибка запуска бота!"
    echo ""
    echo "📋 Последние логи:"
    sudo journalctl -u ad_bot -n 50 --no-pager
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Деплой завершен успешно!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Полезные команды:"
echo "  Просмотр логов:      sudo journalctl -u ad_bot -f"
echo "  Статус:              sudo systemctl status ad_bot"
echo "  Перезапуск:          sudo systemctl restart ad_bot"
echo "  Остановка:           sudo systemctl stop ad_bot"
echo ""

ENDSSH

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Деплой завершен!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Для просмотра логов выполните:${NC}"
echo -e "ssh -i $SSH_KEY $SERVER_USER@$SERVER_HOST 'sudo journalctl -u ad_bot -f'"
echo ""

