---
name: brain-dump-to-phased-roadmap
description: |-
  Use when the user presents a loose collection of items (a brain-dump, an inbox-list, a "I want to do all of these" list, scattered TODOs) and wants help turning it into an actionable plan — phases with dependencies, entry triggers, and confirmation questions on each meaningful design decision. Trigger on phrases like "I have a few things here", "clean up the brain-dump", "how do I tackle all this", "roadmap from these items", "consolidate the inbox", "I don't know where to start", "make me a plan out of this", "consolidate this list into a plan", "turn this dump into a roadmap". Do NOT load when the user already has a phase plan and wants to execute it (use gsd:gsd-execute-phase), when there is a single concrete task (just do it), or for design exploration where the items are not yet committed work (use design-first-iteration). Complements gsd:gsd-new-milestone and gsd:gsd-plan-phase — this skill bridges the gap *before* either of those, when items are still unstructured and clusters are not yet visible.

---

# Brain-Dump to Phased Roadmap

A brain-dump is what happens when the user has been collecting "I should do this" items in their head (or on a paper note, or in an `Inbox/` folder) and finally types them out. They look like a TODO list, but they're not — they have hidden dependencies, hidden clusters, and hidden conflicts. Treating them as a flat list and asking "which one first?" forces the user to do the structuring work themselves.

This skill is the opposite: **find the cluster, surface the dependencies, propose phases with entry triggers, then confirm the design decisions one by one**. Empirically validated by turning 6 loose infrastructure items into a 3-phase Alpha/Beta/Gamma roadmap with all 5 open design decisions resolved in a single confirmation round.

## When to use

- User pastes/lists 4-12 items they want to address
- Items span multiple themes (some networking, some hardware, some software, some admin) but are not yet grouped
- User says "I don't know where to start" or "how do I sequence this"
- There's an `Inbox/`-style accumulation that needs sorting
- A weekly/monthly planning moment where loose ambitions need to become a plan

## When NOT to use

- A single concrete task → just do it, no planning overhead
- Items already have phases/priorities assigned → use `gsd:gsd-execute-phase`
- Items are still ideation, not commitments → use `design-first-iteration`
- The user wants to brainstorm new items, not structure existing ones → use `superpowers:brainstorming`

## The four-step workflow

### Step 1: Capture all items verbatim

List every item exactly as the user wrote/spoke it, numbered. Don't paraphrase, don't combine yet. Numbering anchors the items so the user can reference them by number in conversation.

```
1. Set up your-server as Tailscale subnet router
2. Resolve Tailscale connectivity issues (see daily note)
3. Obsidian sync setup for iPhone
4. Modernize project-hub.md
5. Finish device manual
6. Order fan for your-server (passive maintenance)
```

### Step 2: Find the cluster (the "aha" moment)

Read the items again and ask: **what are they really about?** Often 60-80% of the items share a hidden theme.

Example:
> 4 of 6 items are "Mac↔your-server connectivity" themes (#1 subnet router, #2 Tailscale diagnosis, #3 Obsidian sync via iPhone needs Tailscale, #4 project-hub modernization touches your-server dashboards). As a cluster they describe **one architectural shift: your-server evolving from data-server to home-network gateway.**

This re-framing is the single highest-leverage move in the whole workflow. It transforms 4 loose tasks into one strategic shift with sub-steps. Surface it explicitly: **"I see a pattern — items #X, #Y, #Z, #W are really all about <theme>. Does that match how you think about them?"**

### Step 3: Map dependencies → propose phases

Each item gets a dependency-check: what needs to be true before this can start?

| # | Item | Depends on |
|---|---|---|
| 1 | Subnet router | #2 (Tailscale must be healthy) |
| 2 | Tailscale diagnosis | nothing (entry point) |
| 3 | Obsidian sync | #1 (subnet-router for iPhone VPN) |
| 4 | Modernize project-hub | #1 (your-server dashboards reachable) |
| 5 | Device manual | nothing |
| 6 | Order fan | nothing |

Now phases fall out naturally:

| Phase | Character | Items | Entry-Trigger |
|---|---|---|---|
| **Alpha** | quick wins + unblocker | #2 Tailscale diagnosis, #5 manual, #6 fan order | none — start now |
| **Beta** | architectural shift | #1 subnet router | Alpha #2 done |
| **Gamma** | new capabilities on the new foundation | #3 Obsidian sync, #4 project-hub | Beta done |

Name the phases with **character** (not just "Phase 1/2/3"). "Quick wins + unblocker", "architectural shift", "new capabilities" tells the user what kind of energy each phase needs.

Each phase gets an **entry-trigger** — a concrete condition that signals "OK, this phase can start now". Without entry-triggers, phases blur into each other and the user re-asks "should I start Beta now?" three times.

### Step 4: Surface the design decisions, confirm in one round

Each phase has hidden design decisions. Surface every one explicitly and ask the user — **don't decide for them**. Format as a numbered list of decisions, each with 2-4 options and a recommendation.

Example (5 decisions surfaced together):

```
1. Phase order: Alpha → Beta → Gamma (vs parallel) — Recommendation: sequential
2. Obsidian sync: A) Obsidian Sync ($8/mo), B) self-hosted CouchDB, C) Syncthing — Recommendation: A (plug-and-play)
3. Audio inbox STT: A) Whisper API, B) Whisper.cpp local, C) later — Recommendation: B (local capability vs cloud pay-per-use)
4. Fan delivery time: confirm "next week" holds
5. Brand name for public repos: clarification required
```

The user goes through them in one pass, confirming or correcting. Decisions get logged in the roadmap doc so future sessions don't re-litigate them.

### Step 5: Tidy up the brain-dump

After the roadmap exists, the original brain-dump should not just be deleted — it should be **migrated**, with a trail. Convention: a `_Recently moved items_` section at the bottom of the `Inbox/` (or wherever the dump lived) that lists each item and where it went:

```markdown
## _Recently moved items_

The following 6 items have been structured into [[Roadmap — Infrastructure]]
(Phases Alpha/Beta/Gamma):

1. → Alpha A1
2. → Alpha A2
3. → Gamma C1
4. → Gamma C2
5. → Alpha A3
6. → Alpha A4
```

This trail prevents items from "disappearing" (a frequent inbox-anxiety) and gives the user confidence to clear the brain-dump.

## Anti-patterns

- ❌ **Treating the dump as a flat priority-list**: "which one should I do first?" — that's the wrong question; the right question is "what's the structure?"
- ❌ **Combining items before listing them verbatim**: kills the user's ability to reference items by number, and may merge things that look similar but aren't
- ❌ **Inventing phases without entry-triggers**: phases without triggers blur into each other; the user re-asks "is Beta ready?" repeatedly
- ❌ **Deciding the design questions for the user**: ask, don't assume. The recommendation goes in the question; the choice stays with the user.
- ❌ **Asking decisions one by one in sequence**: surface ALL of them in one round so the user can see the full picture. One round of 5 decisions is faster and clearer than 5 rounds of 1.
- ❌ **Letting the original dump sit untouched after the roadmap exists**: dump+roadmap=ambiguity ("which one is the source of truth?"). Always migrate the dump with a trail.

## Quick template

Use this skeleton to scaffold the roadmap document:

```markdown
# Roadmap <Topic> <Date>

> Consolidated from brain-dump <date>: <N> items → <M> phases.

## Cluster insight
<The "aha" — what is this really about?>

## Phase Alpha — <character>
- **Entry trigger**: <condition>
- **Items**: A1 <item>, A2 <item>, A3 <item>
- **Expected effort**: <duration estimate>

## Phase Beta — <character>
- **Entry trigger**: Alpha <which slots> done
- ...

## Design decisions
1. ✅ <decision> — <choice>
2. ✅ <decision> — <choice>
...

## Migrated items
- Item 1 → Phase Alpha A1
- Item 2 → Phase Alpha A2
- ...
```

## Real-world impact

- 6 loose brain-dump items → 3-phase roadmap (Alpha/Beta/Gamma) in ~20 min conversation
- Cluster insight ("4 of 6 are connectivity") re-framed the work from "to-do list" to "architectural shift"
- All 5 design decisions confirmed in one round (vs. 5 separate sessions to ask one at a time)
- Brain-dump cleared with migration-trail; zero items lost
- Roadmap stored as living source-of-truth (with Current-Truth + Timeline split)
- Phase Alpha A1+A2+A3 completed within ~24h of roadmap creation
