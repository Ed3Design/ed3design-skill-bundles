---
name: briefing-source-triangulation
description: |-
  Use when building a status briefing (morning standup, weekly review, "where was ", session-start briefing) that reads from multiple persistence sources (Daily Note + `.remember/today-*.md` + `.remember/recent.md` + git-log + file mtimes). Without conscious source-priority, briefings can claim items as "open" that were actually completed (e.g. email sent, meeting held, file shipped) because secondary sources lag or summarise. Trigger on phrases like "morning briefing", "daily standup", "where was ", "what was still open", "session-start briefing", "weekly review", "monthly close", "what's new since yesterday", "day overview", or any skill invocation that consumes `.remember/today-*.md` or `recent.md` as status input. Do NOT load when only consuming a single source (just reading the Daily Note for context), when writing INTO `. remember/` files (those are plugin-owned, not briefing input), or for code-only context-gathering (use git-log directly)

---

# briefing-source-triangulation
## The source hierarchy

When building any status briefing, sources rank in this priority order:

| Rank | Source | What it is | Trust for "did X happen?" |
|---|---|---|---|
| 1 | **Daily Note** `Daily Notes/YYYY-MM-DD.md` | Human/plugin-curated, intent-driven, structured blocks | High for documented activity. Silent on external acts (sends, calls, meetings). |
| 2 | **Git log** in code-repos | Atomic commits with timestamps | High for code changes. Silent on everything else. |
| 3 | **File mtimes** on new artifacts | Filesystem ground truth | High for "when was this written". Silent on intent. |
| 4 | **User cross-check** for external acts | E-mail sent? Meeting held? Phone call done? | Only the user knows. Ask, don't infer. |
| 5 | `.remember/today-*.md`, `recent.md`, `archive.md` | Plugin-LLM-summarised secondary | Plausibility-check only. Do NOT treat as primary. |

## Why `.remember/` is rank 5 (not rank 1)

The `remember`-plugin writes via post-tool/save-session hooks:
- `## HH:MM | branch` section markers are **plugin-generated** (likely session-start), not user-input times
- Content is **LLM-summarised** (Haiku-cost signature visible in `.remember/logs/memory-YYYY-MM-DD.log`)
- Sessions with **<3 human messages are silently skipped** (look for `human msgs < 3, skip` in the log)
- Cross-day consolidation sessions can legitimately produce yesterday-themed entries under today's HH:MM marker (when the user explicitly asks for a "wrap up the open session" pass)

None of these are bugs. They are design choices that mean `.remember/today-*.md` cannot be the ground-truth source for "what happened today".

## The triangulation procedure

Before writing any briefing:

1. **Read the Daily Note first.** Skim blocks. This is the canonical chronicle.
2. **Check git log** for repos relevant to the briefing scope: `git log --since="midnight" --pretty=format:"%h %ai %s"`.
3. **For external acts** the Daily Note mentions as "ready" / "ready to send" / "pending review" / "prepared" → **ask the user** whether they completed it. Status verbs like "ready to send" are claims of preparedness, not completion.
4. **Use `.remember/today-*.md` only as plausibility check.** If something there contradicts the Daily Note, trust the Daily Note. If something appears under an HH:MM marker, don't assume the user typed at that time.
5. **Build the briefing.** Carry-Over items inherit the source rank — if the only evidence for "X is open" comes from rank 5, mark it as "appears open, confirm with user".

## The lesson (self-correction)

- Daily Note said "ZIP ready to send" (rank 1, but a preparedness verb)
- `.remember/today-*.md` had a stale block (rank 5)
- No source said "email actually sent"
- The briefing claimed "email send still open" → wrong, the email had been sent hours earlier
- User had to correct it

**The miss:** the briefing should have asked the user "did the send happen?" instead of inferring "ready to send = still pending". The fix is operational: any Carry-Over claim about an external act gets a user-cross-check before it appears in the briefing.

## When to promote out of STUB

- Codify a question template for external acts ("Did you send/meet/deploy X? When?")
- Add a callable triangulation helper that emits a diff between Daily Note claims and `.remember/today-*.md` summaries
- Add a briefing self-audit checklist (every claim has a source rank annotation)
- Then rename to drop `-DRAFT` and add to GA registry
