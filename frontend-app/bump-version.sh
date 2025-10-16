#!/bin/bash
# Скрипт для обновления версии приложения во всех необходимых местах

set -e

if [ -z "$1" ]; then
  echo "Использование: ./bump-version.sh <новая_версия>"
  echo "Пример: ./bump-version.sh 0.1.2"
  exit 1
fi

NEW_VERSION=$1

echo "Обновление версии до $NEW_VERSION..."

# 1. Обновляем версию в корневом package.json
echo "1. Обновление package.json..."
sed -i "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" package.json

# 2. Копируем в public/package.json
echo "2. Синхронизация public/package.json..."
cp package.json public/package.json

# 3. Обновляем версию в custom-service-worker.js
echo "3. Обновление custom-service-worker.js..."
sed -i "s/const CACHE_VERSION = 'v.*';/const CACHE_VERSION = 'v$NEW_VERSION';/" src-pwa/custom-service-worker.js

echo ""
echo "✅ Версия обновлена до $NEW_VERSION в:"
echo "   - package.json"
echo "   - public/package.json"
echo "   - src-pwa/custom-service-worker.js"
echo ""
echo "Следующие шаги:"
echo "1. Проверьте изменения: git diff"
echo "2. Зафиксируйте: git add -u && git commit -m 'Bump version to $NEW_VERSION'"
echo "3. Соберите: quasar build -m pwa"
echo "4. Задеплойте на сервер"
