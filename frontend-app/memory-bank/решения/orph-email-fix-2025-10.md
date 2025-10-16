# Исправление отправки сообщений об ошибках (Орфус)

**Дата:** 2025-10-10  
**Версия:** 0.5.0  
**Статус:** ✅ Успешно развернуто в production

## Проблема

Система отправки сообщений о замеченных орфографических ошибках ("Орфус") не работала корректно:

1. **Переадресация на старый сайт** - запросы шли через `https://old.rueo.ru/orph.php`, что приводило к таймаутам
2. **Ложные сообщения об ошибке** - письма отправлялись, но пользователь видел "Ошибка отправки"
3. **Попытки локальной реализации** - скрипты `orph.php` и `.smtp_config.php` были перенесены, но не работали:
   - Отсутствовала папка `logs/`
   - Не проверялись коды ответов SMTP
   - Таймауты были слишком короткими (5 сек)
   - SMTP-сессия занимала 32 секунды, Service Worker прерывал запрос

4. **Проблема с обновлениями PWA** - при повышении версии происходили бесконечные перезагрузки из-за конфликта двух систем обновления

## Решение

### 1. Прямая отправка через SMTP

**Файл:** `public/orph.php`

Изменения:
- Добавлено `global $smtp_config` для правильного логирования
- Увеличен таймаут с 5 до 15 секунд
- Добавлена валидация всех SMTP-команд с ожидаемыми кодами ответов (220, 250, 334, 235, 354, 221)
- Реализован асинхронный подход:
  ```php
  ignore_user_abort(true);
  set_time_limit(60);
  echo 'Bone'; // Возвращаем успех сразу
  // Закрываем соединение с клиентом
  // Отправляем письмо в фоне
  smtp_send(...);
  ```

### 2. Оптимистичный UI

**Файл:** `src/layouts/MainLayout.vue`

Изменения:
- Уведомление показывается мгновенно, не дожидаясь ответа сервера
- Запрос отправляется в фоне с таймаутом 60 секунд
- Если запрос прервется - письмо всё равно отправится на сервере

```javascript
// Показываем уведомление сразу (оптимистичный подход)
this.$q.notify({
  type: "positive",
  message: "Сообщение отправлено",
});
this.orph_reset();

// Отправляем в фоне
this.$axios.post("/orph.php", postDataSerialized, { timeout: 60000 })
```

### 3. Настройка для dev-режима

**Файлы:**
- `quasar.conf.js` - добавлен прокси `/orph.php` → `http://localhost:8001`
- `public/api-proxy.php` - добавлен обработчик для `/orph.php`
- `start-php-server.sh` - скрипт запуска PHP сервера для разработки

Для работы в dev-режиме нужно запустить:
```bash
./start-php-server.sh
```

### 4. Исправление бесконечных перезагрузок Service Worker

**Проблема:** Конфликт двух систем обновления:
- `register-service-worker.js` → `window.location.reload(true)` при обновлении SW
- `cache-manager.js` → `forceReload()` при обнаружении новой версии в package.json

**Решение:**
- Убрана автоматическая перезагрузка из `register-service-worker.js`
- Оставлен только `cache-manager` как единый источник обновлений
- Добавлена защита через `localStorage.lastReloadVersion` от зацикливания

**Файлы:**
- `src-pwa/register-service-worker.js` - убрана `window.location.reload(true)`
- `src/utils/cache-manager.js` - добавлена проверка `lastReloadVersion`
- `src-pwa/custom-service-worker.js` - исключены PHP-скрипты из перехвата SW

### 5. Синхронизация версий

**Проблема:** Версии в `package.json` (0.1.0) и `public/package.json` (0.1.1) были рассинхронизированы, что вызывало ложные срабатывания системы обновлений.

**Решение:**
- Синхронизированы все три места: `package.json`, `public/package.json`, `custom-service-worker.js`
- Создан скрипт `bump-version.sh` для автоматизации обновления версии

```bash
./bump-version.sh 0.5.0
```

Скрипт обновляет версию в:
1. `package.json`
2. `public/package.json` (копированием)
3. `src-pwa/custom-service-worker.js` (через sed)

### 6. Логирование

**Файл:** `public/orph.php`

Изменения:
- Создается папка `logs/` автоматически
- Логирование работает всегда (не зависит от `debug` настройки)
- Добавлен `.gitignore` в `public/logs/` для исключения логов из git
- Детальная запись всей SMTP-сессии

Debug-режим можно включить в `public/.smtp_config.php`:
```php
'debug' => true  // Для отладки
'debug' => false // Для production
```

## Технические детали

### SMTP-сессия

Полная валидация всех команд:
```php
// EHLO - ожидаем код 250
if (smtp_command($connection, "EHLO ...", 250) === false) return false;

// STARTTLS - ожидаем код 220
if (smtp_command($connection, "STARTTLS", 220) === false) return false;

// AUTH LOGIN - ожидаем код 334
if (smtp_command($connection, "AUTH LOGIN", 334) === false) return false;

// Username - ожидаем код 334
if (smtp_command($connection, base64_encode($username), 334) === false) return false;

// Password - ожидаем код 235
if (smtp_command($connection, base64_encode($password), 235) === false) return false;

// MAIL FROM - ожидаем код 250
if (smtp_command($connection, "MAIL FROM:<...>", 250) === false) return false;

// RCPT TO - ожидаем код 250
if (smtp_command($connection, "RCPT TO:<...>", 250) === false) return false;

// DATA - ожидаем код 354
if (smtp_command($connection, "DATA", 354) === false) return false;

// Сообщение - ожидаем код 250
if (smtp_command($connection, $message . "\r\n.", 250) === false) return false;

// QUIT - ожидаем код 221
smtp_command($connection, "QUIT", 221);
```

### Система версионирования PWA

Как работает:
1. **`__PACKAGE_VERSION__`** в браузере = версия из корневого `package.json` (через webpack define plugin)
2. **`/package.json`** на сервере = `public/package.json` (копируется в dist при сборке)
3. **`cache-manager.js`** каждые 30 минут сравнивает эти версии
4. При обнаружении разницы:
   - Очищает все кэши
   - Сохраняет версию в `localStorage.lastReloadVersion`
   - Перезагружает страницу **один раз**
   - При повторной загрузке проверяет `lastReloadVersion` - если совпадает, не перезагружает

## Проверка в production

**Дата проверки:** 2025-10-10  
**Версия:** 0.5.0

Результаты:
- ✅ Обновление прошло успешно
- ✅ Сообщения отправляются и доходят на почту
- ✅ Версия Service Worker обновилась корректно
- ✅ Бесконечных перезагрузок нет
- ✅ Пользователь получает мгновенную обратную связь

## Коммиты

1. **844b192** - Исправлена отправка сообщений об ошибках через orph.php
2. **3356c53** - Исправлено бесконечное обновление Service Worker
3. **97a9663** - Синхронизированы версии package.json и исправлена документация
4. **50a5b4a** - Добавлен скрипт bump-version.sh для автоматизации
5. **fa0c666** - Bump version to 0.5.0

## Дальнейшие обновления версии

Процесс обновления версии теперь автоматизирован:

```bash
# 1. Обновить версию
./bump-version.sh 0.6.0

# 2. Зафиксировать изменения
git add -u
git commit -m "Bump version to 0.6.0"

# 3. Собрать
quasar build -m pwa

# 4. Задеплоить на сервер
```

Скрипт автоматически обновит версию в трёх местах и предотвратит рассинхронизацию.

## Мониторинг

Для проверки работы системы в production:

1. **Логи SMTP** (временно включить debug):
   ```bash
   tail -f public/logs/mail_errors.log
   ```

2. **Service Worker** в DevTools:
   - Application → Service Workers
   - Должна быть версия с `CACHE_VERSION = v0.5.0`

3. **Console** в браузере:
   - Должны быть логи проверки обновлений каждые 30 минут
   - Не должно быть ошибок SMTP или зацикливаний

## Известные ограничения

1. **Dev-режим требует PHP сервер** - нужно запускать `./start-php-server.sh` перед `quasar dev`
2. **SMTP-сессия занимает ~32 секунды** - используется асинхронный подход, клиент не ждёт
3. **Обновления PWA происходят не мгновенно** - в течение 30 минут после деплоя
4. **Версии нужно синхронизировать вручную** - используйте `bump-version.sh`
