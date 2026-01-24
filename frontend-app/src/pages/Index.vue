<template>
  <q-page class="flex justify-start content-start wrap" padding>
    <div class="flex fit justify-between items-center">
      <div>
        <h1 v-if="showCaptions">Большие словари Бориса Кондратьева</h1>
        <h1 v-else>Веб-словарь</h1>
      </div>
      <div>
        <p v-if="dateCaption" class="no-margin q-py-md">
          <em>{{ dateCaption }}</em>
        </p>
      </div>
    </div>
    <div class="flex-break" />
    <q-form
      class="flex full-width no-wrap"
      @reset="resetForm"
      @submit="searchPhrase = temporaryWord"
    >
      <q-btn
        class="q-mr-xs"
        color="grey-4"
        icon="send"
        outline
        padding="sm"
        size="md"
        text-color="grey-8"
        type="submit"
      ></q-btn>
      <q-btn
        class="q-mr-xs"
        color="grey-4"
        icon="close"
        outline
        padding="sm"
        size="md"
        text-color="grey-8"
        type="reset"
      ></q-btn>
      <q-select
        ref="searchField"
        v-model="searchPhrase"
        :class="{ 'text-h5': $q.screen.gt.sm, 'text-h6': !$q.screen.gt.sm }"
        :options="listOfWords"
        behavior="menu"
        color="green"
        emit-value
        fill-input
        hide-selected
        input-debounce="100"
        label="Введите слово"
        new-value-mode="add-unique"
        outlined
        style="width: 100%; min-width: 0"
        tabindex="1"
        use-input
        @filter="onWriteToSelectArea"
      >
        <template v-slot:no-option>
          <q-item>
            <q-item-section class="text-grey"> Нет результата </q-item-section>
          </q-item>
        </template>
      </q-select>
    </q-form>
    <div class="flex-break" />
    <div
      ref="search_result"
      v-if="$route.path !== '/'"
      class="search_result fit"
    >
      <transition-group appear name="search">
        <div
          v-for="(el, idx) in processedHistorySlots"
          :key="el.word + el.date"
          class="dictionary-article shadow-1 q-my-md q-pa-md"
        >
          <q-btn
            v-if="idx > 0"
            icon="close"
            @click="removeHistoryItem(el)"
            dense
            flat
            class="dictionary-article__remove-button"
          >
            <q-tooltip> Удалить из истории </q-tooltip>
          </q-btn>
          <div v-html="el.processedBody"></div>
        </div>
      </transition-group>
    </div>
    <div class="flex-break" />
    <h3 v-if="showCaptions">Открыты для поиска:</h3>
    <div class="flex-break" />
    <ul v-if="showCaptions">
      <li v-for="(item, index) in filteredLiCaption" :key="index">
        {{ item }}
      </li>
    </ul>
    <div v-show="showCaptions" class="wrap full-width">
      <NewsFeed v-if="showCaptions" :maxItems="5" />

      <!-- Кнопка для перехода ко всем новостям -->
      <div v-if="showCaptions" class="flex justify-center q-mt-md">
        <q-btn
          color="green"
          outline
          label="Показать все новости"
          @click="$router.push('/novajxoj')"
          icon="article"
          class="q-px-lg"
        />
      </div>
    </div>
  </q-page>
</template>
<script>
import { api } from "boot/axios";
import { createMetaMixin, date } from "quasar";
import { replacementsDictionary } from "src/utils/replacements";
import NewsFeed from "components/NewsFeed.vue";

export default {
  name: "PageIndex",
  components: { NewsFeed },
  setup() {
    let date;
    const getDictionaryDate = async () => {
      console.log("Запрос к API: /status/info");
      return await api.get("/status/info");
    };

    return {
      getDictionaryDate,
    };
  },
  mixins: [
    createMetaMixin(function () {
      return {
        title: `Эсперанто словари Бориса Кондратьева${
          this.$route.name === "dictionaryEmpty"
            ? " | Веб-словарь"
            : this.$route.name === "dictionary"
            ? " | Веб-словарь | " + this.searchPhrase
            : ""
        }`,
        meta: {
          description: {
            name: "description",
            content:
              "Веб-интерфейс для поиска по эсперанто-русскому и русско-эсперантскому словарям Кондратьева",
          },
          keywords: {
            name: "keywords",
            content:
              "веб-словарь эсперанто, эсперанто словарь онлайн, искать, русский, эсперанто, словарь, найти, слово",
          },
          equiv: {
            "http-equiv": "Content-Type",
            content: "text/html; charset=UTF-8",
          },
        },
      };
    }),
  ],
  computed: {
    dateCaption: function () {
      return this.respDate || "";
    },
    liCaption: function () {
      return this.respLi.length
        ? this.respLi
        : [
            "большой эсперанто-русский словарь в актуальной редакции, 92492 слова в 46265 словарных статьях;",
            "рабочие материалы большого русско-эсперантского словаря (диапазон А — правнучка), 51060 слов в 31461 словарной статье.",
          ];
    },
    filteredLiCaption: function () {
      return this.liCaption.filter((item) => {
        if (!item) {
          return false;
        }
        return !item.toLowerCase().startsWith("открыты для поиска");
      });
    },
    showCaptions: function () {
      return !(
        this.$route.name === "dictionary" ||
        this.$route.name === "dictionaryEmpty"
      );
    },
    // Вычисляемое свойство для обработки постоянных ссылок в реальном времени
    processedHistorySlots: function() {
      return this.historySlots.map(slot => ({
        ...slot,
        processedBody: this.processPermalinkUrls(slot.body)
      }));
    }
  },
  data() {
    return {
      searchPhrase: "",
      listOfWords: [],
      respDate: "",
      respLi: [],
      temporaryWord: "",
      historySlots: [],
      historyLength: 20,
    };
  },
  created() {
    if (this.$route.params.word) {
      // Заменяем плюсы на пробелы для корректного отображения в поисковой строке
      this.searchPhrase = this.$route.params.word.replace(/\+/g, ' ');
    }
  },

  async mounted() {
    let value = this.$q.localStorage.getItem("rueo_history");
    if (value) {
      this.historySlots = JSON.parse(value);
    }

    try {
      const resp = await this.getDictionaryDate();
      if (resp.status === 200 && resp.data) {
        const text = resp.data.text || "";
        const lines = text
          .split("\n")
          .map((line) => line.trim())
          .filter((line) => line.length > 0);
        if (lines.length) {
          const firstLine = lines[0];
          this.respDate =
            firstLine &&
            !firstLine.toLowerCase().startsWith("открыты для поиска")
              ? firstLine
              : "";
          if (lines.length > 1) {
            this.respLi = lines.slice(1);
          }
        }
      }
    } catch (error) {
      console.error("Не удалось получить информацию о словаре:", error);
    }
    this.$refs.searchField.focus();
    this.$nextTick(() => this.addTooltip());
  },

    methods: {
    // Функция для замены пробелов на + только в постоянных ссылках
    processPermalinkUrls(htmlContent) {
      // Создаем временный DOM элемент для парсинга HTML
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = htmlContent;
      
      // Ищем все ссылки
      const allLinks = tempDiv.querySelectorAll('a[href]');
      
      allLinks.forEach(link => {
        let href = link.getAttribute('href');
        
        if (href && (href.includes('sercxo') || href.includes('rueo.ru'))) {
          // Проверяем различные варианты кодирования пробелов
          let newHref = href;
          let changed = false;
          
          // Если есть %2520 (закодированный %20)
          if (href.includes('%2520')) {
            newHref = href.replace(/%2520/g, '+');
            changed = true;
          }
          // Если есть %20 (простой пробел в URL)
          else if (href.includes('%20')) {
            newHref = href.replace(/%20/g, '+');
            changed = true;
          }
          // Если есть обычные пробелы (браузер может их отображать как есть)
          else if (href.includes(' ')) {
            newHref = href.replace(/\s+/g, '+');
            changed = true;
          }
          
          if (changed) {
            link.setAttribute('href', newHref);
          }
        }
      });
      
      return tempDiv.innerHTML;
    },
    removeHistoryItem(el) {
      // Удаляем из оригинального массива, так как processedHistorySlots - это вычисляемое свойство
      this.historySlots = [...this.historySlots].filter((item) => {
        return item.date !== el.date;
      });
      this.saveHistory();
    },
    saveHistory: function () {
      this.$q.localStorage.set(
        "rueo_history",
        JSON.stringify(this.historySlots)
      );
    },
    async submitInputSelect(val) {
      console.log("Запрос поисковых подсказок для:", val);
      try {
        const resp = await api.get("/suggest", {
          params: { term: val.trim() },
        });
        console.log("Ответ поисковых подсказок:", resp);
        if (resp.status === 200 && Array.isArray(resp.data)) {
          this.listOfWords = resp.data.map((item) =>
            typeof item === "string"
              ? { label: item, value: item }
              : {
                  label: item.label ?? item.value ?? "",
                  value: item.value ?? item.label ?? "",
                }
          );
          console.log("Установлены поисковые подсказки:", this.listOfWords);
        } else {
          console.warn(
            "Ожидался массив подсказок, но получен другой тип:",
            typeof resp.data
          );
          this.listOfWords = [];
        }
      } catch (error) {
        console.error("Ошибка получения поисковых подсказок:", error);
        this.listOfWords = [];
      }
    },
    onWriteToSelectArea: async function (val, update, abort) {
      if (val && val?.length > 0) {
        // await this.$router.replace({name: 'dictionary', params: {word: val}});
        this.temporaryWord = val;
        await this.submitInputSelect(val);
        update();
      }
      abort();
    },
    async submitSelectedWord(val) {
      console.log("Запрос поиска слова:", val);
      if (val && val?.length > 0) {
        await this.$router.replace({
          name: "dictionary",
          params: { word: val },
        });
        const word = val.trim();

        try {
          const resp = await api.get("/search", {
            params: { query: word },
            timeout: 15000,
          });
          console.log("Ответ поиска слова:", resp);

          if (resp.status === 200 && resp.data) {
            const { count, html, fuzzy_html: fuzzyHtml } = resp.data;
            const timeStamp = Date.now();
            const humanDate = date.formatDate(
              timeStamp,
              "YYYY-MM-DD-HH-mm-ss"
            );

            if (count > 0 && html) {
              const processedHtml = this.processPermalinkUrls(
                `${html}${fuzzyHtml || ""}`
              );

              const newEntry = {
                date: timeStamp,
                humanDate,
                word: val,
                body: processedHtml,
              };

              const existing = this.historySlots.filter(
                (item) => item.word !== val
              );
              this.historySlots = [newEntry, ...existing].slice(
                0,
                this.historyLength
              );
              this.saveHistory();
              this.$nextTick(() => this.addTooltip());
            } else {
              console.log("Подходящей словарной статьи не найдено");
              const notFoundMessage = `<div class="text-center text-h6 q-pa-md">Подходящей словарной статьи не найдено.</div>`;
              const existing = this.historySlots.filter(
                (item) => item.word !== val
              );
              this.historySlots = [
                {
                  date: timeStamp,
                  humanDate,
                  word: val,
                  body: notFoundMessage,
                },
                ...existing,
              ].slice(0, this.historyLength);
              this.saveHistory();
            }
          }
        } catch (error) {
          console.error("Ошибка поиска слова:", error);
          const timeStamp = Date.now();
          const humanDate = date.formatDate(timeStamp, "YYYY-MM-DD-HH-mm-ss");
          this.historySlots.unshift({
            date: timeStamp,
            humanDate,
            word: val,
            body: `<div class="text-red">Ошибка поиска: ${error.message}</div>`,
          });
          this.historySlots = this.historySlots.slice(0, this.historyLength);
          this.saveHistory();
        }
      } else {
        await this.$router.replace({ name: "dictionaryEmpty" });
      }
    },
    addTooltip() {
      let wordTags1 = document.getElementsByTagName("span");
      let wordTags2 = document.getElementsByTagName("em");

      const replacementMap = new Map(replacementsDictionary);

      const replacementElements = [...wordTags1, ...wordTags2].filter((el) => {
        return replacementMap.has(el.textContent.trim());
      });

      replacementElements.forEach((el) => {
        el.classList.add("tooltip");
        let tooltipSpan = document.createElement("span");
        tooltipSpan.classList.add("tooltiptext");
        tooltipSpan.textContent = replacementMap.get(el.textContent.trim());
        el.appendChild(tooltipSpan);
      });
    },
    resetForm(evt) {
      this.searchPhrase = "";
      this.temporaryWord = "";
      // this.$router.replace({name: 'dictionaryEmpty'})
      this.$refs.searchField.focus();
    },
  },

  watch: {
    searchPhrase: function (val) {
      this.temporaryWord = val;
      this.submitSelectedWord(val);
    },
    // Обрабатываем изменение маршрута для замены плюсов на пробелы
    '$route'(to) {
      if (to.params.word) {
        this.searchPhrase = to.params.word.replace(/\+/g, ' ');
      }
    }
  },
};
</script>
<style lang="sass">
.dictionary-article
  background-color: var(--rueo-card-bg)
  border: 1px solid var(--rueo-card-border)
  display: grid
  grid-template-columns: 1fr
  color: var(--rueo-text-secondary)
.dictionary-article:first-child
  background-color: var(--rueo-card-featured-bg)
.body--dark .dictionary-article:first-child
  background-color: var(--rueo-card-bg)
.dictionary-article__remove-button
    width: 2em
    justify-self: end

.tooltip
  position: relative
  display: inline-block
  border-bottom: 1px dotted black

.tooltip .tooltiptext
  visibility: hidden
  min-width: 120px
  background-color: $green-5
  color: #fff
  text-align: center
  padding: 5px
  border-radius: 6px
  top: 100%
  left: 50%
  margin-left: -60px
  opacity: 0
  transition: opacity 1s
  position: absolute
  z-index: 1
  font-style: normal
  font-size: 0.9em

.tooltip .tooltiptext::after
  content: " "
  position: absolute
  bottom: 100%
  left: 50%
  margin-left: -5px
  border-width: 5px
  border-style: solid
  border-color: transparent transparent $green-5 transparent

.tooltip:hover .tooltiptext
  visibility: visible
  opacity: 1
</style>
<style>
.search-move {
  transition: transform 0.8s ease;
}

.search-enter-from {
  opacity: 0;
  transform: translateY(30px);
}

.search-leave-to {
  opacity: 0;
  transform: translateX(-30%);
}

.search-enter-active {
  transition: opacity 0.5s, transform 0.5s;
}

.search-leave-active {
  position: absolute;
}
</style>
