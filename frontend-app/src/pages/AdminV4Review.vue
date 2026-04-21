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
          </q-card-section>
        </q-card>

        <q-card flat bordered class="q-mt-lg" v-if="selectedBlock">
          <q-card-section class="column q-gutter-sm">
            <div class="text-subtitle1">Выбранный блок</div>
            <div class="text-caption text-grey-8">form_id: {{ selectedBlock.formId }}</div>
            <div class="text-caption text-grey-8">block_id: {{ selectedBlock.blockId }}</div>
            <div class="text-body2 q-mt-xs">{{ selectedBlock.raw || '—' }}</div>
            <q-chip
              v-if="selectedBlock?.applied"
              size="sm"
              color="positive"
              text-color="white"
              icon="check"
            >applied</q-chip>

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
              <q-select
                v-model="selectedCandidate"
                :options="candidateOptions"
                dense
                outlined
                label="Кандидат для apply"
                emit-value
                map-options
              />
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
              dense
              outlined
              label="Значение для Edit"
              class="q-mt-sm"
            />

            <q-btn
              color="positive"
              outline
              label="Apply resolution"
              :loading="applying"
              :disable="applying || !astPayload || !canApply"
              @click="applyResolution"
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
                    @click="selectBlock(form.formId, block)"
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
                    @click="selectBlock(form.formId, block)"
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
import { computed, defineComponent, h, ref } from 'vue';
import { useQuasar } from 'quasar';
import { api } from 'boot/axios';

const $q = useQuasar();

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
const resolveResult = ref(null);
const selectedCandidate = ref(null);
const actionMode = ref('accept');
const editValue = ref('');
const appliedBlocks = ref({});

const canApply = computed(() => actionMode.value !== 'edit' || Boolean(editValue.value?.trim()));

const normalizedForms = computed(() => {
  const forms = astPayload.value?.v4_ast?.forms;
  if (!Array.isArray(forms)) return [];

  return forms.map((form, formIndex) => {
    const blocks = Array.isArray(form?.blocks) ? form.blocks : [];
    const mapped = blocks.map((block, blockIndex) => ({
      ...block,
      blockId: `b${blockIndex}`,
      blockType: block?.type || 'unknown',
      raw: block?.raw || '',
      number: block?.number,
      senseNumber: block?.sense_number,
      exampleEo: block?.example_eo || '',
      exampleRu: block?.example_ru || '',
    }));

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
      formId: `f${formIndex}`,
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
      if (b.number != null) {
        chips.push(h('span', { class: 'text-caption text-grey-7 q-ml-sm' }, `#${b.number}`));
      }

      if (b.blockType === 'example_raw' || b.blockType === 'example') {
        return h('div', { class: 'column' }, [
          h('div', { class: 'row items-center q-gutter-sm' }, chips),
          h('div', { class: 'text-body2 text-weight-medium q-mt-xs' }, `пример <${b.exampleEo || '—'}>`),
          h('div', { class: 'text-body2 q-mt-xs' }, `перевод: ${b.exampleRu || '—'}`),
        ]);
      }

      return h('div', { class: 'column' }, [
        h('div', { class: 'row items-center q-gutter-sm' }, chips),
        h('div', { class: 'text-body2 q-mt-xs' }, b.raw || '—'),
      ]);
    };
  },
});

function isSelected(formId, blockId) {
  return selectedBlock.value?.formId === formId && selectedBlock.value?.blockId === blockId;
}

function selectBlock(formId, block) {
  const key = `${formId}:${block.blockId}`;
  selectedBlock.value = {
    formId,
    blockId: block.blockId,
    raw: block.raw,
    blockType: block.blockType,
    applied: Boolean(appliedBlocks.value[key]),
    context: {
      label: block.blockType,
      items: [block.raw].filter(Boolean),
      number: block.number,
      sense_number: block.senseNumber,
      example_eo: block.exampleEo,
      example_ru: block.exampleRu,
    },
  };
  actionMode.value = 'accept';
  editValue.value = '';
}

function setActionMode(mode) {
  actionMode.value = mode;
}

async function loadAst() {
  if (!artId.value) return;
  loadingAst.value = true;
  resolveResult.value = null;
  selectedCandidate.value = null;
  selectedBlock.value = null;
  actionMode.value = 'accept';
  editValue.value = '';
  appliedBlocks.value = {};

  try {
    const { data } = await api.get(`/admin/v4/articles/${lang.value}/${artId.value}/ast`);
    astPayload.value = data;
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
        : null;

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

    const key = `${selectedBlock.value.formId}:${selectedBlock.value.blockId}`;
    appliedBlocks.value = { ...appliedBlocks.value, [key]: true };
    selectedBlock.value = { ...selectedBlock.value, applied: true };

    $q.notify({ type: 'positive', message: `Действие ${actionMode.value} применено` });
  } catch (err) {
    console.error(err);
    $q.notify({ type: 'negative', message: 'Apply не выполнен' });
  } finally {
    applying.value = false;
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
</style>
