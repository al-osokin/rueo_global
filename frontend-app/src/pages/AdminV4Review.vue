<template>
  <q-page class="q-pa-md admin-v4-review">
    <div class="row q-col-gutter-lg">
      <div class="col-12 col-md-4">
        <q-card flat bordered>
          <q-card-section class="column q-gutter-md">
            <div class="text-h6">V4 Review (MVP)</div>
            <q-select
              v-model="lang"
              :options="langOptions"
              emit-value
              map-options
              dense
              outlined
              label="Язык"
            />
            <q-input
              v-model.number="artId"
              type="number"
              dense
              outlined
              label="art_id"
              :min="1"
              @keyup.enter="loadAst"
            />
            <q-btn
              color="primary"
              label="Загрузить AST"
              :loading="loadingAst"
              :disable="!artId || loadingAst"
              @click="loadAst"
            />
            <q-btn
              color="secondary"
              outline
              label="Переразобрать статью"
              :loading="reparsingArticle"
              :disable="!artId || reparsingArticle || loadingAst"
              @click="reparseArticle"
            />
            <q-btn
              color="negative"
              outline
              label="Сбросить подтверждения статьи"
              :loading="resettingArticle"
              :disable="!artId || resettingArticle || loadingAst"
              @click="resetArticleResolutions"
            />
          </q-card-section>
        </q-card>

        <q-card
          ref="selectedCardRef"
          flat
          bordered
          class="q-mt-lg selected-block-card"
          v-if="selectedBlock"
          :style="selectedCardStyle"
        >
          <q-card-section class="column q-gutter-sm">
            <div class="text-subtitle1">Выбранный блок</div>
            <div class="text-caption text-grey-8">form_id: {{ selectedBlock.formId }}</div>
            <div class="text-caption text-grey-8">block_id: {{ selectedBlock.blockId }}</div>
            <div class="text-body2 q-mt-xs raw-preview">{{ selectedBlock.raw || '—' }}</div>
            <q-chip
              v-if="selectedBlock?.reviewFlag && !selectedBlock?.applied"
              size="sm"
              :color="flagColor(selectedBlock.reviewFlag)"
              text-color="white"
            >{{ selectedBlock.reviewFlag }}</q-chip>
            <q-chip
              v-if="selectedBlock?.applied"
              size="sm"
              color="positive"
              text-color="white"
              icon="check"
            >applied</q-chip>
            <q-chip
              v-if="selectedBlock?.dirty"
              size="sm"
              color="warning"
              text-color="black"
              icon="edit"
            >dirty</q-chip>

            <q-btn
              color="secondary"
              outline
              label="Gemma Assist"
              :loading="resolving"
              :disable="resolving || !astPayload"
              @click="runResolve"
            />

            <div v-if="resolveResult" class="q-mt-sm">
              <div class="text-caption text-grey-7">
                {{ resolveResult.provider }} · confidence {{ Number(resolveResult.confidence || 0).toFixed(2) }}
              </div>
              <div class="text-caption text-grey-7 q-mb-xs">Кандидат для apply (из Gemma)</div>
              <q-select
                v-model="selectedCandidate"
                :options="candidateOptions"
                class="fit-input"
                dense
                outlined
                emit-value
                map-options
              />
              <div class="text-caption text-grey-7 q-mt-xs">
                Если нужен свой вариант — используй режим <strong>Edit</strong> и поле «Значение для Edit».
              </div>
              <div class="text-caption q-mt-xs">{{ resolveResult.rationale_short }}</div>
            </div>

            <div class="row q-gutter-sm q-mt-sm">
              <q-btn
                :color="actionMode === 'accept' ? 'positive' : 'grey-7'"
                :outline="actionMode !== 'accept'"
                label="Accept"
                size="sm"
                @click="setActionMode('accept')"
              />
              <q-btn
                :color="actionMode === 'reject' ? 'negative' : 'grey-7'"
                :outline="actionMode !== 'reject'"
                label="Reject"
                size="sm"
                @click="setActionMode('reject')"
              />
              <q-btn
                :color="actionMode === 'edit' ? 'warning' : 'grey-7'"
                :outline="actionMode !== 'edit'"
                label="Edit"
                size="sm"
                @click="setActionMode('edit')"
              />
            </div>

            <q-input
              v-if="actionMode === 'edit'"
              v-model="editValue"
              type="textarea"
              autogrow
              dense
              outlined
              label="Значение для Edit"
              class="q-mt-sm fit-input"
            />

            <q-btn
              color="positive"
              outline
              label="Apply resolution"
              :loading="applying"
              :disable="applying || !astPayload || !canApply"
              @click="applyResolution"
            />
            <q-btn
              color="negative"
              outline
              label="Сбросить этот блок"
              :loading="resettingBlock"
              :disable="resettingBlock || !astPayload || !selectedBlock"
              @click="resetSelectedBlock"
            />
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-8">
        <q-banner v-if="astPayload?.parse_error" class="bg-red-1 text-red-10 q-mb-md">
          <div class="text-weight-medium">parse_error</div>
          <div>{{ astPayload.parse_error }}</div>
        </q-banner>

        <q-banner v-if="astPayload?.review_diagnostic" class="bg-orange-1 text-orange-10 q-mb-md">
          <div class="text-weight-medium">review_diagnostic</div>
          <div><strong>code:</strong> {{ astPayload.review_diagnostic.code || '—' }}</div>
          <div><strong>message:</strong> {{ astPayload.review_diagnostic.message || '—' }}</div>
          <div v-if="astPayload.review_diagnostic.hint"><strong>hint:</strong> {{ astPayload.review_diagnostic.hint }}</div>
        </q-banner>

        <q-card flat bordered v-if="astPayload">
          <q-card-section>
            <div class="row items-center q-gutter-sm">
              <div class="text-h6">{{ astPayload.headword || '—' }}</div>
              <q-chip size="sm" color="grey-4" text-color="grey-8">#{{ astPayload.art_id }}</q-chip>
              <q-chip size="sm" color="blue-1" text-color="blue-9">{{ astPayload.lang }}</q-chip>
            </div>
          </q-card-section>

          <q-separator />

          <q-card-section class="column q-gutter-md">
            <q-expansion-item
              v-for="form in normalizedForms"
              :key="form.formId"
              default-opened
              icon="account_tree"
              :label="`form ${form.index}: ${form.title}`"
            >
              <div v-if="form.formLevelBlocks.length" class="q-ml-md q-mt-sm">
                <div class="text-caption text-grey-7 q-mb-xs">form-level blocks</div>
                <div class="column q-gutter-xs">
                  <div
                    v-for="block in form.formLevelBlocks"
                    :key="block.blockId"
                    class="ast-block"
                    :class="{ 'ast-block--selected': isSelected(form.formId, block.blockId) }"
                    @click="selectBlock(form.formId, block, $event)"
                  >
                    <BlockView :block="block" />
                  </div>
                </div>
              </div>

              <div v-for="sense in form.senses" :key="sense.senseKey" class="q-ml-md q-mt-sm">
                <div class="text-subtitle2">sense {{ sense.number }}</div>
                <div class="column q-gutter-xs q-mt-xs">
                  <div
                    v-for="block in sense.blocks"
                    :key="block.blockId"
                    class="ast-block"
                    :class="{ 'ast-block--selected': isSelected(form.formId, block.blockId) }"
                    @click="selectBlock(form.formId, block, $event)"
                  >
                    <BlockView :block="block" />
                  </div>
                </div>
              </div>
            </q-expansion-item>
          </q-card-section>
        </q-card>

        <q-banner v-else class="bg-grey-2 text-grey-8">
          Введи art_id и загрузи AST.
        </q-banner>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { computed, defineComponent, h, nextTick, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();

const langOptions = [
  { label: 'Эсперанто', value: 'eo' },
  { label: 'Русский', value: 'ru' },
];

const lang = ref('eo');
const artId = ref(null);
const loadingAst = ref(false);
const astPayload = ref(null);

const selectedBlock = ref(null);
const resolving = ref(false);
const applying = ref(false);
const reparsingArticle = ref(false);
const resettingArticle = ref(false);
const resettingBlock = ref(false);
const resolveResult = ref(null);
const selectedCandidate = ref(null);
const actionMode = ref('accept');
const editValue = ref('');
const blockFlags = ref({});
const queryInitialized = ref(false);
const selectedCardTop = ref(12);
const selectedCardRef = ref(null);

const canApply = computed(() => actionMode.value !== 'edit' || Boolean(editValue.value?.trim()));
const selectedCardStyle = computed(() => ({ top: `${selectedCardTop.value}px` }));

function pickStableId(candidates, fallback) {
  for (const candidate of candidates) {
    if (candidate == null) continue;
    const value = String(candidate).trim();
    if (value) return value;
  }
  return fallback;
}

function blockKey(formId, blockId) {
  return `${formId}:${blockId}`;
}

function hydrateFlagsFromResolvedBlocks(payload) {
  const source = payload?.resolved_blocks;
  if (!source || typeof source !== 'object') return {};

  const next = {};
  Object.entries(source).forEach(([key, value]) => {
    if (!key) return;
    next[key] = {
      applied: Boolean(value?.applied),
      dirty: false,
      operatorAction: value?.operator_action || null,
      updatedAt: value?.updated_at || null,
    };
  });
  return next;
}

function getBlockSourceText(block) {
  if (!block || typeof block !== 'object') return '';
  if (block.type === 'example_raw' || block.type === 'example') {
    return String(block.example_ru || block.raw || '').trim();
  }
  return String(block.raw || '').trim();
}

function getFinalLayerText(operatorAction) {
  if (!operatorAction || typeof operatorAction !== 'object') return null;
  const action = String(operatorAction.action || '').toLowerCase();
  if (!action) return null;
  if (action === 'reject') return '⛔ отклонено';

  const value = typeof operatorAction.value === 'string' ? operatorAction.value.trim() : '';
  const selected = typeof operatorAction.selected_candidate_id === 'string'
    ? operatorAction.selected_candidate_id.trim()
    : '';
  const text = value || selected;
  return text || '✅ подтверждено';
}

const normalizedForms = computed(() => {
  const forms = astPayload.value?.v4_ast?.forms;
  if (!Array.isArray(forms)) return [];

  return forms.map((form, formIndex) => {
    const formId = pickStableId(
      [form?.form_id, form?.id, form?.uuid, form?.key],
      `form_${formIndex}`,
    );

    const blocks = Array.isArray(form?.blocks) ? form.blocks : [];
    const mapped = blocks.map((block, blockIndex) => {
      const stableBlockId = pickStableId(
        [block?.block_id, block?.id, block?.uuid, block?.key],
        `block_${blockIndex}`,
      );
      const key = blockKey(formId, stableBlockId);
      const flags = blockFlags.value[key] || { applied: false, dirty: false };
      const sourceText = getBlockSourceText(block);
      const initialItems = splitItemsForAssist(sourceText);
      const initialText = initialItems.join(' | ');
      const finalText = getFinalLayerText(flags.operatorAction);
      return {
        ...block,
        blockId: stableBlockId,
        blockType: block?.type || 'unknown',
        raw: block?.raw || '',
        number: block?.number,
        senseNumber: block?.sense_number,
        exampleEo: block?.example_eo || '',
        exampleRu: block?.example_ru || '',
        sourceText,
        initialText,
        finalText,
        reviewFlag: classifyReviewFlag(block),
        applied: Boolean(flags.applied),
        dirty: Boolean(flags.dirty),
      };
    });

    const formLevelBlocks = mapped.filter((b) => b.scope === 'form' || b.senseNumber == null);
    const senseMap = new Map();

    mapped.forEach((b) => {
      if (b.senseNumber == null) return;
      if (!senseMap.has(b.senseNumber)) {
        senseMap.set(b.senseNumber, []);
      }
      senseMap.get(b.senseNumber).push(b);
    });

    const senses = Array.from(senseMap.entries()).map(([number, senseBlocks]) => ({
      senseKey: `s${number}`,
      number,
      blocks: senseBlocks,
    }));

    return {
      index: formIndex + 1,
      formId,
      title: form?.expanded || form?.raw || '—',
      formLevelBlocks,
      senses,
    };
  });
});

const candidateOptions = computed(() => {
  const candidates = resolveResult.value?.candidates;
  if (!Array.isArray(candidates)) return [];
  return candidates.map((item, idx) => ({ label: item, value: `c${idx}` }));
});

const BlockView = defineComponent({
  name: 'BlockView',
  props: {
    block: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    return () => {
      const b = props.block;
      const chips = [
        h('span', { class: 'text-caption text-grey-7' }, `type: ${b.blockType}`),
      ];
      if (b.reviewFlag && !b.applied) {
        chips.push(
          h(
            'span',
            { class: `text-caption q-ml-sm flag-chip flag-chip--${b.reviewFlag}` },
            b.reviewFlag,
          ),
        );
      }
      if (b.dirty) {
        chips.push(
          h(
            'span',
            { class: 'text-caption q-ml-sm flag-chip flag-chip--dirty' },
            'dirty',
          ),
        );
      }
      if (b.applied) {
        chips.push(
          h(
            'span',
            { class: 'text-caption q-ml-sm flag-chip flag-chip--applied' },
            'applied',
          ),
        );
      }
      if (b.number != null) {
        chips.push(h('span', { class: 'text-caption text-grey-7 q-ml-sm' }, `#${b.number}`));
      }

      const layers = [];
      if (b.finalText) {
        layers.push(h('div', { class: 'text-body2 text-weight-medium q-mt-xs layer-final' }, `финальный: ${b.finalText}`));
      }
      if (b.initialText) {
        layers.push(h('div', { class: 'text-body2 q-mt-xs layer-initial' }, `начальный: ${b.initialText}`));
      }
      layers.push(h('div', { class: 'text-caption text-grey-7 q-mt-xs layer-source' }, `исходник: ${b.sourceText || '—'}`));

      if (b.blockType === 'example_raw' || b.blockType === 'example') {
        return h('div', { class: 'column' }, [
          h('div', { class: 'row items-center q-gutter-sm' }, chips),
          h('div', { class: 'text-caption text-grey-8 q-mt-xs' }, `EO: <${b.exampleEo || '—'}>`),
          ...layers,
        ]);
      }

      return h('div', { class: 'column' }, [
        h('div', { class: 'row items-center q-gutter-sm' }, chips),
        ...layers,
      ]);
    };
  },
});

function classifyReviewFlag(block) {
  const raw = String(block?.raw || '').toLowerCase();

  const hasMany = raw.includes('_или_') || raw.includes('(_или_') || raw.includes('(или');
  if (hasMany) return 'many-to-many';

  const hasLineMergeRisk =
    (raw.includes(';') && raw.includes(',')) ||
    ((raw.includes('(') && raw.includes(')')) && (raw.includes(';') || raw.includes(','))) ||
    raw.split(';').length - 1 >= 2 ||
    raw.split(',').length - 1 >= 3;

  if (hasLineMergeRisk) return 'line-merge-risk';
  return 'clean';
}

function flagColor(flag) {
  if (flag === 'many-to-many') return 'deep-orange';
  if (flag === 'line-merge-risk') return 'orange';
  return 'positive';
}

function isSelected(formId, blockId) {
  return selectedBlock.value?.formId === formId && selectedBlock.value?.blockId === blockId;
}

function stripReviewMarkers(value) {
  let text = String(value || '').replace(/_/g, ' ').replace(/\s+/g, ' ').trim();
  if (!text) return '';

  const markerRe = /^(?:[а-яё]+\.|т\.е\.)\s+/i;
  while (markerRe.test(text)) {
    text = text.replace(markerRe, '').trim();
  }

  // Remove leading Esperanto control marker like 'iun' accidentally leaked from form heading.
  text = text.replace(/^([a-z]{2,6})\s+/i, (m, w) => (/^[a-z]{2,6}$/i.test(w) ? '' : m)).trim();
  return text;
}

function splitItemsForAssist(raw) {
  const text = String(raw || '').trim();
  if (!text) return [];
  const noTailSemicolon = text.replace(/;\s*$/g, '');
  const segments = noTailSemicolon
    .split(';')
    .map((part) => part.trim())
    .filter(Boolean);

  const out = [];
  segments.forEach((segment) => {
    const parts = segment
      .split(/,(?![^()]*\))/g)
      .map((part) => part.trim())
      .filter(Boolean);
    if (parts.length) {
      out.push(...parts);
    } else if (segment) {
      out.push(segment);
    }
  });

  const dedup = [];
  const seen = new Set();
  out.forEach((item) => {
    const cleaned = stripReviewMarkers(item).replace(/\s+/g, ' ').trim();
    if (!cleaned) return;
    const key = cleaned.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    dedup.push(cleaned);
  });

  return expandAbbreviatedSeries(dedup);
}

function looksLikeStandaloneAdjective(token) {
  const t = String(token || '').toLowerCase().trim();
  if (!t || t.includes(' ')) return false;
  return /(ый|ий|ой|ая|яя|ое|ее|ые|ие|ого|его|ому|ему|ым|им|ую|юю|ых|их|шийся|вшийся)$/.test(t);
}

function looksLikeSimpleNoun(token) {
  const t = String(token || '').toLowerCase().trim();
  if (!t || t.includes(' ')) return false;
  return /(т|рт|ние|ция|изм|ость|ка|ок|ик|ец|ор|арь|лог|аборт|плод|рифма)$/.test(t) || /[а-яё]$/.test(t);
}

function expandAbbreviatedSeries(items) {
  if (!Array.isArray(items) || items.length < 3) return items || [];

  const last = String(items[items.length - 1] || '').trim();
  const lastParts = last.split(/\s+/).filter(Boolean);
  // Expand only strict pattern: "adj, adj, adj noun"
  if (lastParts.length !== 2) return items;
  if (!looksLikeStandaloneAdjective(lastParts[0]) || !looksLikeSimpleNoun(lastParts[1])) return items;

  const prefixes = items.slice(0, -1);
  const canExpand = prefixes.length >= 2 && prefixes.every((item) => looksLikeStandaloneAdjective(item));
  if (!canExpand) return items;

  const suffix = lastParts[1];
  const expanded = [...prefixes.map((item) => `${item} ${suffix}`), last];

  const dedup = [];
  const seen = new Set();
  expanded.forEach((item) => {
    const cleaned = item.replace(/\s+/g, ' ').trim();
    if (!cleaned) return;
    const key = cleaned.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    dedup.push(cleaned);
  });

  return dedup;
}

function selectBlock(formId, block, event) {
  resolveResult.value = null;
  selectedCandidate.value = null;
  const key = blockKey(formId, block.blockId);
  const flags = blockFlags.value[key] || { applied: false, dirty: false };
  selectedBlock.value = {
    formId,
    blockId: block.blockId,
    raw: block.raw,
    blockType: block.blockType,
    reviewFlag: block.reviewFlag,
    applied: Boolean(flags.applied),
    dirty: Boolean(flags.dirty),
    context: {
      label: block.blockType,
      items: splitItemsForAssist(block.blockType === 'example_raw' ? (block.exampleRu || block.raw) : block.raw),
      source_raw: stripReviewMarkers(block.blockType === 'example_raw' ? (block.exampleRu || block.raw) : block.raw),
      number: block.number,
      sense_number: block.senseNumber,
      example_eo: block.exampleEo,
      example_ru: block.exampleRu,
    },
  };
  actionMode.value = 'accept';
  editValue.value = '';

  const targetEl = event?.currentTarget;
  if (typeof window !== 'undefined' && targetEl && typeof targetEl.getBoundingClientRect === 'function') {
    const rect = targetEl.getBoundingClientRect();
    const anchorTop = Math.round(rect.top - 12);

    nextTick(() => {
      const cardEl = selectedCardRef.value?.$el || selectedCardRef.value;
      const cardHeight =
        cardEl && typeof cardEl.getBoundingClientRect === 'function'
          ? cardEl.getBoundingClientRect().height
          : 360;
      const vh = window.innerHeight || document.documentElement.clientHeight || 800;
      const minTop = 12;
      const maxTop = Math.max(minTop, Math.round(vh - cardHeight - 12));
      selectedCardTop.value = Math.min(maxTop, Math.max(minTop, anchorTop));
    });
  } else {
    selectedCardTop.value = 12;
  }
}

function setActionMode(mode) {
  actionMode.value = mode;
}

function syncQueryFromState() {
  if (!queryInitialized.value) return;
  const nextQuery = {
    ...route.query,
    lang: lang.value,
  };
  if (artId.value) {
    nextQuery.art_id = String(artId.value);
  } else {
    delete nextQuery.art_id;
  }
  router.replace({ query: nextQuery }).catch(() => {});
}

function initFromQuery() {
  const qLang = typeof route.query.lang === 'string' ? route.query.lang : null;
  if (qLang && langOptions.some((item) => item.value === qLang)) {
    lang.value = qLang;
  }

  const qArt = Number(route.query.art_id);
  if (Number.isFinite(qArt) && qArt > 0) {
    artId.value = qArt;
  }

  queryInitialized.value = true;
  if (artId.value) {
    loadAst();
  }
}

watch([lang, artId], () => {
  syncQueryFromState();
});

initFromQuery();

async function loadAst() {
  if (!artId.value) return;
  loadingAst.value = true;
  resolveResult.value = null;
  selectedCandidate.value = null;
  selectedBlock.value = null;
  actionMode.value = 'accept';
  editValue.value = '';
  blockFlags.value = {};

  try {
    const { data } = await api.get(`/admin/v4/articles/${lang.value}/${artId.value}/ast`);
    astPayload.value = data;
    blockFlags.value = hydrateFlagsFromResolvedBlocks(data);
  } catch (err) {
    console.error(err);
    astPayload.value = null;
    $q.notify({ type: 'negative', message: 'Не удалось загрузить AST' });
  } finally {
    loadingAst.value = false;
  }
}

async function runResolve() {
  if (!selectedBlock.value || !artId.value) {
    $q.notify({ type: 'warning', message: 'Сначала выбери блок' });
    return;
  }

  resolving.value = true;
  resolveResult.value = null;
  selectedCandidate.value = null;
  try {
    const payload = {
      article_id: artId.value,
      lang: lang.value,
      form_id: selectedBlock.value.formId,
      block_id: selectedBlock.value.blockId,
      context: selectedBlock.value.context || {},
    };
    const { data } = await api.post('/admin/v4/resolve-block', payload);
    resolveResult.value = data;
    if (Array.isArray(data?.candidates) && data.candidates.length) {
      selectedCandidate.value = 'c0';
    }
    const key = blockKey(selectedBlock.value.formId, selectedBlock.value.blockId);
    blockFlags.value = {
      ...blockFlags.value,
      [key]: {
        applied: Boolean(blockFlags.value[key]?.applied),
        dirty: true,
      },
    };
    selectedBlock.value = {
      ...selectedBlock.value,
      applied: Boolean(blockFlags.value[key]?.applied),
      dirty: true,
    };
    $q.notify({ type: 'positive', message: 'Gemma Assist: черновик получен' });
  } catch (err) {
    console.error(err);
    $q.notify({ type: 'negative', message: 'Gemma Assist не ответил' });
  } finally {
    resolving.value = false;
  }
}

async function applyResolution() {
  if (!selectedBlock.value || !artId.value) {
    $q.notify({ type: 'warning', message: 'Сначала выбери блок' });
    return;
  }
  if (actionMode.value === 'edit' && !editValue.value?.trim()) {
    $q.notify({ type: 'warning', message: 'Для Edit введи значение' });
    return;
  }

  applying.value = true;
  try {
    const selectedIdx = selectedCandidate.value ? Number(selectedCandidate.value.replace('c', '')) : null;
    const selectedCandidateValue =
      selectedIdx != null && Number.isFinite(selectedIdx)
        ? (resolveResult.value?.candidates || [])[selectedIdx] || null
        : ((resolveResult.value?.candidates || [])[0] || null);

    const payload = {
      article_id: artId.value,
      lang: lang.value,
      form_id: selectedBlock.value.formId,
      block_id: selectedBlock.value.blockId,
      operator_action: {
        action: actionMode.value,
        selected_candidate_id: selectedCandidateValue,
        value: actionMode.value === 'edit' ? editValue.value.trim() : selectedCandidateValue,
        comment: 'MVP apply from v4-review screen',
      },
    };
    await api.post('/admin/v4/apply-resolution', payload);

    const key = blockKey(selectedBlock.value.formId, selectedBlock.value.blockId);
    blockFlags.value = {
      ...blockFlags.value,
      [key]: {
        applied: true,
        dirty: false,
        operatorAction: payload.operator_action,
      },
    };
    selectedBlock.value = { ...selectedBlock.value, applied: true, dirty: false };

    $q.notify({ type: 'positive', message: `Действие ${actionMode.value} применено` });
  } catch (err) {
    console.error(err);
    $q.notify({ type: 'negative', message: 'Apply не выполнен' });
  } finally {
    applying.value = false;
  }
}

async function reparseArticle() {
  if (!artId.value) return;
  reparsingArticle.value = true;
  try {
    await api.post(`/admin/articles/${lang.value}/${artId.value}/reparse`);
    await loadAst();
    $q.notify({ type: 'positive', message: 'Статья переразобрана' });
  } catch (err) {
    console.error(err);
    $q.notify({ type: 'negative', message: 'Не удалось переразобрать статью' });
  } finally {
    reparsingArticle.value = false;
  }
}

async function resetArticleResolutions() {
  if (!artId.value) return;
  try {
    await $q.dialog({
      title: 'Сброс подтверждений',
      message: `Сбросить все подтверждения для статьи #${artId.value}?`,
      cancel: true,
      persistent: true,
      ok: { label: 'Сбросить', color: 'negative' },
    });
  } catch {
    return;
  }

  resettingArticle.value = true;
  try {
    await api.post(`/admin/articles/${lang.value}/${artId.value}/reset`);
    await loadAst();
    $q.notify({ type: 'positive', message: 'Подтверждения статьи сброшены' });
  } catch (err) {
    console.error(err);
    $q.notify({ type: 'negative', message: 'Не удалось сбросить подтверждения статьи' });
  } finally {
    resettingArticle.value = false;
  }
}

async function resetSelectedBlock() {
  if (!selectedBlock.value || !artId.value) {
    $q.notify({ type: 'warning', message: 'Сначала выбери блок' });
    return;
  }

  const target = `${selectedBlock.value.formId}:${selectedBlock.value.blockId}`;
  try {
    await $q.dialog({
      title: 'Сброс блока',
      message: `Сбросить подтверждение для блока ${target}?`,
      cancel: true,
      persistent: true,
      ok: { label: 'Сбросить', color: 'negative' },
    });
  } catch {
    return;
  }

  resettingBlock.value = true;
  try {
    await api.post('/admin/v4/reset-block', {
      article_id: artId.value,
      lang: lang.value,
      form_id: selectedBlock.value.formId,
      block_id: selectedBlock.value.blockId,
    });
    await loadAst();
    $q.notify({ type: 'positive', message: 'Подтверждение блока сброшено' });
  } catch (err) {
    console.error(err);
    $q.notify({ type: 'negative', message: 'Не удалось сбросить подтверждение блока' });
  } finally {
    resettingBlock.value = false;
  }
}
</script>

<style scoped>
.ast-block {
  border: 1px solid var(--q-color-grey-4);
  border-radius: 8px;
  padding: 8px 10px;
  cursor: pointer;
}

.ast-block--selected {
  border-color: var(--q-color-primary);
  background: rgba(25, 118, 210, 0.08);
}

.flag-chip,
:deep(.flag-chip) {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 1px 8px;
  color: #fff;
  font-weight: 600;
  line-height: 1.4;
}

.flag-chip--clean,
:deep(.flag-chip--clean) {
  background: #2e7d32;
}

.flag-chip--line-merge-risk,
:deep(.flag-chip--line-merge-risk) {
  background: #ef6c00;
}

.flag-chip--many-to-many,
:deep(.flag-chip--many-to-many) {
  background: #d84315;
}

.flag-chip--dirty,
:deep(.flag-chip--dirty) {
  background: #f9a825;
  color: #111;
}

.flag-chip--applied,
:deep(.flag-chip--applied) {
  background: #2e7d32;
}

.layer-final {
  color: #1b5e20;
}

.layer-initial {
  color: #37474f;
}

.layer-source {
  font-style: italic;
}

.selected-block-card {
  position: sticky;
  top: 12px;
  align-self: flex-start;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: visible;
}

.admin-v4-review :deep(.col-12),
.admin-v4-review :deep(.col-md-4),
.admin-v4-review :deep(.col-md-8) {
  min-width: 0;
}

.admin-v4-review :deep(.col-md-4) {
  overflow: visible;
}

:deep(.selected-block-card .q-card__section),
:deep(.selected-block-card .row),
:deep(.selected-block-card .column),
:deep(.selected-block-card .text-caption),
:deep(.selected-block-card .text-body2) {
  min-width: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
  word-break: break-word;
}

:deep(.selected-block-card .q-field),
:deep(.selected-block-card .q-field__control),
:deep(.selected-block-card .q-field__control-container),
:deep(.selected-block-card .q-field__native),
:deep(.selected-block-card .q-field__input) {
  min-width: 0;
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
}

:deep(.selected-block-card .q-field__native),
:deep(.selected-block-card .q-field__input) {
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
}

:deep(.selected-block-card .row) {
  flex-wrap: wrap;
}

:deep(.selected-block-card .ellipsis),
:deep(.selected-block-card .q-chip__content),
:deep(.selected-block-card .q-field__native span),
:deep(.selected-block-card .q-field__label),
:deep(.selected-block-card .q-select__dropdown-icon + div) {
  white-space: normal !important;
  text-overflow: clip !important;
  overflow: visible !important;
  overflow-wrap: anywhere;
  word-break: break-word;
}


.raw-preview {
  white-space: normal;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.fit-input {
  max-width: 100%;
}

:deep(.fit-input .q-field__control),
:deep(.fit-input .q-field__native),
:deep(.fit-input .q-field__input),
:deep(.selected-block-card .q-card__section),
:deep(.selected-block-card .q-select__dropdown-icon) {
  min-width: 0;
}

:deep(.selected-block-card .q-field__native),
:deep(.selected-block-card .q-field__input) {
  overflow-wrap: anywhere;
  word-break: break-word;
}


@media (max-width: 1023px) {
  .selected-block-card {
    position: static;
    top: auto;
  }
}

</style>
