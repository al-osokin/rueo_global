/*
 * Cache Manager для автоматической проверки обновлений
 */

class CacheManager {
  constructor() {
    // Получаем версию из package.json через webpack define plugin
    this.currentVersion = typeof __PACKAGE_VERSION__ !== 'undefined' ? __PACKAGE_VERSION__ : '0.0.3';
    // Флаг для предотвращения множественных перезагрузок
    this.isChecking = false;
    // Флаг для предотвращения зацикливания перезагрузок
    this.reloadAttempted = false;
  }

  // Проверка версии через fetch API
  async checkForUpdates() {
    // Предотвращаем одновременные проверки
    if (this.isChecking) {
      return false;
    }
    
    // Предотвращаем повторные попытки перезагрузки
    if (this.reloadAttempted) {
      return false;
    }
    
    this.isChecking = true;
    
    try {
      // В продакшене package.json находится в корне
      const packagePath = '/package.json';
      
      const response = await fetch(packagePath, {
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache',
          'Expires': '0'
        }
      });
      
      if (response.ok) {
        const packageJson = await response.json();
        const serverVersion = packageJson.version;
        
        if (serverVersion && serverVersion !== this.currentVersion) {
          console.log(`Доступна новая версия: ${serverVersion} (текущая: ${this.currentVersion})`);
          
          // Дополнительная проверка: убеждаемся, что можем снова получить доступ к package.json
          // перед очисткой кэша и перезагрузкой
          const verifyResponse = await fetch(packagePath, {
            cache: 'no-cache',
            headers: {
              'Cache-Control': 'no-cache',
              'Pragma': 'no-cache',
              'Expires': '0'
            }
          });
          
          if (verifyResponse.ok) {
            await this.clearAllCaches();
            this.isChecking = false;
            return true;
          } else {
            console.log('Не удалось подтвердить доступ к package.json, отмена перезагрузки');
            this.isChecking = false;
            return false;
          }
        }
      }
      this.isChecking = false;
      return false;
    } catch (error) {
      console.log('Ошибка проверки обновлений:', error);
      this.isChecking = false;
      // Если не можем получить доступ к package.json, не пытаемся перезагружаться
      return false;
    }
  }

  // Очистка всех кэшей
  async clearAllCaches() {
    try {
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(
          cacheNames.map(name => caches.delete(name))
        );
        console.log('Все кэши очищены');
      }
      
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();
        if (registration) {
          await registration.unregister();
          console.log('Service Worker отменен');
        }
      }
    } catch (error) {
      console.error('Ошибка очистки кэшей:', error);
    }
  }

  // Принудительное обновление страницы
  forceReload() {
    console.log('forceReload вызван');
    
    // В dev-режиме не перезагружаем автоматически
    if (process.env.NODE_ENV !== 'production') {
      console.log('Dev-режим: пропускаем автоматическую перезагрузку');
      return;
    }
    
    // Предотвращаем множественные попытки перезагрузки
    if (this.reloadAttempted) {
      console.log('Перезагрузка уже выполнялась, пропускаем');
      return;
    }
    
    // Сохраняем флаг в localStorage для предотвращения зацикливания между сессиями
    const lastReloadVersion = localStorage.getItem('lastReloadVersion');
    if (lastReloadVersion === this.currentVersion) {
      console.log('Уже перезагружались на эту версию, пропускаем');
      return;
    }
    
    this.reloadAttempted = true;
    localStorage.setItem('lastReloadVersion', this.currentVersion);
    
    console.log('Перезагрузка страницы для применения обновлений...');
    
    // Добавляем небольшую задержку перед перезагрузкой
    setTimeout(() => {
      window.location.reload(true);
    }, 1000);
  }

  // Сброс флага перезагрузки (вызывается при успешной загрузке страницы)
  resetReloadFlag() {
    this.reloadAttempted = false;
  }

  // Отправка сообщения Service Worker для пропуска ожидания
  async skipWaiting() {
    if ('serviceWorker' in navigator) {
      const registration = await navigator.serviceWorker.getRegistration();
      if (registration && registration.waiting) {
        registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
    }
  }
}

// Экспортируем экземпляр менеджера кэша
export default new CacheManager();
