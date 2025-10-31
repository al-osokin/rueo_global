<template>
  <q-page class="q-pa-md q-gutter-lg admin-review">
    <div class="row q-col-gutter-lg">
      <div class="col-12 col-md-4">
        <q-card flat bordered class="q-mb-lg">
          <q-card-section class="column q-gutter-xs">
            <div class="text-h6">Статистика</div>
            <div class="text-body1">
              На проверку:
              <span class="text-weight-medium">
                {{ formatNumber(stats.needs_review) }}
                <span class="text-grey-7" v-if="stats.total"> ({{ formatPercent(stats.needs_review, stats.total) }})</span>
              </span>
            </div>
            <div class="text-body1">
              Проверено:
              <span class="text-weight-medium">{{ formatNumber(stats.reviewed) }}</span>
            </div>
            <div class="text-body1 text-grey-7">
              Всего статей:
              <span class="text-weight-medium">{{ formatNumber(stats.total) }}</span>
            </div>
          </q-card-section>
        </q-card>
        <q-card flat bordered>
          <q-card-section class="column q-gutter-md">
            <div class="text-h6">Поиск статьи</div>
            <q-select
              v-model="lang"
              :options="langOptions"
              label="Язык"
              dense
              outlined
            />
            <q-select
              v-model="selectedArtId"
              :options="suggestions"
              :loading="loadingSuggestions"
              use-input
              hide-selected
              fill-input
              emit-value
              map-options
              dense
              outlined
              label="Начните вводить заголовок"
              @filter="onFilter"
              @update:model-value="loadArticle"
            >
              <template #no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    Нет совпадений
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-toggle
              v-model="showPendingOnly"
              label="Только требующие проверки"
              dense
            />
            <q-input
              v-model.number="directArtId"
              label="Перейти по art_id"
              type="number"
              dense
              outlined
              clearable
              @keyup.enter="() => directArtId && loadArticle(directArtId)"
            >
              <template #append>
                <q-btn
                  flat
                  round
                  icon="arrow_forward"
                  :disable="!directArtId"
                  @click="() => loadArticle(directArtId)"
                />
              </template>
            </q-input>
            <div class="row q-gutter-sm">
              <q-btn
                color="secondary"
                outline
                label="Случайная проверка"
                icon="shuffle"
                :disable="saving"
                @click="loadSpotCheck"
              />
            </div>
          </q-card-section>
        </q-card>
        <q-card flat bordered class="q-mt-lg">
          <q-card-section class="column q-gutter-sm">
            <div class="text-subtitle1">Сервис</div>
            <q-btn
              color="primary"
              outline
              label="Переразобрать проблемные"
              :loading="reparseLoading"
              :disable="reparseLoading"
              @click="reparseArticles"
            />
            <q-toggle
              v-model="includePending"
              label="Включать непроверенные"
              dense
            />
          </q-card-section>
        </q-card>
        <q-card flat bordered class="q-mt-lg" v-if="article && article.review_notes.length">
          <q-card-section>
            <div class="text-subtitle1">Заметки парсера</div>
            <q-list dense>
              <q-item v-for="(note, idx) in article.review_notes" :key="idx">
                <q-item-section>{{ note }}</q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
        <q-card flat bordered class="q-mt-lg" v-if="article && article.notes.length">
          <q-card-section>
            <div class="text-subtitle1">Комментарии</div>
            <q-list dense>
              <q-item v-for="note in article.notes" :key="note.id">
                <q-item-section>
                  <div class="text-body2">{{ note.body }}</div>
                  <div class="text-caption text-grey-6">
                    <span v-if="note.author">{{ note.author }} · </span>{{ formatDate(note.created_at) }}
                  </div>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-8">
        <q-card flat bordered v-if="article">
          <q-card-section class="q-gutter-sm">
            <div class="text-h6">{{ article.headword }}</div>
            <div class="text-caption text-grey-7">
              Шаблон: {{ article.template || '—' }} · Статус: {{ article.parsing_status }}
            </div>
            <div class="row q-gutter-sm q-mt-sm">
              <q-btn
                color="warning"
                outline
                size="sm"
                label="Сбросить"
                :loading="resetting"
                :disable="resetting"
                @click="resetArticle"
              />
              <q-btn
                color="primary"
                outline
                size="sm"
                label="Переразобрать открытую"
                :loading="reparseCurrentLoading"
                :disable="reparseCurrentLoading"
                @click="reparseCurrentArticle"
              />
            </div>
          </q-card-section>
          <q-separator />
          <q-card-section class="q-gutter-md">
            <div
              v-for="group in groups"
              :key="group.group_id"
              class="q-pa-sm q-border rounded-borders"
              :class="{
                'bg-amber-1': group.auto_generated,
                'bg-red-1': group.requires_review && !group.accepted,
              }"
            >
              <div class="row items-center justify-between">
                <div>
                  <span class="text-weight-medium">
                    {{ group.label || 'Перевод' }}
                  </span>
                  <q-chip
                    v-if="group.section"
                    dense
                    color="blue-grey-2"
                    text-color="blue-grey-9"
                    class="q-ml-sm"
                  >
                    {{ group.section }}
                  </q-chip>
                  <q-chip v-if="group.requires_review" dense color="red" text-color="white" class="q-ml-sm">
                    требуется проверка
                  </q-chip>
                  <q-chip v-if="group.auto_generated" dense color="orange" text-color="white" class="q-ml-sm">
                    авто
                  </q-chip>
                </div>
                <q-toggle
                  v-model="group.accepted"
                  size="sm"
                  color="green"
                  label="Принять"
                />
              </div>
              <div class="text-body2 q-ml-sm">
                <div>
                  <span class="text-grey-7">Текущий вариант:</span>
                  {{ formatItems(group.items) }}
                </div>
                <div v-if="group.base_items.length" class="text-caption text-grey-7">
                  Источник: {{ formatItems(group.base_items) }}
                </div>
                <div v-if="group.candidates.length > 1" class="q-mt-sm">
                  <div class="text-caption text-grey-7 q-mb-xs">
                    Выберите гипотезу:
                  </div>
                  <div class="column q-gutter-xs">
                    <div
                      v-for="candidate in group.candidates"
                      :key="candidate.id || candidate.title"
                      class="column"
                    >
                      <div class="row no-wrap items-start">
                        <q-radio
                          :model-value="group.selected_candidate"
                          :name="group.group_id"
                          :val="candidate.id"
                          dense
                          @update:model-value="(val) => onCandidateChange(group, val)"
                        />
                        <div class="q-ml-sm">
                          <div class="text-body2">{{ candidate.title }}</div>
                          <div class="text-caption text-grey-7" v-if="candidate.id !== 'manual' || candidate.items.length">
                            {{ formatItems(candidate.items) }}
                          </div>
                        </div>
                      </div>
                      <div v-if="candidate.id === 'manual' && group.selected_candidate === 'manual'" class="q-ml-md q-mt-xs">
                        <q-input
                          v-model="group.manual_override"
                          outlined
                          dense
                          type="textarea"
                          autogrow
                          label="Введите варианты (синонимы через | )"
                          hint="Например: выступать в роли адвоката | выступать в роли защитника"
                          :disable="saving"
                          @update:model-value="(val) => onManualOverrideChange(group, val)"
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <q-input
              v-model="comment"
              type="textarea"
              outlined
              autogrow
              label="Комментарий"
              :disable="saving"
            />
          </q-card-section>
          <q-card-actions align="between" class="q-gutter-sm">
            <q-btn
              color="red"
              outline
              icon="first_page"
              label="ПРЕД. ПРОБЛ."
              :disable="saving"
              @click="saveAndGo('prev-problematic')"
            />
            <q-btn
              color="primary"
              outline
              icon="chevron_left"
              label="НАЗАД"
              :disable="saving || !canGoPrevById"
              @click="saveAndGo('prev-id')"
            />
            <q-btn
              color="primary"
              outline
              icon-right="chevron_right"
              label="ВПЕРЁД"
              :loading="saving"
              :disable="saving"
              @click="saveAndGo('next-id')"
            />
            <q-btn
              color="red"
              outline
              icon-right="last_page"
              label="СЛЕД. ПРОБЛ."
              :disable="saving"
              @click="saveAndGo('next-problematic')"
            />
          </q-card-actions>
        </q-card>
        <q-banner v-else class="bg-grey-2 text-grey-8">
          Выберите статью для просмотра.
        </q-banner>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from "vue";
import { useQuasar } from "quasar";
import { api } from "boot/axios";

const $q = useQuasar();

const langOptions = [
  { label: "Эсперанто", value: "eo" },
  { label: "Русский", value: "ru" },
];

const lang = ref("eo");
const stats = reactive({
  total: 0,
  needs_review: 0,
  reviewed: 0,
});
const suggestions = ref([]);
const loadingSuggestions = ref(false);
const selectedArtId = ref(null);
const directArtId = ref(null);

const article = ref(null);
const groups = reactive([]);
const comment = ref("");
const saving = ref(false);
const resetting = ref(false);
const history = ref([]);
const historyIndex = ref(-1);
const showPendingOnly = ref(true);
const includePending = ref(false);
const reparseLoading = ref(false);
const reparseCurrentLoading = ref(false);

const canGoBack = computed(() => historyIndex.value > 0);
const canGoPrevById = computed(() => article.value && article.value.art_id > 1);

const formatDate = (value) => {
  if (!value) return "";
  return new Date(value).toLocaleString();
};

const formatNumber = (value) => {
  const number = Number.isFinite(value) ? value : 0;
  return new Intl.NumberFormat("ru-RU").format(number);
};

const formatPercent = (part, total) => {
  const numerator = Number(part);
  const denominator = Number(total);
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator <= 0) {
    return "0.0%";
  }
  const percent = (numerator / denominator) * 100;
  return `${percent.toFixed(1)}%`;
};

const normalizeItemsKey = (items) => {
  if (!Array.isArray(items)) {
    return "";
  }
  return items.join("|||");
};

const formatItems = (items) => {
  if (!Array.isArray(items) || !items.length) {
    return "—";
  }
  return items.join(" | ");
};

const loadStats = async () => {
  try {
    const { data } = await api.get(`/admin/articles/${lang.value}/stats`);
    stats.total = data?.total ?? 0;
    stats.needs_review = data?.needs_review ?? 0;
    stats.reviewed = data?.reviewed ?? 0;
  } catch (err) {
    console.error(err);
    stats.total = 0;
    stats.needs_review = 0;
    stats.reviewed = 0;
    $q.notify({ type: "negative", message: "Не удалось получить статистику" });
  }
};

const applyCandidateSelection = (group, candidateId = null) => {
  const candidates = Array.isArray(group.candidates) ? group.candidates : [];
  if (!candidates.length) {
    group.selected_candidate = null;
    group.items = Array.isArray(group.items) ? [...group.items] : [];
  } else {
    let chosen = candidates.find((candidate) => candidate.id === candidateId);
    if (!chosen) {
      [chosen] = candidates;
    }
    group.selected_candidate = chosen?.id ?? null;
    group.items = Array.isArray(chosen?.items) ? [...chosen.items] : [];
  }
  const baseKey = normalizeItemsKey(group.base_items);
  const itemsKey = normalizeItemsKey(group.items);
  if (baseKey) {
    group.auto_generated = baseKey !== itemsKey;
  }
};

const onCandidateChange = (group, candidateId) => {
  if (!group) return;
  if (candidateId === group.selected_candidate) {
    return;
  }
  applyCandidateSelection(group, candidateId);
};

const onManualOverrideChange = (group, text) => {
  if (!group) return;
  const manualCandidate = group.candidates.find((c) => c.id === "manual");
  if (manualCandidate) {
    const newItems = text
      ? text.split("|").map((phrase) => phrase.trim()).filter(Boolean)
      : [];
    manualCandidate.items = newItems;
    if (group.selected_candidate === "manual") {
      group.items = [...newItems];
    }
  }
};

const clearArticle = () => {
  article.value = null;
  groups.splice(0, groups.length);
  comment.value = "";
};

watch(lang, () => {
  suggestions.value = [];
  selectedArtId.value = null;
  directArtId.value = null;
  clearArticle();
  history.value = [];
  historyIndex.value = -1;
  loadStats();
});

watch(showPendingOnly, () => {
  suggestions.value = [];
});

const onFilter = (val, update, abort) => {
  if (!val || val.length < 2) {
    update(() => {
      suggestions.value = [];
    });
    return;
  }

  loadingSuggestions.value = true;
  const params = { query: val };
  if (showPendingOnly.value) {
    params.status = "needs_review";
  }
  api
    .get(`/admin/articles/${lang.value}`, {
      params,
    })
    .then(({ data }) => {
      update(() => {
        suggestions.value = data.map((item) => ({
          label: item.headword || `#${item.art_id}`,
          value: item.art_id,
          parsing_status: item.parsing_status,
        }));
      });
    })
    .catch((err) => {
      console.error(err);
      update(() => {
        suggestions.value = [];
      });
      $q.notify({ type: "negative", message: "Не удалось получить подсказки" });
    })
    .finally(() => {
      loadingSuggestions.value = false;
    });
};

const prepareGroups = (payload) => {
  groups.splice(0, groups.length);
  const resolvedGroups = payload.resolved_translations?.groups || {};
  (payload.groups || []).forEach((group) => {
    const candidateList = Array.isArray(group.candidates)
      ? group.candidates.map((candidate) => ({
          id: candidate.id,
          title: candidate.title,
          items: Array.isArray(candidate.items) ? [...candidate.items] : [],
        }))
      : [];
    const baseItems = Array.isArray(group.base_items) ? [...group.base_items] : [];
    const storedGroup = resolvedGroups[group.group_id] || {};
    const localGroup = {
      group_id: group.group_id,
      label: group.label,
      items: Array.isArray(group.items) ? [...group.items] : [],
      base_items: baseItems,
      requires_review: group.requires_review,
      auto_generated: group.auto_generated,
      section: group.section || null,
      accepted: group.accepted,
      candidates: candidateList,
      selected_candidate: group.selected_candidate || (candidateList[0]?.id ?? null),
      manual_override: storedGroup.manual_override || "",
    };
    applyCandidateSelection(localGroup, localGroup.selected_candidate);
    groups.push(localGroup);
  });
};

const updateHistory = (artId, options = {}) => {
  const { fromHistory = false, historyPosition } = options;
  if (fromHistory) {
    if (typeof historyPosition === "number") {
      historyIndex.value = historyPosition;
    }
    return;
  }

  if (historyIndex.value >= 0 && history.value[historyIndex.value] === artId) {
    return;
  }

  const cutoff = historyIndex.value + 1;
  history.value = history.value.slice(0, cutoff);
  history.value.push(artId);
  historyIndex.value = history.value.length - 1;
};

const loadArticle = async (artId, options = {}) => {
  if (!artId) return;
  try {
    const { data } = await api.get(`/admin/articles/${lang.value}/${artId}`);
    article.value = data;
    comment.value = "";
    prepareGroups(data);
    selectedArtId.value = null; // Очищаем поле заголовка
    updateHistory(artId, options);
  } catch (err) {
    console.error(err);
    $q.notify({ type: "negative", message: "Не удалось загрузить статью" });
  }
};

const buildResolvedPayload = () => {
  const resolved = article.value?.resolved_translations || {};
  const result = {
    ...(resolved || {}),
    auto_candidates: article.value?.auto_candidates || [],
    groups: {},
  };
  groups.forEach((group) => {
    const entry = {
      accepted: !!group.accepted,
    };
    if (group.selected_candidate) {
      entry.selected_candidate = group.selected_candidate;
    }
    if (group.selected_candidate === "manual" && group.manual_override && group.manual_override.trim()) {
      entry.manual_override = group.manual_override.trim();
    } else if (group.selected_candidate !== "manual") {
      entry.manual_override = "";
    }
    result.groups[group.group_id] = entry;
  });
  return result;
};

const loadNextPending = async (afterId = null) => {
  try {
    const params = { mode: "next" };
    if (afterId != null) {
      params.after = afterId;
    }
    const { data } = await api.get(`/admin/articles/${lang.value}/queue`, {
      params,
    });
    if (data?.art_id) {
      await loadArticle(data.art_id);
    } else {
      $q.notify({ type: "info", message: "Все статьи просмотрены" });
    }
  } catch (err) {
    console.error(err);
    $q.notify({ type: "negative", message: "Не удалось получить следующую статью" });
  }
};

const loadPrevProblematic = async (beforeId = null) => {
  try {
    const params = { mode: "prev" };
    if (beforeId != null) {
      params.before = beforeId;
    }
    const { data } = await api.get(`/admin/articles/${lang.value}/queue`, {
      params,
    });
    if (data?.art_id) {
      await loadArticle(data.art_id);
    } else {
      $q.notify({ type: "info", message: "Нет предыдущих проблемных статей" });
    }
  } catch (err) {
    console.error(err);
    $q.notify({ type: "negative", message: "Не удалось получить предыдущую статью" });
  }
};

const loadNextById = async () => {
  if (!article.value) return;
  const nextId = article.value.art_id + 1;
  await loadArticle(nextId);
};

const loadPrevById = async () => {
  if (!article.value || article.value.art_id <= 1) return;
  const prevId = article.value.art_id - 1;
  await loadArticle(prevId);
};

const resetArticle = async () => {
  if (!article.value || resetting.value) {
    return;
  }
  const confirmed = window.confirm("Сбросить подтверждённые варианты для этой статьи?");
  if (!confirmed) {
    return;
  }
  resetting.value = true;
  try {
    const { data } = await api.post(`/admin/articles/${lang.value}/${article.value.art_id}/reset`);
    article.value = data;
    prepareGroups(data);
    comment.value = "";
    updateHistory(data.art_id, { fromHistory: true });
    $q.notify({ type: "positive", message: "Статья сброшена" });
  } catch (err) {
    console.error(err);
    $q.notify({ type: "negative", message: "Не удалось сбросить статью" });
  } finally {
    resetting.value = false;
    await loadStats();
  }
};

const reparseArticles = async () => {
  if (reparseLoading.value) {
    return;
  }
  reparseLoading.value = true;
  try {
    const payload = {};
    if (includePending.value) {
      payload.include_pending = true;
    }
    const { data } = await api.post(`/admin/articles/${lang.value}/reparse`, payload);
    const updated = data?.updated ?? 0;
    const failed = data?.failed_details ?? [];
    if (updated) {
      $q.notify({ type: "positive", message: `Переразобрано ${updated} стат.` });
    }
    if (failed.length) {
      $q.notify({
        type: "warning",
        message: `Не удалось обработать ${failed.length} стат.`,
      });
    }
    if (article.value) {
      await loadArticle(article.value.art_id, { fromHistory: true });
    }
    await loadStats();
  } catch (err) {
    console.error(err);
    $q.notify({ type: "negative", message: "Не удалось запустить переразбор" });
  } finally {
    reparseLoading.value = false;
  }
};

const reparseCurrentArticle = async () => {
  if (!article.value || reparseCurrentLoading.value) {
    return;
  }
  reparseCurrentLoading.value = true;
  try {
    const { data } = await api.post(
      `/admin/articles/${lang.value}/${article.value.art_id}/reparse`
    );
    if (data?.article) {
      article.value = data.article;
      prepareGroups(data.article);
      comment.value = "";
      updateHistory(data.article.art_id, { fromHistory: true });
      if (data.parse_error) {
        $q.notify({
          type: "warning",
          message: `Переразбор завершился с ошибкой: ${data.parse_error}`,
        });
      } else {
        $q.notify({ type: "positive", message: "Статья переразобрана" });
      }
    } else {
      $q.notify({ type: "negative", message: "Не удалось получить данные статьи" });
    }
  } catch (err) {
    console.error(err);
    const detail = err?.response?.data?.detail;
    $q.notify({ type: "negative", message: detail || "Не удалось переразобрать статью" });
  } finally {
    reparseCurrentLoading.value = false;
    await loadStats();
  }
};

const loadSpotCheck = async () => {
  try {
    const { data } = await api.get(`/admin/articles/${lang.value}/queue`, {
      params: { mode: "spotcheck" },
    });
    if (data?.art_id) {
      await loadArticle(data.art_id);
    } else {
      $q.notify({ type: "info", message: "Нет статей для проверки" });
    }
  } catch (err) {
    console.error(err);
    $q.notify({ type: "negative", message: "Не удалось получить статью" });
  }
};

const saveAndGo = async (direction = "next-problematic") => {
  if (!article.value) {
    return;
  }

  saving.value = true;
  try {
    const payload = {
      resolved_translations: buildResolvedPayload(),
    };
    if (comment.value && comment.value.trim().length) {
      payload.comment = comment.value.trim();
    }
    await api.post(`/admin/articles/${lang.value}/${article.value.art_id}`, payload);
    $q.notify({ type: "positive", message: "Сохранено" });
    comment.value = "";
    await loadStats();

    const currentId = article.value?.art_id;
    
    switch (direction) {
      case "prev-problematic":
        await loadPrevProblematic(currentId);
        break;
      case "prev-id":
        await loadPrevById();
        break;
      case "next-id":
        await loadNextById();
        break;
      case "next-problematic":
      case "next":
        await loadNextPending(currentId);
        break;
      default:
        break;
    }
  } catch (err) {
    console.error(err);
    $q.notify({ type: "negative", message: "Не удалось сохранить" });
  } finally {
    saving.value = false;
  }
};

onMounted(() => {
  loadStats();
  loadNextPending();
});

</script>

<style scoped>
.admin-review .q-border {
  border: 1px solid var(--q-color-grey-4);
}
</style>
