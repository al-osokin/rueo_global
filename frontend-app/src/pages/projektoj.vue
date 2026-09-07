<template>
  <q-page class="wrap projects-page" padding>
    <header class="projects-intro">
      <h1>Дружественные проекты</h1>
    </header>

    <div class="projects-grid">
      <article
        v-for="project in projects"
        :key="project.url"
        :class="`project-card project-card--${project.accent}`"
      >
        <div class="project-card__topline" aria-hidden="true"></div>
        <p class="project-card__domain">{{ project.domain }}</p>
        <h2>{{ project.name }}</h2>

        <div class="project-card__descriptions">
          <p lang="ru">{{ project.descriptionRu }}</p>
          <p class="project-card__esperanto" lang="eo">
            {{ project.descriptionEo }}
          </p>
        </div>

        <a
          :aria-label="`Открыть ${project.name} в новой вкладке`"
          :href="project.url"
          class="project-card__link"
          rel="noopener noreferrer"
          target="_blank"
        >
          <span>Перейти на сайт</span>
          <q-icon aria-hidden="true" name="open_in_new" size="18px" />
        </a>
      </article>
    </div>
  </q-page>
</template>

<script>
import { createMetaMixin } from "quasar";

const projects = [
  {
    name: "Biologio",
    domain: "biologio.rueo.ru",
    url: "https://biologio.rueo.ru/",
    accent: "green",
    descriptionRu:
      "Шестиязычный картинный словарь животных (русский, латинский, эсперанто, английский, немецкий, испанский)",
    descriptionEo:
      "Seslingva biologia bildvortaro (rusa, latina, Esperanto, angla, germana, hispana)",
  },
  {
    name: "Frazaro",
    domain: "frazaro.ru",
    url: "https://frazaro.ru/",
    accent: "blue",
    descriptionRu:
      "Практический иллюстрированный словарь эсперанто с примерами предложений и переводов",
    descriptionEo:
      "Praktika Esperanto-vortaro ilustrita per propozicioj kaj iliaj tradukoj",
  },
];

export default {
  name: "ProjectsPage",
  data() {
    return { projects };
  },
  mixins: [
    createMetaMixin(function () {
      return {
        title: "Эсперанто словари Бориса Кондратьева | Дружественные проекты",
        meta: {
          description: {
            name: "description",
            content:
              "Дружественные эсперанто-проекты: шестиязычный картинный словарь животных Biologio и практический словарь Frazaro.",
          },
          keywords: {
            name: "keywords",
            content:
              "эсперанто, словарь эсперанто, Biologio, Frazaro, дружественные проекты",
          },
        },
      };
    }),
  ],
};
</script>

<style lang="scss" scoped>
.projects-page {
  padding-top: clamp(28px, 5vw, 56px);
  padding-bottom: 64px;
}

.projects-intro {
  max-width: 660px;
  margin-bottom: clamp(28px, 5vw, 48px);
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.project-card {
  position: relative;
  display: flex;
  min-height: 360px;
  flex-direction: column;
  overflow: hidden;
  padding: clamp(24px, 4vw, 34px);
  border: 1px solid var(--rueo-card-border);
  border-radius: 18px;
  background: var(--rueo-card-featured-bg);
  box-shadow: 0 14px 36px rgba(24, 48, 61, 0.08);
}

.project-card__topline {
  position: absolute;
  top: 0;
  right: 0;
  left: 0;
  height: 5px;
}

.project-card--green .project-card__topline {
  background: linear-gradient(90deg, #31b44b, #8bc34a);
}

.project-card--blue .project-card__topline {
  background: linear-gradient(90deg, #168aad, #52b6d7);
}

.project-card__domain {
  margin: 2px 0 14px;
  color: var(--rueo-text-secondary);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.project-card h2 {
  margin: 0 0 24px;
  font-size: clamp(27px, 3vw, 34px);
  line-height: 1.1;
}

.project-card__descriptions {
  display: grid;
  gap: 16px;
  margin-bottom: 28px;
  font-size: 16px;
  line-height: 1.55;
}

.project-card__descriptions p {
  margin: 0;
}

.project-card__esperanto {
  padding-top: 16px;
  border-top: 1px solid var(--rueo-border-color);
  color: var(--rueo-text-secondary);
  font-style: italic;
}

.project-card__link {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 8px;
  margin-top: auto;
  font-size: 16px;
  font-weight: 700;
}

.body--dark .project-card {
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.26);
}

@media (max-width: 700px) {
  .projects-grid {
    grid-template-columns: 1fr;
  }

  .project-card {
    min-height: 0;
  }
}
</style>
