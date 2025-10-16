<template>
  <q-page padding>
    <!-- content -->
    <div class="flex justify-between items-center">
      <h1>От автора</h1>
      <p class="no-margin q-py-md"><em>Предисловие к эсперанто-русскому словарю</em></p>
    </div>
    <transition>
      <component :is="`Page${currentPage}`"></component>
    </transition>
    <q-pagination
      v-model="currentPage"
      :max="7"
      class="justify-center"
      color="green"
      direction-links
      push
    />
    <!--    <ul class="wrap">-->
    <!--      <li v-for="i in 7"-->
    <!--          :key=i>-->
    <!--        <router-link :to="{name:'about', params:{page:i}}">Страница {{ i }}</router-link>-->
    <!--        <q-btn :to="{name:'about', params:{page:i}}" flat exact>Страница {{ i }}</q-btn>-->
    <!--      </li>-->
    <!--    </ul>-->
  </q-page>
</template>
<script>
import {defineAsyncComponent} from 'vue';
import {createMetaMixin} from 'quasar';

export default {
  name: 'About',
  components: {
    Page1: defineAsyncComponent(() => import('components/about/page1')),
    Page2: defineAsyncComponent(() => import('components/about/page2')),
    Page3: defineAsyncComponent(() => import('components/about/page3')),
    Page4: defineAsyncComponent(() => import('components/about/page4')),
    Page5: defineAsyncComponent(() => import('components/about/page5')),
    Page6: defineAsyncComponent(() => import('components/about/page6')),
    Page7: defineAsyncComponent(() => import('components/about/page7')),

  },
  data() {
    return {
      currentPage: 1,
    };
  },
  mixins: [
    createMetaMixin(function() {
      return {
        title: `Эсперанто словари Бориса Кондратьева | От автора - Страница ${this.currentPage}`,
        meta: {
          description: {name: 'description', content: 'Предисловие Бориса Кондратьева к эсперанто-русскому словарю'},
          keywords: {
            name: 'keywords',
            content: 'история, причина, словарь, актуальность, эсперанто, эсперантская грамматика, словоупотребление',
          },
          equiv: {'http-equiv': 'Content-Type', content: 'text/html; charset=UTF-8'},
        },
      };
    }),
  ],
  created() {
    this.currentPage = +(this.$route.params.page || '1');
  },
  computed: {
    // page: function() {
    //   return this.$route.params.page || '1';
    // },
  },
  watch: {
    '$route.params.page': {
      handler(val) {
        this.currentPage = +(val || '1');
      },
      deep: true,
    },
    currentPage: function(val) {
      if (this.$route.name === 'about' || this.$route.name === 'aboutMain') {
        if (val) {
          this.$router.push({name: 'about', params: {page: val}});
        } else this.$router.push({name: 'aboutMain'});
      }
    },
  },
};
</script>
