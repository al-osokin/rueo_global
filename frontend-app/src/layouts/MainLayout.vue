<template>
  <q-layout view="hHh lpR fff">
    <q-header
      bordered
      class="q-py-none theme-surface header-shell"
      height-hint="98"
      reveal
    >
      <q-toolbar
        class="q-mx-auto container-style flex justify-between items-center"
      >
        <router-link to="/">
          <img
            :width="262"
            alt="Словари Кондратьева"
            class="q-my-sm"
            src="~assets/rueo_logo_with_text.svg"
          />
        </router-link>
        <div class="row items-center no-wrap q-gutter-xs toolbar-controls">
          <div class="my-info gt-sm">
            большие словари Бориса Кондратьева<br />эсперанто-русский,
            русско-эсперантский
          </div>
          <q-btn
            v-if="$q.screen.lt.md"
            color="green"
            dense
            flat
            icon="menu"
            round
            @click="rightDrawerOpen = !rightDrawerOpen"
          />
        </div>
      </q-toolbar>
      <div
        :style="{ height: $q.screen.gt.sm ? '' : '30px' }"
        class="header-tabs-background"
      >
        <div class="q-mx-auto container-style header-menu-row">
          <q-tabs
            v-if="$q.screen.gt.sm"
            :dense="!$q.screen.gt.sm"
            align="center"
            class="text-white header-tabs"
            style="height: 60px"
          >
            <q-route-tab
              :to="{ name: 'aboutMain' }"
              content-class="my-tab-buttons"
              label="От автора"
            />
            <q-route-tab
              :to="{ name: 'grammarMain' }"
              content-class="my-tab-buttons"
              label="Грамматика"
            />
            <q-route-tab
              :to="{ name: 'dictionaryEmpty' }"
              content-class="my-tab-buttons"
              label="Веб-словарь"
            />
            <q-route-tab
              :to="{ name: 'team' }"
              content-class="my-tab-buttons"
              label="Команда"
            />
          </q-tabs>
          <q-space />
          <q-btn
            :aria-label="`Переключить тему. Сейчас ${isDark ? 'тёмная' : 'светлая'}`"
            class="theme-toggle-btn header-theme-btn"
            dense
            flat
            round
            :icon="themeIcon"
            :color="isDark ? 'amber-5' : 'blue-grey-7'"
            @click="toggleTheme"
          >
            <q-tooltip>{{ themeTooltip }}</q-tooltip>
          </q-btn>
        </div>
      </div>
    </q-header>
    <q-drawer v-model="rightDrawerOpen" bordered overlay side="right">
      <!-- drawer content -->
      <div class="q-pa-lg">
        <div class="text-right">
          <div class="q-pl-lg" @click="rightDrawerOpen = false">
            <q-icon
              class="cursor-pointer"
              color="green"
              name="close"
              size="md"
            />
          </div>
        </div>
        <q-list class="">
          <q-item class="q-pl-none theme-toggle-item" v-ripple="false">
            <q-item-section avatar>
              <q-icon :name="themeIcon" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ isDark ? "Тёмная тема" : "Светлая тема" }}</q-item-label>
              <q-item-label caption>Переключить оформление</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle
                color="green"
                dense
                :model-value="isDark"
                @update:model-value="onThemeToggle"
              />
            </q-item-section>
          </q-item>
          <q-separator class="q-my-sm" />
          <q-item :to="{ name: 'aboutMain' }" active-class="" class="q-pl-none">
            <q-item-section>
              <q-item-label class="q-pl-none">От автора</q-item-label>
            </q-item-section>
          </q-item>
          <q-item
            :to="{ name: 'grammarMain' }"
            active-class=""
            class="q-pl-none"
          >
            <q-item-section>
              <q-item-label class="q-pl-none">Грамматика</q-item-label>
            </q-item-section>
          </q-item>
          <q-item
            :to="{ name: 'dictionaryEmpty' }"
            active-class=""
            class="q-pl-none"
          >
            <q-item-section>
              <q-item-label class="q-pl-none">Веб-словарь</q-item-label>
            </q-item-section>
          </q-item>
          <q-item :to="{ name: 'team' }" active-class="" class="q-pl-none">
            <q-item-section>
              <q-item-label class="q-pl-none">Команда</q-item-label>
            </q-item-section>
          </q-item>
          <q-item :to="{ name: 'donate' }" active-class="" class="q-pl-none">
            <q-item-section>
              <q-item-label class="q-pl-none">Поддержать проект</q-item-label>
            </q-item-section>
          </q-item>
          <q-item :to="{ name: 'search' }" active-class="" class="q-pl-none">
            <q-item-section>
              <q-item-label class="q-pl-none">Поиск на сайте</q-item-label>
            </q-item-section>
          </q-item>
          <q-item :to="{ name: 'social' }" active-class="" class="q-pl-none">
            <q-item-section>
              <q-item-label class="q-pl-none">Социальные сети</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </div>
    </q-drawer>
    <q-page-container>
      <router-view class="q-mx-auto container-style" />
      <q-page-scroller
        :offset="[18, 28]"
        :scroll-offset="150"
        position="bottom-right"
      >
        <q-btn color="green" fab icon="keyboard_arrow_up" />
      </q-page-scroller>
      <q-dialog v-model="dialogVisible" class="">
        <q-card>
          <q-toolbar>
            <q-toolbar-title
              ><span class="text-weight-bold"
                >Отправить сообщение об ошибке</span
              ></q-toolbar-title
            >
            <q-btn v-close-popup dense flat icon="close" round />
          </q-toolbar>
          <q-form class=" " @reset="orph_reset" @submit="orph_send">
            <q-card-section>
              <q-input v-model="formLink" label="Страница:" type="text" />
            </q-card-section>
            <q-card-section>
              <q-input
                v-model="formText"
                label="Ошибка в тексте:"
                type="text"
              />
            </q-card-section>
            <q-card-section>
              <q-input
                v-model="formComment"
                label="Комментарий (не обязательно):"
                type="text"
              />
            </q-card-section>
            <q-card-section>
              <div class="text-green-4">Вы останетесь на этой же странице</div>
            </q-card-section>
            <q-card-actions align="right">
              <q-btn color="red-6" flat label="Закрыть" type="reset" />
              <q-btn
                class="q-ml-sm"
                color="green-6"
                label="Отправить"
                type="submit"
              />
            </q-card-actions>
          </q-form>
        </q-card>
      </q-dialog>
    </q-page-container>
    <q-footer bordered class="q-py-none theme-surface footer-shell">
      <div
        :style="{ height: $q.screen.gt.sm ? '' : '30px' }"
        class="footer-tabs-background"
      >
        <q-tabs
          v-if="$q.screen.gt.sm"
          :dense="!$q.screen.gt.sm"
          align="center"
          class="text-white q-mx-auto container-style"
          switch-indicator
        >
          <q-route-tab
            :to="{ name: 'donate' }"
            content-class="my-tab-buttons"
            label="Поддержать проект"
          />
          <q-route-tab
            :to="{ name: 'search' }"
            content-class="my-tab-buttons"
            label="Поиск на сайте"
          />
          <q-route-tab
            :to="{ name: 'social' }"
            content-class="my-tab-buttons"
            label="Социальные сети"
          />
        </q-tabs>
      </div>
      <q-toolbar
        class="q-mx-auto container-style flex justify-between items-center"
      >
        <div class="footer-text-left">
          <div class="row items-center justify-between">
            <div class="row items-center">
              <router-link class="gt-xs" to="/">
                <img
                  alt="Словари Кондратьева"
                  class="q-my-sm q-mr-sm"
                  height="50"
                  src="~assets/rueo_logo_grey.svg"
                  width="61"
                />
              </router-link>
              <div class="text-grey-8">
                <p class="no-margin">
                  © 2009-2025, Большие словари
                  <strong>Бориса Кондратьева</strong>
                </p>
              </div>
            </div>
            <a
              href="https://roboto.pro"
              target="_blank"
              class="text-grey-8 text-no-wrap"
              style="text-decoration: none"
              :class="$q.screen.width > 710 ? 'q-mx-auto' : ''"
              >Создано Роботами{{ version ? '. v' + version : '' }}</a
            >
          </div>
        </div>
        <q-btn flat @click="orph" class="q-pa-none">
          <img :src="require(`../assets/orph.png`)" height="35" width="120" />
        </q-btn>
      </q-toolbar>
    </q-footer>
  </q-layout>
</template>
<script>
import { defineComponent } from "vue";
import {
  ThemeMode,
  applyTheme,
  clearThemePreference,
  detectPreferredTheme,
  getStoredTheme,
  listenToSystemThemeChange,
  persistThemePreference,
} from "src/utils/theme";

export default defineComponent({
  name: "MainLayout",

  components: {},
  setup() {
    return {};
  },
  data() {
    return {
      rightDrawerOpen: false,
      dialogVisible: false,
      formLink: "",
      formText: "",
      formComment: "",
      formKey: "2З5",
      version:
        typeof __PACKAGE_VERSION__ !== "undefined"
          ? __PACKAGE_VERSION__
          : null,
      currentTheme: ThemeMode.LIGHT,
      hasManualTheme: false,
      removeThemeListener: null,
    };
  },
  computed: {
    isDark() {
      return this.currentTheme === ThemeMode.DARK;
    },
    themeIcon() {
      return this.isDark ? "light_mode" : "dark_mode";
    },
    themeTooltip() {
      return this.isDark
        ? "Включена тёмная тема"
        : "Включена светлая тема";
    },
  },
  methods: {
    onKeyPress(e) {
      if (e.ctrlKey && e.keyCode === 13) {
        this.orph();
      }
    },
    toggleRightDrawer: function () {
      this.rightDrawerOpen = !this.rightDrawerOpen;
    },
    syncThemeState() {
      const storedTheme = getStoredTheme();
      if (storedTheme === ThemeMode.DARK || storedTheme === ThemeMode.LIGHT) {
        this.hasManualTheme = true;
        this.setTheme(storedTheme, false);
      } else {
        if (storedTheme) {
          clearThemePreference();
        }
        this.hasManualTheme = false;
        const initial = this.$q.dark.isActive
          ? ThemeMode.DARK
          : detectPreferredTheme();
        this.setTheme(initial, false);
      }
    },
    setTheme(mode, persistPreference = false) {
      this.currentTheme = mode;
      applyTheme(mode);
      if (persistPreference) {
        persistThemePreference(mode);
        this.hasManualTheme = true;
      }
    },
    toggleTheme() {
      const nextTheme = this.isDark ? ThemeMode.LIGHT : ThemeMode.DARK;
      this.setTheme(nextTheme, true);
    },
    onThemeToggle(value) {
      this.setTheme(value ? ThemeMode.DARK : ThemeMode.LIGHT, true);
    },

    orph() {
      const hostname = "https://rueo.ru";
      // console.log(hostname + this.$route.path);
      // this.formLink = location.href;
      this.formLink = hostname + this.$route.path;
      let sel = "";
      if (window.getSelection) {
        sel = window.getSelection().toString();
      } else if (document.selection) {
        sel = document.selection.createRange().text;
      }
      this.formText = sel;
      this.dialogVisible = true;
    },
    async orph_send() {
      const params = new URLSearchParams();
      params.append("url", this.formLink);
      params.append("text", this.formText);
      params.append("comment", this.formComment);
      params.append("key", this.formKey);

      try {
        await this.$axios.post("/orph", params, {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          timeout: 60000,
        });
        this.$q.notify({
          type: "positive",
          message: "Сообщение отправлено",
        });
        this.orph_reset();
      } catch (error) {
        console.error("Не удалось отправить сообщение об ошибке", error);
        this.$q.notify({
          type: "negative",
          message: "Не удалось отправить сообщение",
        });
      }
    },
    orph_reset() {
      this.formLink = "";
      this.formText = "";
      this.formComment = "";
      this.dialogVisible = false;
    },
  },
  watch: {},
  mounted() {
    this.syncThemeState();
    this.removeThemeListener = listenToSystemThemeChange((mode) => {
      if (!this.hasManualTheme) {
        this.setTheme(mode, false);
      }
    });
  },

  beforeUnmount() {
    window.removeEventListener("keyup", this.onKeyPress);
    if (this.removeThemeListener) {
      this.removeThemeListener();
      this.removeThemeListener = null;
    }
  },
  created() {
    window.addEventListener("keyup", this.onKeyPress);

    //yandex.metrika
    (function (d, w, c) {
      (w[c] = w[c] || []).push(function () {
        try {
          w.yaCounter33490238 = new Ya.Metrika({
            id: 33490238,
            clickmap: true,
            trackLinks: true,
            accurateTrackBounce: true,
          });
        } catch (e) {}
      });

      let n = d.getElementsByTagName("script")[0],
        s = d.createElement("script"),
        f = function () {
          n.parentNode.insertBefore(s, n);
        };
      s.type = "text/javascript";
      s.async = true;
      s.src = "https://mc.yandex.ru/metrika/watch.js";

      if (w.opera == "[object Opera]") {
        d.addEventListener("DOMContentLoaded", f, false);
      } else {
        f();
      }
    })(document, window, "yandex_metrika_callbacks");

    //reformal

    //Костыль: настройки скрипта положил в файл index.template.html
    function reformal() {
      const script = document.createElement("script");
      script.type = "text/javascript";
      script.async = true;
      script.src =
        ("https:" == document.location.protocol ? "https://" : "http://") +
        "media.reformal.ru/widgets/v3/reformal.js";
      document.head.appendChild(script);
    }

    reformal();
  },
});
</script>
<style lang="sass" scoped>
.header-tabs-background
  background-image: url(~assets/menu1.png)
  background-position-y: 100%
.body--dark .header-tabs-background
  background-image: linear-gradient(120deg, #0d2f45, #081521)

.footer-tabs-background
  background-image: url(~assets/menu2.png)
  background-position-y: 0%
.body--dark .footer-tabs-background
  background-image: linear-gradient(120deg, #07121d, #03080c)

.footer-text-left
  padding-left: 0
  display: grid
  grid-row-gap: 0.5rem
  width: 100%

.container-style
  max-width: 940px

.header-menu-row
  display: flex
  align-items: center
  gap: 12px
.header-tabs
  flex: 1
.header-theme-btn
  margin-left: auto

.my-info
  text-align: right
  color: var(--rueo-text-secondary)
  font-style: italic

.header-shell,
.footer-shell,
.toolbar-controls
  transition: background-color 0.25s ease, color 0.25s ease

.theme-toggle-btn
  min-width: 40px

.theme-toggle-item
  border-radius: 12px
  background-color: var(--rueo-surface-alt)
</style>
<style lang="sass">
@media (max-width: $breakpoint-xs-max)
  #reformal_tab
    display: none !important
</style>
