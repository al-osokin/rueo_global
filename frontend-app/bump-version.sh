#!/bin/bash
# Скрипт для обновления версии приложения во всех необходимых местах

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v npm >/dev/null 2>&1; then
  echo "Ошибка: npm не найден. Установите Node.js/npm и повторите попытку."
  exit 1
fi

if [ -z "$1" ]; then
  echo "Использование: ./bump-version.sh <новая_версия>"
  echo "Пример: ./bump-version.sh 0.1.2"
  exit 1
fi

if [ ! -f "package.json" ]; then
  echo "Ошибка: package.json не найден в $SCRIPT_DIR"
  exit 1
fi

if [ ! -f "src-pwa/custom-service-worker.js" ]; then
  echo "Ошибка: src-pwa/custom-service-worker.js не найден"
  exit 1
fi

if [ ! -f "quasar.config.cjs" ]; then
  echo "Ошибка: quasar.config.cjs не найден"
  exit 1
fi

NEW_VERSION=$1

echo "Обновление версии до $NEW_VERSION..."

# 1. Обновляем версию в package.json и package-lock.json
echo "1. Обновление package.json и package-lock.json..."
npm version "$NEW_VERSION" --no-git-tag-version

# 2. Копируем в public/package.json
echo "2. Синхронизация public/package.json..."
cp package.json public/package.json

# 3. Обновляем версию в custom-service-worker.js
echo "3. Обновление custom-service-worker.js..."
sed -i "s/const CACHE_VERSION = 'v.*';/const CACHE_VERSION = 'v$NEW_VERSION';/" src-pwa/custom-service-worker.js

# 4. Обновляем manifestFilename, если он статически задан
echo "4. Проверка manifestFilename в quasar.config.cjs..."
if grep -q "manifestFilename" quasar.config.cjs; then
  if grep -q "manifest-\${" quasar.config.cjs; then
    echo "   manifestFilename уже использует версию из package.json"
  else
    sed -i "s/manifestFilename:.*$/manifestFilename: \"manifest-$NEW_VERSION.json\",/" quasar.config.cjs
  fi
else
  echo "   Внимание: manifestFilename не найден (используется manifest.json по умолчанию)"
fi

echo ""
echo "✅ Версия обновлена до $NEW_VERSION в:"
echo "   - package.json"
echo "   - package-lock.json"
echo "   - public/package.json"
echo "   - src-pwa/custom-service-worker.js"
echo "   - quasar.config.cjs (manifestFilename)"
echo ""
echo "Следующие шаги:"
echo "1. Проверьте изменения: git diff"
echo "2. Зафиксируйте: git add -u && git commit -m 'Bump version to $NEW_VERSION'"
echo "3. Соберите: quasar build -m pwa"
echo "4. Задеплойте на сервер"
