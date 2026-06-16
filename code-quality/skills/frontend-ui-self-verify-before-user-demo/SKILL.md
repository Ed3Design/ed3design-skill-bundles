---
name: frontend-ui-self-verify-before-user-demo
description: |-
  Use when a frontend/UI change has been deployed (Vite/React/Vue, FastAPI Jinja, Electron, any browser-rendered surface) AND you are about to tell the user "refresh the browser", "check the app", "it's deployed" — STOP and self-verify first via Playwright/Chrome-DevTools-MCP: `browser_navigate` → `browser_snapshot` → `browser_take_screenshot` → `browser_evaluate` (DOM-query the element/text/style you changed). Especially required when (a) the surface has multiple modes (edit/preview/print, light/dark, mobile/desktop) and the user may view a different one than you changed, (b) the user already complained "nothing changed" — switch to verify-mode, do NOT add cache-busting theories, (c) you rebuilt >2 times without visual confirmation. Do NOT load for backend-only changes, for changes the user said to deploy without checking, or for features needing auth/state a headless browser cannot reach. Prevents burning debug-rounds on cache-theories when the change rendered in a mode the user wasn't looking at.
---

# Frontend-UI Self-Verify Before User Demo

## Overview

Before you tell the user "check the app", "refresh your browser", "it's deployed, take a look" or equivalent — **you** first open the browser via the MCP tool, navigate to the changed surface, and verify that the **visible DOM** actually contains what you changed. Only then hand off to the user.

This maxim is the UI variant of "measure, don't guess". A user-demo without self-verify is the same as a cut-operation without read-back: you're claiming something you haven't measured.

## When to use

Trigger phrases (what you're about to say):
- "Refresh the browser please" / "Reload the page"
- "Take a look at this" / "Test it now"
- "It's deployed" / "The new version is running"
- "Should work now"
- "Hard-reload with Cmd-Shift-R"

Trigger symptoms (especially urgent):
- User already said "nothing changed" → verify NOW, do NOT write another cache theory
- You've made >2 deploy iterations without visible verification
- The view has multiple modes (edit/preview/print, expand/collapse, mobile/desktop) — the user may be looking at the mode you did **not** change
- The UI change was "large" (layout refactor, new component, new CSS scheme) — risk that only one path got updated

## When NOT to use

- Backend-only: API response shape, DB migrations, CLI tools, batch jobs (no rendered surface)
- User explicitly said "just push it, I'll test" — then self-verify is overhead
- Auth-gated UI without test credentials → do a **partial verify** on the public route + document the limit honestly ("public route OK, auth route not checkable from here")
- Pure style tweaks on a localhost dev-server the user has open themselves — they see it immediately

## The 5-Step Self-Verify Flow

### Step 1 — Identify the EXACT surface that should change

Before you open the browser: write down in 1 sentence **what** you expect visually and **where**:
- Route (`/letters/edit/123`)
- Element selector (`[data-testid="letter-preview"]` or CSS selector `.letter-body`)
- Expectation ("should contain `<div class='letter-header'>` with two columns")

If you don't write this down → you'll hallucinate during the browser-check ("looks good") without concretely verifying.

### Step 2 — Navigate

```
mcp__plugin_playwright_playwright__browser_navigate(url="http://your-host:8080/letters/edit/123")
```

or the Chrome-DevTools-MCP equivalent (`navigate_page`).

### Step 3 — Snapshot + Screenshot

```
mcp__plugin_playwright_playwright__browser_snapshot()       # ARIA-tree, leichtgewichtig
mcp__plugin_playwright_playwright__browser_take_screenshot()  # pixel-truth
```

Snapshot shows you the structure (which components are rendered), screenshot shows you what the user **sees**. We need both — snapshot alone misses CSS bugs, screenshot alone misses stale caches in invisible areas.

### Step 4 — Targeted Evaluate

Ask the concrete question from Step 1 to the page:

```
mcp__plugin_playwright_playwright__browser_evaluate(
  function="() => { 
    const el = document.querySelector('.letter-header');
    return {
      found: !!el,
      childCount: el?.children?.length,
      computedColumns: el ? getComputedStyle(el).gridTemplateColumns : null,
      html: el?.outerHTML?.slice(0, 300)
    };
  }"
)
```

Here it gets concrete: if you expect 2 columns, check `gridTemplateColumns` or `display: flex` + `flex-direction`. If you expect a specific text, check `textContent`.

### Step 5 — Discrepancy → STOP, do not hand off to user

If the DOM does not show what's expected:
- ❌ NOT "must be the browser cache, do a hard-reload"
- ❌ NOT "the build-stamp shows the new version, so it should be fine"
- ✅ Bug diagnosis **before** the user-demo: check the build asset (`docker exec frontend ls -la /usr/share/nginx/html/assets/ | head`), check the source code in the container (`docker exec frontend cat /app/dist/...`), or open the correct mode/tab/panel you actually meant.

**Only when self-verify confirms the expectation → hand off to the user.**

## Common Failure Modes (empirical)

| Mode | Symptom | Self-verify catches it because... |
|---|---|---|
| **Edit-vs-Preview-Panel** | Change was in the print-window, editor showed old textarea | snapshot shows only 1 panel; screenshot of edit-mode instead of print |
| **Multi-stage Docker stale dist** | Source-rsync without dist-rebuild, old assets served | `evaluate` of the asset-hash returns a different state than git-HEAD |
| **Cache-Header SPA trap** | `index.html` from browser cache, new assets but wrong manifest | screenshot shows mismatch of layout and content |
| **Wrong selector** | DOM never had the element, you only edited a textarea without rendering | `evaluate` returns `found: false` |
| **Conditional rendering** | Element renders only in one state (an item selected etc.) | screenshot of the default state is empty → you must establish the state |

## Anti-Patterns to AVOID

| Anti-Pattern | What happens | What to do instead |
|---|---|---|
| "Cache-bust" spiral | Hard-reload, incognito, ?v=1 — all without a DOM read | Self-verify Step 3-4. If the DOM is stale, it's a build bug, not cache. |
| Build-stamp as verification | Sidebar shows "Build 14:32" → supposedly new | Build-stamp ≠ layout correctness. Targeted-evaluate on the changed surface. |
| User-reload instruction as a test | "do a hard-reload, tell me what you see" | The user then sees what you would see — with the same bug. Self-verify first. |
| Token-burn theory stack | 5 hypotheses about how the cache might be stale | 1 browser-navigate + 1 evaluate saves 5 theories. |

## Red Flags — STOP and Self-Verify

- You're typing "please refresh the browser" → STOP. Self-verify first.
- User said "nothing changed" a 2nd+ time → STOP. Self-verify first.
- You're explaining why the cache might be the problem → STOP. Self-verify first.
- You're writing a 3rd cache-header variant without checking the effect of the first → STOP. Self-verify first.
- You've done >2 docker-compose rebuilds without a browser test → STOP. Self-verify first.

## Cost of Skipping

- **5+ debug-rounds** for a "cache problem" that was none
- **Build-stamp mechanics** built + incognito-tests + nginx-headers — all unnecessary if the "edit-panel shows old textarea" bug had been caught 5 minutes after deploy via self-verify
- **Trust erosion**: "It's frustrating that I'm burning a hundred euros of tokens here just because you again didn't verify your results the way the rules require."
- **~2h wall-clock**
