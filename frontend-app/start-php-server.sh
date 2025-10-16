#!/bin/bash
# Скрипт для запуска PHP сервера в режиме разработки

cd "$(dirname "$0")/public"
echo "Запускаем PHP сервер на http://localhost:8001..."
echo "Для остановки нажмите Ctrl+C"
php -S localhost:8001
