#!/bin/bash

# ——————————————————————————————————————————————————————————————
# СКРИПТ ОБНОВЛЕНИЯ БОТА НА СЕРВЕРЕ
# ——————————————————————————————————————————————————————————————

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Конфигурация
SSH_KEY="privatekey-932873.pem"
SERVER_USER="ubuntu"
SERVER_HOST="81.94.159.247"
SERVER_PATH="/home/ubuntu/ad_bot"

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Обновление бота на сервере${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Проверка наличия SSH ключа
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ Ошибка: SSH ключ не найден: $SSH_KEY${NC}"
    exit 1
fi

chmod 600 "$SSH_KEY"

echo -e "${YELLOW}🔄 Обновление бота...${NC}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" bash <<'ENDSSH'
set -e

SERVER_PATH="/home/ubuntu/ad_bot"

cd "$SERVER_PATH"

echo "⏸️  Останавливаем бота..."
sudo systemctl stop ad_bot

echo "💾 Создаем бэкап конфигурации и БД..."
cp config.py /tmp/config.py.backup
if [ -f "bot_database.db" ]; then
    cp bot_database.db /tmp/bot_database.db.backup
fi

echo "📥 Обновляем код..."
git fetch origin
git reset --hard origin/main || git reset --hard origin/master

echo "📥 Восстанавливаем конфигурацию и БД..."
cp /tmp/config.py.backup config.py
if [ -f "/tmp/bot_database.db.backup" ]; then
    cp /tmp/bot_database.db.backup bot_database.db
fi

echo "📦 Обновляем зависимости..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "🚀 Запускаем бота..."
sudo systemctl start ad_bot

sleep 2

if sudo systemctl is-active --quiet ad_bot; then
    echo "✅ Бот успешно обновлен и запущен!"
    sudo systemctl status ad_bot --no-pager -l | head -n 15
else
    echo "❌ Ошибка запуска!"
    sudo journalctl -u ad_bot -n 30 --no-pager
    exit 1
fi

ENDSSH

echo ""
echo -e "${GREEN}✅ Обновление завершено!${NC}"
echo ""

