# Tasks: Dark Mode

## Task 1 — Enable Tailwind class-based dark mode

**File:** `frontend/tailwind.config.js`

- [x] Add `darkMode: 'class'` at the top level of the config object

Test: `grep darkMode frontend/tailwind.config.js` outputs `darkMode: 'class'`.

---

## Task 2 — Create `useDarkMode` hook

**File:** `frontend/src/hooks/useDarkMode.ts` (new file)

- [x] Implement hook that:
  - Initializes `dark` state from `localStorage.getItem('dark-mode')`, falling back to `window.matchMedia('(prefers-color-scheme: dark)').matches`
  - On every `dark` state change: toggles `dark` class on `document.documentElement` and writes to `localStorage`
  - Returns `{ dark: boolean, toggle: () => void }`

Test: import succeeds; toggling applies/removes `.dark` on `<html>`.

---

## Task 3 — Add toggle button to `Layout.tsx`

**File:** `frontend/src/components/Layout.tsx`

- [x] Import `useDarkMode` from `../hooks/useDarkMode`
- [x] Call `useDarkMode()` to get `{ dark, toggle }`
- [x] Add a `<button>` immediately before the "Sign out" button that:
  - Calls `toggle` on click
  - Shows a Sun SVG icon when `dark === true` (click → go light)
  - Shows a Moon SVG icon when `dark === false` (click → go dark)
  - Has `aria-label` and `title` attributes for accessibility
  - Uses classes `text-gray-400 hover:text-white transition-colors`

Test: button appears in header; clicking it toggles dark mode visually; preference persists after reload.

---

## Task 4 — Dark variants for component classes in `index.css`

**File:** `frontend/src/index.css`

Update each `@layer components` class and the `@layer base body` rule with dark variants:

- [x] `body`: add `dark:bg-gray-900 dark:text-gray-100`
- [x] `.card`: add `dark:bg-gray-800 dark:border-gray-700`
- [x] `.btn-secondary`: add `dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-600`
- [x] `.input`: add `dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100 dark:placeholder-gray-500`
- [x] `.label`: add `dark:text-gray-300`
- [x] `.badge-gray`: add `dark:bg-gray-700 dark:text-gray-300`
- [x] `.badge-green`: add `dark:bg-green-900 dark:text-green-200`
- [x] `.badge-red`: add `dark:bg-red-900 dark:text-red-200`

Test: `.card` elements show dark background; `.btn-secondary` shows dark styled buttons.

---

## Task 5 — Dark variants in `DashboardPage.tsx`

**File:** `frontend/src/pages/DashboardPage.tsx`

- [x] Add `dark:` variants to table `thead` rows (`bg-gray-50` → `+ dark:bg-gray-700`)
- [x] Add `dark:` variants to `divide-gray-*` / `border-gray-*` classes on table wrappers and `tbody`
- [x] Add `dark:` variants to supplementary text colors (`text-gray-500`, `text-gray-400`)
- [x] Add `dark:` variants to `text-gray-700` and `text-gray-900` inline headings/labels

---

## Task 6 — Dark variants in `LeaguePage.tsx`

**File:** `frontend/src/pages/LeaguePage.tsx`

- [x] Add `dark:` variants to table theads (`bg-gray-50 dark:bg-gray-700`)
- [x] Add `dark:` variants to `divide-*` and `border-*` table internals
- [x] Add `dark:` variants to supplementary text (`text-gray-500`, `text-gray-400`, `text-gray-600`)
- [x] Add `dark:` variants to inline `bg-white` panels that aren't already using `.card`

---

## Task 7 — Dark variants in `DraftPage.tsx`

**File:** `frontend/src/pages/DraftPage.tsx`

- [x] Add `dark:` variants to table theads and row backgrounds
- [x] Add `dark:` variants to descriptive text colors
- [x] Add `dark:` variants to any explicit `bg-white` / `bg-gray-50` panel backgrounds not using `.card`

---

## Task 8 — Dark variants in `RosterPage.tsx` and `RosterViewPage.tsx`

**Files:** `frontend/src/pages/RosterPage.tsx`, `frontend/src/pages/RosterViewPage.tsx`

- [x] Add `dark:` variants to table theads, dividers, and supplementary text in both files

---

## Task 9 — Dark variants in `AdminPage.tsx`

**File:** `frontend/src/pages/AdminPage.tsx`

- [x] Add `dark:` variants to all table `thead` rows and `tbody` row backgrounds
- [x] Add `dark:` variants to `divide-*` separators
- [x] Add `dark:` variants to supplementary text colors
- [x] Add `dark:` variants to any inline `bg-white`/`bg-gray-50` that aren't `.card`
- [x] Check accordion panels and scoring event tables

---

## Task 10 — Dark variants in `InfoPage.tsx` and `CreateLeaguePage.tsx`

**Files:** `frontend/src/pages/InfoPage.tsx`, `frontend/src/pages/CreateLeaguePage.tsx`

- [x] Add `dark:` variants to any inline text colors and backgrounds

---

## Task 11 — Rebuild and redeploy frontend

- [x] `docker compose build frontend && docker compose up -d frontend`
- [x] Verify toggle appears in header, dark mode applies site-wide, and persists on reload

---

## Implementation Order

| Task | Depends on |
|------|------------|
| 1 — Tailwind config | — |
| 2 — `useDarkMode` hook | 1 |
| 3 — Layout toggle button | 2 |
| 4 — `index.css` dark variants | 1 |
| 5–10 — Per-page dark variants | 1, 4 |
| 11 — Rebuild + deploy | 3, 4, 5–10 |
