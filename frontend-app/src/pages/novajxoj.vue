<template>
  <q-page class="flex justify-start content-start wrap" padding>
    <div class="flex fit justify-between items-center q-mb-md">
      <h1>Все новости проекта</h1>
    </div>

    <NewsFeed
      :enable-pagination="true"
      :items-per-page="itemsPerPage"
      :current-page="currentPage"
      :max-items="1000"
      @page-change="handlePageChange"
      @items-per-page-change="handleItemsPerPageChange"
    />
  </q-page>
</template>

<script>
import NewsFeed from 'components/NewsFeed.vue'

export default {
  name: 'NovajxojPage',
  components: { NewsFeed },
  data() {
    return {
      currentPage: 1,
      itemsPerPage: 10
    }
  },
  methods: {
    handlePageChange(page) {
      this.currentPage = page
    },
    handleItemsPerPageChange(itemsPerPage) {
      this.itemsPerPage = itemsPerPage
      this.currentPage = 1 // Reset to first page when changing items per page
    }
  },
  meta() {
    return {
      title: 'Все новости проекта | Веб-словарь эсперанто'
    }
  }
}
</script>

<style scoped>
</style>
