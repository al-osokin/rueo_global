# Frontend Spec

This spec documents the Stage I frontend application behavior as recorded in `frontend-app/memory-bank/*`.

Primary references
- App source: `frontend-app/src/`
- Memory bank: `frontend-app/memory-bank/*`
- PWA docs: `frontend-app/memory-bank/docs/pwa-cache-update.md`

Verification note
- This spec is derived from memory-bank docs. No commands were executed.

## Purpose and users (from memory-bank)

The frontend provides an end-user UI for:
- dictionary search (Esperanto <-> Russian)
- viewing a project news feed
- reporting typos via an Orphus-style flow

Target users
- Esperanto learners
- Esperanto teachers
- language enthusiasts
- users needing translation

## Tech stack (as implemented)

Framework and tooling
- Vue 3 (Composition API)
- Quasar Framework
- Vue Router
- Vite
- ESLint
- PostCSS

Key dependencies
- `quasar`
- `axios`
- `vue-router`
- `markdown-it` (news rendering)

## Project structure (high level)

From `frontend-app/memory-bank/techContext.md`:
- `src/components/` reusable components
- `src/pages/` pages (including `Index.vue`, `novajxoj.vue`)
- `src/router/` routes
- `src/layouts/` layouts
- `src/boot/` boot files
- `src/css/` styles
- `src/i18n/` localization
- `src/utils/` utilities
- `public/news.md` (news in Markdown)
- `public/icons/` app icons

## API integrations (from memory-bank)

External services
- `old.rueo.ru` was used to fetch update date in older flows
- `/status/info` on the new backend returns update info in Stage I

Data formats
- Markdown for news (`public/news.md`)
- HTML for search results
- JSON for search history

Update mechanisms
- manual refresh button in the news UI
- automatic news update check every 3 hours
- UI shows time of last update
- notifications when new items appear

## Key UI components and patterns

Core components (from `systemPatterns.md`)
- `NewsFeed.vue`: news list with pagination
- `Index.vue`: homepage with search + news feed
- `novajxoj.vue`: page showing full news archive with pagination
- `MainLayout.vue`: shared layout

State handling
- component-local state for news
- LocalStorage for search history (`rueo_history`)
- reactive props for pagination

Performance and UX notes (from memory-bank)
- routes are lazy-loaded
- search input is debounced
- layout uses Quasar breakpoints for responsive behavior
- UI aims for accessibility (semantic markup, keyboard navigation)

Routing patterns
- Vue Router with lazy-loaded pages
- named routes; nested routes for content sections

## News system details

News file format
- `public/news.md` (Markdown)
- blocks separated by a line containing `---`
- each block has a `#` H1 title and body content

Parsing and update logic (from memory-bank)
- client-side parsing into an array of news items
- manual refresh button
- auto-update checks every 3 hours
- update is detected by change in number of items
- notifications on new items
- news order follows file order (date sorting removed during Markdown migration)
- UI shows last update time and provides a toggle for auto-update
- H1-H6 heading styles were added to match the site theme and improve readability

Pagination and pages
- `/novajxoj` page shows all news with pagination
- pagination supports 10/20/50 items per page
- homepage includes a "Show all news" button styled to match the site theme

Migration note
- The news system was migrated from Textile (`news.textile`) to Markdown (`news.md`).
- The Textile file is no longer present in this repo.

## Search UI behavior (from memory-bank)

Search and suggestions
- debounced input to reduce request volume
- autocomplete via Quasar `q-select`
- search history stored in `rueo_history`

Permalink handling for spaces (from `frontend-app/memory-bank/activeContext.md`)
- frontend normalizes permalinks so spaces are encoded as `+`
- it also normalizes inbound permalinks (`%20`, `%2520`, spaces) back to `+`
- when rendering in the search box, `+` is converted back to a space
- API requests for search and suggest were updated to build URLs manually to preserve `+` encoding

Historical completion notes (from memory-bank)
- The news pagination work and `/novajxoj` page are marked as completed and tested.
- Manual and automatic news update flows are marked as completed.
- Test snapshot mentions dev server running at `http://localhost:8081/`.

## Orphus-style typo reporting (memory-bank notes)

User flow
- user selects text, triggers a report dialog, and submits a form
- UI shows a success notification immediately (optimistic UI)
- background request is sent with a long timeout

Implementation notes (from memory-bank)
- The memory-bank doc references a PHP endpoint (`/orph.php`) and helper files under `frontend-app/public/`, but those PHP files are not present in this repo.
- Dev flow references `frontend-app/start-php-server.sh` for running a local PHP server.
- This suggests parts of the Orphus flow may live outside this repo in production.
- The historical fix notes include:
  - optimistic UI (notify success immediately, send in background)
  - long request timeouts (60s) to cover slow SMTP sessions
  - PHP-side async send (`ignore_user_abort`, `set_time_limit`) with logging
  - log files under a `public/logs/` directory (not present in this repo)

## PWA cache and update system

From `frontend-app/memory-bank/docs/pwa-cache-update.md` and `progress.md`:

Components
- Custom service worker: `src-pwa/custom-service-worker.js`
  - cache versioning via `CACHE_VERSION`
  - cache-first for static assets, network-first for API
  - deletes old caches on activation
- Service worker registration: `src-pwa/register-service-worker.js`
- Cache manager: `src/utils/cache-manager.js`
  - checks version via `/package.json`
  - clears caches and reloads when version changes

Update cadence
- periodic checks every 30 minutes
- auto reload on new version

Versioning workflow (from memory-bank)
1) Update version in `package.json`.
2) Copy to `public/package.json`.
3) Update `CACHE_VERSION` in `custom-service-worker.js`.
4) Build and deploy: `quasar build -m pwa`.

Deployment notes
- `public/package.json` is copied into the build output and must be accessible at `/package.json` without caching.
- The runtime `__PACKAGE_VERSION__` constant is injected from `package.json` during build.

Automation helper
- `frontend-app/bump-version.sh <version>` updates:
  - `package.json`
  - `public/package.json`
  - `src-pwa/custom-service-worker.js` (CACHE_VERSION)

Known issues and fixes (from memory-bank)
- Avoid double reload loops by using a single source of truth for reloads (cache-manager) and guarding with a `lastReloadVersion` value in LocalStorage.
- Ensure `/package.json` is served without caching or the update detector will misfire.
