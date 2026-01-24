<template>
  <q-page padding>
    <!-- content -->
    <component :is="`Page${page}`"></component>
    <ol class="wrap">
      <li v-for="(i,index) in listOfPages"
          :key="index">
        <router-link :to="{name:'grammar',params:{page:index+1}}">{{ i }}</router-link>
      </li>
    </ol>
    <!--    <ul class="wrap">-->
    <!--      <li v-for="i in 7"-->
    <!--          :key=i>-->
    <!--        <router-link :to="{name:'gram', params:{page:i}}">Страница {{ i }}</router-link>-->
    <!--        <q-btn :to="{name:'gram', params:{page:i}}" flat exact>Страница {{ i }}</q-btn>-->
    <!--      </li>-->
    <!--    </ul>-->
  </q-page>
</template>
<script>
import {defineAsyncComponent} from 'vue';
import {createMetaMixin} from 'quasar';

export default {
  name: 'Grammar',
  components: {
    Page1: defineAsyncComponent(() => import('components/gram/page1.vue')),
    Page2: defineAsyncComponent(() => import('components/gram/page2.vue')),
    Page3: defineAsyncComponent(() => import('components/gram/page3.vue')),
    Page4: defineAsyncComponent(() => import('components/gram/page4.vue')),
    Page5: defineAsyncComponent(() => import('components/gram/page5.vue')),
    Page6: defineAsyncComponent(() => import('components/gram/page6.vue')),
    Page7: defineAsyncComponent(() => import('components/gram/page7.vue')),
    Page8: defineAsyncComponent(() => import('components/gram/page8.vue')),
    Page9: defineAsyncComponent(() => import('components/gram/page9.vue')),
    Page10: defineAsyncComponent(() => import('components/gram/page10.vue')),
    Page11: defineAsyncComponent(() => import('components/gram/page11.vue')),
    Page12: defineAsyncComponent(() => import('components/gram/page12.vue')),
    Page13: defineAsyncComponent(() => import('components/gram/page13.vue')),
    Page14: defineAsyncComponent(() => import('components/gram/page14.vue')),
    Page15: defineAsyncComponent(() => import('components/gram/page15.vue')),
    Page16: defineAsyncComponent(() => import('components/gram/page16.vue')),
    Page17: defineAsyncComponent(() => import('components/gram/page17.vue')),
    Page18: defineAsyncComponent(() => import('components/gram/page18.vue')),

  },
  data() {
    return {
      listOfPages: [
        'Алфавит. Произношение',
        'Словарный состав',
        'Передача национальных имён',
        'Морфология и словообразование',
        'Имя существительное',
        'Имя прилагательное',
        'Наречие',
        'Местоимения',
        'Числительные',
        'Глагол',
        'Артикль',
        'Служебные части речи',
        'Синтаксис',
        'Пунктуация',
        'Стиль',
        'О пользовании словарём',
        'Условные обозначения',
        'Использованные источники'],
    };
  },
  mixins: [
    createMetaMixin(function() {
      return {
        title: `Эсперанто словари Бориса Кондратьева | Грамматика - ${this.listOfPages[this.page - 1]}`,
        meta: {
          description: {
            name: 'description',
            content: 'Грамматика международного языка Эсперанто, описанная в эсперанто-русском словаре Бориса Кондратьева',
          },
          keywords: {
            name: 'keywords',
            content: 'Эсперанто, международный язык, грамматика, алфавит, произношение, глагол, синтаксис, морфология, о пользовании словарём, пунктуация',
          },
          equiv: {'http-equiv': 'Content-Type', content: 'text/html; charset=UTF-8'},
        },
      };
    }),
  ],
  computed: {
    page: function() {
      return this.$route.params.page || '1';
    },
  },
};
</script>
