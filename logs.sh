#!/bin/bash

# ——————————————————————————————————————————————————————————————
# СКРИПТ ПРОСМОТРА ЛОГОВ БОТА
# ——————————————————————————————————————————————————————————————

# Конфигурация
SSH_KEY="privatekey-932873.pem"
SERVER_USER="ubuntu"
SERVER_HOST="81.94.159.247"

# Проверка наличия SSH ключа
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Ошибка: SSH ключ не найден: $SSH_KEY"
    exit 1
fi

chmod 600 "$SSH_KEY"

echo "📋 Подключаемся к логам бота..."
echo "Нажмите Ctrl+C для выхода"
echo ""

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_HOST" 'sudo journalctl -u ad_bot -f'

