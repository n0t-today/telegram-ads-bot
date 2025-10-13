# 🔧 Настройка автозапуска через systemd

Эта инструкция поможет настроить бота для автоматического запуска при загрузке системы и перезапуска при сбоях.

## Шаг 1: Создание service файла

Создайте файл `/etc/systemd/system/ad_bot.service`:

```bash
sudo nano /etc/systemd/system/ad_bot.service
```

Вставьте следующее содержимое:

```ini
[Unit]
Description=Telegram Ads Bot
After=network.target

[Service]
Type=simple
User=n0t-today
WorkingDirectory=/home/n0t-today/Документы/Работа/@skiberok
ExecStart=/usr/bin/python3 /home/n0t-today/Документы/Работа/@skiberok/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Важно:** Если вы используете виртуальное окружение, замените `ExecStart` на:

```ini
ExecStart=/home/n0t-today/Документы/Работа/@skiberok/venv/bin/python /home/n0t-today/Документы/Работа/@skiberok/main.py
```

## Шаг 2: Активация службы

```bash
# Перезагрузка конфигурации systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable ad_bot

# Запуск службы
sudo systemctl start ad_bot

# Проверка статуса
sudo systemctl status ad_bot
```

## Управление службой

### Запуск
```bash
sudo systemctl start ad_bot
```

### Остановка
```bash
sudo systemctl stop ad_bot
```

### Перезапуск
```bash
sudo systemctl restart ad_bot
```

### Проверка статуса
```bash
sudo systemctl status ad_bot
```

### Отключение автозапуска
```bash
sudo systemctl disable ad_bot
```

## Просмотр логов

### Последние логи
```bash
sudo journalctl -u ad_bot -n 50
```

### Логи в реальном времени
```bash
sudo journalctl -u ad_bot -f
```

### Логи за сегодня
```bash
sudo journalctl -u ad_bot --since today
```

### Логи за последний час
```bash
sudo journalctl -u ad_bot --since "1 hour ago"
```

## Устранение проблем

### Служба не запускается

1. Проверьте права на файлы:
```bash
ls -la /home/n0t-today/Документы/Работа/@skiberok/
```

2. Проверьте путь к Python:
```bash
which python3
```

3. Проверьте синтаксис конфигурации:
```bash
sudo systemd-analyze verify ad_bot.service
```

### Служба постоянно перезапускается

Проверьте логи на наличие ошибок:
```bash
sudo journalctl -u ad_bot -n 100
```

Частые причины:
- Неправильный токен бота
- Неправильные ID групп/каналов
- Отсутствующие зависимости

### Изменение конфигурации

После любых изменений в service файле:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ad_bot
```

## Пример настройки с виртуальным окружением

Если вы хотите использовать виртуальное окружение:

1. Создайте виртуальное окружение:
```bash
cd /home/n0t-today/Документы/Работа/@skiberok
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Измените `ExecStart` в service файле:
```ini
ExecStart=/home/n0t-today/Документы/Работа/@skiberok/venv/bin/python /home/n0t-today/Документы/Работа/@skiberok/main.py
```

3. Перезагрузите службу:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ad_bot
```

## Мониторинг

### Автоматическая проверка работы бота

Создайте скрипт проверки `/home/n0t-today/check_bot.sh`:

```bash
#!/bin/bash
if ! systemctl is-active --quiet ad_bot; then
    echo "Бот не запущен! Перезапускаю..."
    sudo systemctl start ad_bot
fi
```

Сделайте его исполняемым:
```bash
chmod +x /home/n0t-today/check_bot.sh
```

Добавьте в cron для проверки каждые 5 минут:
```bash
crontab -e
```

Добавьте строку:
```
*/5 * * * * /home/n0t-today/check_bot.sh
```

