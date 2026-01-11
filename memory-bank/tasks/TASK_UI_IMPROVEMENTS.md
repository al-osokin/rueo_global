# Task: UI Improvements for AdminReview

## Context
User needs two UI improvements in admin review interface for better workflow:
1. Display current article ID (art_id) in the interface
2. Add ability to reparse articles in a range (from X to Y)

## Current State

### Files
- **Frontend:** `/home/avo/rueo_global/frontend-app/src/pages/AdminReview.vue`
- **Backend:** `/home/avo/rueo_global/backend/app/admin.py`

### Existing Features
1. **"Переразобрать проблемные"** button (line 100):
   - Calls `reparseArticles()` function (line 665)
   - Endpoint: `POST /admin/articles/{lang}/reparse`
   - Accepts `include_pending` flag (toggle on line 106)
   - Backend: `reparse_article_batch()` (admin.py line 243)

2. **"Переразобрать открытую"** button (line 159):
   - Calls `reparseCurrentArticle()` function
   - Endpoint: `POST /admin/articles/{lang}/{art_id}/reparse`
   - Backend: `reparse_single_article()` (admin.py line 296)

3. **"Перейти по art_id"** input field (line 57):
   - Model: `directArtId` (number input)
   - On enter or arrow button: calls `loadArticle(directArtId)`

### Backend API Endpoint (Already Exists!)
**POST /admin/articles/{lang}/reparse** (admin.py line 243):
```python
@router.post("/articles/{lang}/reparse", response_model=ReparseResponse)
def reparse_article_batch(
    lang: str,
    payload: ReparseRequest,
    session=Depends(get_session),
):
    _ensure_lang(lang)
    service = ArticleReviewService(session)
    result = service.reparse_articles(
        lang,
        art_ids=payload.art_ids,  # ← ALREADY SUPPORTS art_ids list!
        include_pending=payload.include_pending,
    )
    return ReparseResponse(**result)
```

**Important:** Backend already supports `art_ids` parameter! When `art_ids` is provided, it reparses ONLY those IDs. When `art_ids` is None/empty, it reparses by status (needs_review).

## Task 1: Display Current Article ID

### Requirements
Display current article ID in **TWO places**:

1. **In "Перейти по art_id" input field:**
   - Auto-fill with current article ID when article is loaded
   - User can see ID and easily copy it
   - Input remains editable for navigation

2. **Near article title/headword:**
   - Add small badge or label showing "ID: 270" or "#270"
   - Always visible, doesn't interfere with layout
   - Placed near headword display (around line 139-144)

### Implementation Guide

**Location 1: Input field auto-fill**
- Find `loadArticle()` function and add:
  ```javascript
  directArtId.value = articleData.art_id;
  ```
- This auto-fills the input when article loads

**Location 2: Badge near title**
- Find article headword display section (around line 139-144)
- Add small badge/chip showing art_id:
  ```vue
  <div class="row items-center q-gutter-sm">
    <div class="text-h5">{{ article.headword }}</div>
    <q-chip size="sm" color="grey-4" text-color="grey-8">
      #{{ article.art_id }}
    </q-chip>
  </div>
  ```

## Task 2: Range Reparse UI

### Requirements
Add UI for reparsing articles in a range (e.g., from ID 1 to ID 50).

**Location:** Add to "Сервис" card section (after "Переразобрать проблемные" button, around line 110)

### Implementation Guide

**1. Add reactive variables (in setup()):**
```javascript
const reparseRangeFrom = ref(null);
const reparseRangeTo = ref(null);
const reparseRangeLoading = ref(false);
```

**2. Add UI elements (in template, after line 110):**
```vue
<div class="text-caption text-grey-7 q-mt-md">Или перегенерить диапазон:</div>
<div class="row q-col-gutter-sm">
  <div class="col-6">
    <q-input
      v-model.number="reparseRangeFrom"
      label="С art_id"
      type="number"
      dense
      outlined
      :min="1"
    />
  </div>
  <div class="col-6">
    <q-input
      v-model.number="reparseRangeTo"
      label="По art_id"
      type="number"
      dense
      outlined
      :min="1"
    />
  </div>
</div>
<q-btn
  color="primary"
  outline
  label="Перегенерить все с ... по ..."
  :loading="reparseRangeLoading"
  :disable="reparseRangeLoading || !reparseRangeFrom || !reparseRangeTo"
  @click="reparseRange"
/>
```

**3. Add function (in setup(), near `reparseArticles` function around line 665):**
```javascript
const reparseRange = async () => {
  if (reparseRangeLoading.value || !reparseRangeFrom.value || !reparseRangeTo.value) {
    return;
  }
  
  if (reparseRangeFrom.value > reparseRangeTo.value) {
    $q.notify({ 
      type: "warning", 
      message: "Начальный ID должен быть меньше конечного" 
    });
    return;
  }
  
  reparseRangeLoading.value = true;
  try {
    // Generate array of art_ids from range
    const art_ids = [];
    for (let id = reparseRangeFrom.value; id <= reparseRangeTo.value; id++) {
      art_ids.push(id);
    }
    
    const payload = { art_ids };  // Backend already supports this!
    const { data } = await api.post(`/admin/articles/${lang.value}/reparse`, payload);
    
    const updated = data?.updated ?? 0;
    const failed = data?.failed_details ?? [];
    
    if (updated) {
      $q.notify({ 
        type: "positive", 
        message: `Переразобрано ${updated} статей из диапазона ${reparseRangeFrom.value}-${reparseRangeTo.value}` 
      });
    }
    if (failed.length) {
      console.warn("Failed to reparse:", failed);
      $q.notify({ 
        type: "warning", 
        message: `Не удалось переразобрать ${failed.length} статей` 
      });
    }
    
    // Reload current article if it was in the range
    if (article.value?.art_id >= reparseRangeFrom.value && 
        article.value?.art_id <= reparseRangeTo.value) {
      await loadArticle(article.value.art_id);
    }
    
    await loadStats();
  } catch (err) {
    console.error(err);
    $q.notify({ type: "negative", message: "Не удалось переразобрать диапазон" });
  } finally {
    reparseRangeLoading.value = false;
  }
};
```

## Testing

### Test Case 1: Article ID Display
1. Open admin review page
2. Load any article (e.g., art_id=270)
3. Verify:
   - "Перейти по art_id" input shows "270"
   - Badge/chip near headword shows "#270" or "ID: 270"
4. Navigate to another article
5. Verify ID updates in both places

### Test Case 2: Range Reparse
1. Enter range: from=1, to=50
2. Click "Перегенерить все с ... по ..."
3. Verify:
   - Request sent to `/admin/articles/eo/reparse` with `{"art_ids": [1, 2, ..., 50]}`
   - Success notification shows count and range
   - Stats update after completion
4. Test edge cases:
   - Empty fields → button disabled
   - from > to → warning notification
   - Large range (e.g., 1-1000) → works but may take time

## Backend Note
**NO BACKEND CHANGES NEEDED!** The existing endpoint already supports `art_ids` parameter.

## Expected Result
1. User can see current article ID in two places
2. User can reparse specific ranges for testing parser fixes
3. No need to reparse all 46k+ articles when debugging

## Files to Modify
- `/home/avo/rueo_global/frontend-app/src/pages/AdminReview.vue` (only file to change)

## Success Criteria
- [ ] Article ID displayed in "Перейти по art_id" input when article loads
- [ ] Article ID displayed as badge/chip near article headword
- [ ] Two new input fields for range (from/to) added to UI
- [ ] "Перегенерить все с ... по ..." button added and working
- [ ] Range validation works (from <= to)
- [ ] Success notification shows range and count
- [ ] No console errors
- [ ] Code follows existing Vue 3 Composition API style
