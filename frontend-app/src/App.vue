<template>
  <router-view />
</template>

<script>
import { defineComponent } from 'vue';
import cacheManager from './utils/cache-manager';

export default defineComponent({
  name: 'App',
  
  data() {
    return {
      updateCheckCount: 0,
      maxUpdateChecks: 5 // Максимальное количество проверок перед остановкой
    }
  },
  
  async mounted() {
    // Сбрасываем флаг перезагрузки при успешной загрузке страницы
    cacheManager.resetReloadFlag();
    
    // Проверяем обновления при загрузке приложения только в production
    if (process.env.NODE_ENV === 'production') {
      await this.checkForUpdates();
      
      // Периодически проверяем обновления каждые 30 минут
      setInterval(async () => {
        if (this.updateCheckCount < this.maxUpdateChecks) {
          await this.checkForUpdates();
          this.updateCheckCount++;
        }
      }, 30 * 60 * 1000); // 30 минут
    }
  },
  
  methods: {
    async checkForUpdates() {
      try {
        const hasUpdates = await cacheManager.checkForUpdates();
        if (hasUpdates) {
          // Если есть обновления, перезагружаем страницу
          console.log('Перезагрузка страницы для применения обновлений...');
          cacheManager.forceReload();
        }
      } catch (error) {
        console.log('Ошибка при проверке обновлений:', error);
      }
    }
  }
})
</script>
