<template>
  <div class="news-feed q-mt-md">
    <div v-if="showTitle" class="q-mb-md">
      <div class="flex justify-between items-center">
        <h3>Новости проекта</h3>
        <div class="flex items-center q-gutter-sm">
          <q-btn
            v-if="!loading"
            icon="refresh"
            size="sm"
            flat
            round
            color="green"
            @click="refreshNews"
            :loading="loading"
          >
            <q-tooltip>Обновить новости</q-tooltip>
          </q-btn>
          <q-btn
            icon="settings"
            size="sm"
            flat
            round
            color="grey-6"
            @click="toggleAutoUpdate"
          >
            <q-tooltip>{{ autoUpdateEnabled ? 'Отключить автообновление' : 'Включить автообновление' }}</q-tooltip>
          </q-btn>
        </div>
      </div>
      <div v-if="lastUpdate" class="text-caption text-grey-6 q-mt-xs">
        Обновлено: {{ formatLastUpdate(lastUpdate) }}
      </div>
    </div>
    <div v-if="loading" class="text-center q-pa-md">
      <q-spinner color="primary" size="3em" />
    </div>
    <div v-else-if="error" class="text-negative q-pa-md">
      Не удалось загрузить новости
    </div>
    <div v-else-if="visibleNewsSections.length === 0" class="text-grey q-pa-md">
      Новостей пока нет
    </div>
    <div v-else>
      <!-- Controls for pagination -->
      <div v-if="enablePagination" class="q-mb-md flex justify-between items-center">
        <q-select
          v-model="internalItemsPerPage"
          :options="itemsPerPageOptions"
          label="Новостей на странице"
          outlined
          dense
          style="min-width: 200px"
          @update:model-value="handleItemsPerPageChange"
          color="green"
        />
        <div class="text-caption text-grey-7">
          Показано {{ newsItems.length }} из {{ allNewsItems.length }} новостей
        </div>
      </div>

      <q-card
        v-for="section in visibleNewsSections"
        :key="section.id"
        class="news-card q-mb-md"
        flat
        bordered
      >
        <q-card-section class="news-section-title-section">
          <h1 class="news-section-title">{{ section.title }}</h1>
        </q-card-section>
        <q-card-section v-if="section.introHtml" class="q-pt-none">
          <div class="news-content" v-html="section.introHtml"></div>
        </q-card-section>
        <q-card-section
          v-for="item in section.items"
          :key="item.id"
          class="news-item-section"
        >
          <h2 class="news-item-title">{{ item.title }}</h2>
          <div class="news-content" v-html="item.content"></div>
        </q-card-section>
      </q-card>

      <!-- Pagination -->
      <div v-if="enablePagination && totalPages > 1" class="flex justify-center q-mt-lg">
        <q-pagination
          v-model="internalCurrentPage"
          :max="totalPages"
          color="green"
          size="md"
          @update:model-value="handlePageChange"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { api } from 'boot/axios'
import MarkdownIt from 'markdown-it'

export default {
  name: 'NewsFeed',
  props: {
    showTitle: {
      type: Boolean,
      default: true
    },
    maxItems: {
      type: Number,
      default: 5
    },
    itemsPerPage: {
      type: Number,
      default: 10
    },
    currentPage: {
      type: Number,
      default: 1
    },
    enablePagination: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      newsSections: [],
      allNewsItems: [],
      loading: false,
      error: false,
      internalCurrentPage: 1,
      internalItemsPerPage: 10,
      lastUpdate: null,
      updateInterval: null,
      autoUpdateEnabled: true,
      newsSourceText: ''
    }
  },
  computed: {
    newsItems() {
      if (!this.enablePagination) {
        return this.allNewsItems.slice(0, this.maxItems)
      }

      const start = (this.currentPage - 1) * this.itemsPerPage
      const end = start + this.itemsPerPage
      return this.allNewsItems.slice(start, end)
    },
    visibleNewsSections() {
      const visibleItemIds = new Set(this.newsItems.map(item => item.id))
      const showIntroSections = !this.enablePagination || this.currentPage === 1

      return this.newsSections
        .map(section => {
          const items = section.items.filter(item => visibleItemIds.has(item.id))
          const introHtml = showIntroSections ? section.introHtml : ''

          return {
            ...section,
            introHtml,
            items
          }
        })
        .filter(section => section.introHtml || section.items.length > 0)
    },
    totalPages() {
      if (!this.enablePagination) return 1
      return Math.ceil(this.allNewsItems.length / this.itemsPerPage)
    },
    itemsPerPageOptions() {
      return [
        { label: '10 новостей', value: 10 },
        { label: '20 новостей', value: 20 },
        { label: '50 новостей', value: 50 }
      ]
    }
  },
  watch: {
    currentPage() {
      this.internalCurrentPage = this.currentPage
    },
    itemsPerPage() {
      this.internalItemsPerPage = this.itemsPerPage
    }
  },
  async mounted() {
    await this.loadNews()
    this.startAutoUpdate()
  },
  beforeUnmount() {
    this.stopAutoUpdate()
  },
  methods: {
    async loadNews() {
      this.loading = true
      this.error = false

      try {
        const text = await this.fetchNewsText()
        const newsData = this.parseMarkdownNews(text)
        this.newsSections = newsData.sections
        this.allNewsItems = newsData.items
        this.newsSourceText = text
        this.lastUpdate = new Date()
      } catch (error) {
        console.error('Error loading news:', error)
        this.error = true
      } finally {
        this.loading = false
      }
    },

    async fetchNewsText() {
      const url = `/news.md?ts=${Date.now()}`
      const response = await fetch(url, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache',
          'Expires': '0'
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return response.text()
    },

    handlePageChange(page) {
      this.internalCurrentPage = page
      this.$emit('page-change', page)
    },

    handleItemsPerPageChange(value) {
      this.internalItemsPerPage = value
      this.internalCurrentPage = 1 // Reset to first page when changing items per page
      this.$emit('items-per-page-change', value)
      this.$emit('page-change', 1)
    },
    
    parseMarkdownNews(markdownContent) {
      const md = new MarkdownIt({
        html: true,
        linkify: true,
        typographer: true
      })

      const sections = []
      const newsItems = []
      let currentSection = null
      let currentItem = null

      const renderLines = lines => {
        const content = lines.join('\n').trim()
        return content ? md.render(content) : ''
      }

      const ensureSection = () => {
        if (!currentSection) {
          currentSection = {
            id: `section-${sections.length}`,
            title: 'Новости',
            introLines: [],
            introHtml: '',
            items: []
          }
          sections.push(currentSection)
        }

        return currentSection
      }

      const finalizeItem = () => {
        if (!currentItem) return

        const item = {
          id: `news-${newsItems.length}`,
          sectionId: currentSection.id,
          title: currentItem.title,
          content: renderLines(currentItem.contentLines)
        }

        currentSection.items.push(item)
        newsItems.push(item)
        currentItem = null
      }

      const finalizeSectionIntro = section => {
        if (section && !section.introHtml) {
          section.introHtml = renderLines(section.introLines)
        }
      }

      const lines = markdownContent.split('\n')

      for (const rawLine of lines) {
        const line = rawLine.replace(/\s+$/, '')
        const trimmedLine = line.trim()

        if (trimmedLine === '---') {
          continue
        }

        const sectionMatch = line.match(/^#\s+(.+)$/)
        if (sectionMatch) {
          finalizeItem()
          finalizeSectionIntro(currentSection)

          currentSection = {
            id: `section-${sections.length}`,
            title: sectionMatch[1].trim(),
            introLines: [],
            introHtml: '',
            items: []
          }
          sections.push(currentSection)
          continue
        }

        const itemMatch = line.match(/^##\s+(.+)$/)
        if (itemMatch) {
          const section = ensureSection()
          finalizeItem()
          finalizeSectionIntro(section)
          currentItem = {
            title: itemMatch[1].trim(),
            contentLines: []
          }
          continue
        }

        if (currentItem) {
          currentItem.contentLines.push(line)
        } else {
          ensureSection().introLines.push(line)
        }
      }

      finalizeItem()
      finalizeSectionIntro(currentSection)

      return {
        sections: sections.filter(section => section.introHtml || section.items.length > 0),
        items: newsItems
      }
    },

    async refreshNews() {
      await this.loadNews()
      this.lastUpdate = new Date()
      this.$q.notify({
        message: 'Новости обновлены',
        color: 'green',
        icon: 'check_circle',
        position: 'top-right',
        timeout: 2000
      })
    },

    toggleAutoUpdate() {
      this.autoUpdateEnabled = !this.autoUpdateEnabled
      if (this.autoUpdateEnabled) {
        this.startAutoUpdate()
        this.$q.notify({
          message: 'Автообновление включено',
          color: 'green',
          icon: 'sync',
          position: 'top-right',
          timeout: 2000
        })
      } else {
        this.stopAutoUpdate()
        this.$q.notify({
          message: 'Автообновление отключено',
          color: 'grey-7',
          icon: 'sync_disabled',
          position: 'top-right',
          timeout: 2000
        })
      }
    },

    startAutoUpdate() {
      if (this.autoUpdateEnabled && !this.updateInterval) {
        // Проверяем обновления каждые 3 часа
        this.updateInterval = setInterval(async () => {
          try {
            const text = await this.fetchNewsText()

            if (text !== this.newsSourceText) {
              const newsData = this.parseMarkdownNews(text)
              this.newsSections = newsData.sections
              this.allNewsItems = newsData.items
              this.newsSourceText = text
              this.lastUpdate = new Date()
              this.$q.notify({
                message: 'Появились новые новости!',
                color: 'green',
                icon: 'newspaper',
                position: 'top-right',
                timeout: 3000
              })
            }
          } catch (error) {
            console.error('Error checking for news updates:', error)
          }
        }, 3 * 60 * 60 * 1000) // 3 часа
      }
    },

    stopAutoUpdate() {
      if (this.updateInterval) {
        clearInterval(this.updateInterval)
        this.updateInterval = null
      }
    },

    formatLastUpdate(date) {
      const now = new Date()
      const diff = now - date
      const minutes = Math.floor(diff / (1000 * 60))
      const hours = Math.floor(diff / (1000 * 60 * 60))

      if (minutes < 1) {
        return 'только что'
      } else if (minutes < 60) {
        return `${minutes} мин назад`
      } else if (hours < 24) {
        return `${hours} ч назад`
      } else {
        return date.toLocaleDateString('ru-RU', {
          day: 'numeric',
          month: 'short',
          hour: '2-digit',
          minute: '2-digit'
        })
      }
    }

  }
}
</script>

<style scoped>
.news-card {
  max-width: 100%;
}

.news-section-title {
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.25;
  margin: 0;
  color: #324d5b;
}

.news-item-section {
  padding-top: 0;
}

.news-item-section + .news-item-section {
  border-top: 1px solid #e0e0e0;
  padding-top: 1rem;
}

.news-item-title {
  font-size: 1.3rem;
  font-weight: 600;
  line-height: 1.3;
  margin: 0 0 0.5rem 0;
  color: #324d5b;
}

.news-card .text-subtitle2 {
  font-size: 0.9rem;
}

/* Стили для заголовков в контенте новостей */
.news-content :deep(h1) {
  font-size: 1.5rem;
  font-weight: 600;
  margin: 1rem 0 0.5rem 0;
  color: #324d5b;
}

.news-content :deep(h2) {
  font-size: 1.3rem;
  font-weight: 600;
  margin: 1rem 0 0.5rem 0;
  color: #324d5b;
}

.news-content :deep(h3) {
  font-size: 1.2rem;
  font-weight: 600;
  margin: 0.8rem 0 0.4rem 0;
  color: #1976d2;
}

.news-content :deep(h4) {
  font-size: 1.1rem;
  font-weight: 500;
  margin: 0.8rem 0 0.4rem 0;
  color: #424242;
}

.news-content :deep(h5) {
  font-size: 1rem;
  font-weight: 500;
  margin: 0.6rem 0 0.3rem 0;
  color: #616161;
}

.news-content :deep(h6) {
  font-size: 0.95rem;
  font-weight: 500;
  margin: 0.6rem 0 0.3rem 0;
  color: #757575;
}

.news-content :deep(p) {
  margin: 0.5rem 0;
  line-height: 1.5;
}

.news-content :deep(ul), .news-content :deep(ol) {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.news-content :deep(li) {
  margin: 0.25rem 0;
}

.news-content :deep(blockquote) {
  border-left: 4px solid #e0e0e0;
  padding-left: 1rem;
  margin: 1rem 0;
  color: #666;
  font-style: italic;
}

.news-content :deep(code) {
  background-color: #f5f5f5;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.news-content :deep(pre) {
  background-color: #f5f5f5;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  margin: 1rem 0;
}

.news-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.news-content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 1rem 0;
}

.news-content :deep(th), .news-content :deep(td) {
  border: 1px solid #ddd;
  padding: 0.5rem;
  text-align: left;
}

.news-content :deep(th) {
  background-color: #f5f5f5;
  font-weight: 600;
}

@media (max-width: 599px) {
  .news-section-title {
    font-size: 1.3rem;
  }

  .news-item-title {
    font-size: 1.2rem;
  }

  .news-card .text-subtitle2 {
    font-size: 0.8rem;
  }

  .news-content :deep(h1) {
    font-size: 1.3rem;
  }

  .news-content :deep(h2) {
    font-size: 1.2rem;
  }

  .news-content :deep(h3) {
    font-size: 1.1rem;
  }

  .news-content :deep(h4) {
    font-size: 1rem;
  }
}
</style>
