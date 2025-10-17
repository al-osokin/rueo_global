/*
 * This file (which will be your service worker)
 * is picked up by the build system ONLY if
 * quasar.conf > pwa > workboxPluginMode is set to "InjectManifest"
 */

// Workbox manifest injection point
// This will be replaced with the actual manifest during build
const manifest = self.__WB_MANIFEST || [];

// ВАЖНО: Версия должна совпадать с версией в package.json
// При изменении версии в package.json также обновите эту константу
const CACHE_VERSION = 'v1.0.0';
const CACHE_NAME = `quasar-pwa-${CACHE_VERSION}`;
const API_CACHE_NAME = `quasar-pwa-api-${CACHE_VERSION}`;

// Список URL, которые не должны кэшироваться
const EXTERNAL_URLS = [
  'reformal.ru',
  'mc.yandex.ru',
  'log.php'
];

// Список системных файлов, которые не должны кэшироваться
const SYSTEM_FILES = [
  '.htaccess',
  '.php',
  '.sql',
  '.db',
  'api-proxy',
  'robots.txt',
  'sitemap.xml'
];

self.addEventListener('install', event => {
  console.log('Service Worker installing...');
  // Кэшируем файлы из манифеста
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        // Фильтруем только локальные файлы (без внешних URL и системных файлов)
        const urlsToCache = manifest
          .filter(entry => entry && entry.url)
          .map(entry => entry.url)
          .filter(url => {
            // Исключаем внешние URL
            if (EXTERNAL_URLS.some(external => url.includes(external))) {
              return false;
            }
            // Исключаем системные файлы
            if (SYSTEM_FILES.some(system => url.includes(system))) {
              return false;
            }
            // Исключаем URL, которые начинаются с протокола (внешние ресурсы)
            if (url.startsWith('http://') || url.startsWith('https://')) {
              return false;
            }
            return true;
          })
          // Добавляем базовый URL для относительных путей
          .map(url => url.startsWith('/') ? url : '/' + url);
          
        console.log('Кэшируем файлы:', urlsToCache);
        
        // Пытаемся добавить файлы в кэш с обработкой ошибок
        return Promise.all(
          urlsToCache.map(url => {
            return fetch(url)
              .then(response => {
                if (response.ok) {
                  return cache.put(url, response);
                } else {
                  console.warn('Не удалось загрузить файл для кэширования:', url, response.status);
                  return Promise.resolve();
                }
              })
              .catch(error => {
                console.warn('Ошибка при кэшировании файла:', url, error);
                return Promise.resolve();
              });
          })
        ).then(() => {
          console.log('Кэширование завершено');
        });
      })
      .then(() => {
        // Пропускаем ожидание для немедленной активации
        console.log('Service Worker установлен');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('Ошибка при установке Service Worker:', error);
        // Продолжаем установку даже при ошибках кэширования
        return self.skipWaiting();
      })
  );
});

self.addEventListener('activate', event => {
  console.log('Service Worker activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(cacheName => cacheName !== CACHE_NAME && cacheName !== API_CACHE_NAME)
          .map(cacheName => {
            console.log('Удаляем старый кэш:', cacheName);
            return caches.delete(cacheName);
          })
      );
    }).then(() => {
      // Получаем контроль над всеми страницами
      console.log('Service Worker активирован');
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', event => {
  // Игнорируем не-HTTP запросы, внешние трекеры и PHP скрипты
  if (!event.request.url.startsWith('http') || 
      EXTERNAL_URLS.some(external => event.request.url.includes(external)) ||
      event.request.url.includes('.php')) {
    return;
  }

  // Для API запросов используем network-first стратегию с кэшированием
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Кэшируем только успешные ответы
          if (response.ok) {
            const responseToCache = response.clone();
            caches.open(API_CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
          }
          return response;
        })
        .catch(() => {
          // Если сеть недоступна, возвращаем из кэша
          return caches.match(event.request);
        })
    );
  }
  // Для статических файлов из манифеста используем cache-first стратегию
  else if (manifest.some(entry => entry && entry.url === event.request.url)) {
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          // Возвращаем из кэша, если есть
          if (response) {
            return response;
          }
          // Иначе загружаем из сети
          return fetch(event.request)
            .then(response => {
              // Кэшируем только успешные ответы
              if (response.ok) {
                const responseToCache = response.clone();
                caches.open(CACHE_NAME)
                  .then(cache => {
                    cache.put(event.request, responseToCache);
                  });
              }
              return response;
            });
        })
    );
  }
  // Для остальных запросов используем network-only
  else {
    return;
  }
});

// Обработка сообщений от приложения
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
