---
name: ephemeral-container-file-detection
description: NOT YET TDD-TESTED. Do not auto-trigger. Use when designing or auditing Docker-based deployments BEFORE writing implementation plans that rely on files persisting across container rebuilds. Trigger on phrases like "Volume-Mount für X", "warum sind die Files weg", "Container-Rebuild hat Models gelöscht", "model_path zeigt auf File die nicht da ist", "Phantom-Registry in DB", "Inference schlägt mit FileNotFoundError", "bevor wir bauen — sind die Voraussetzungen da", "Pre-Flight Deployment-Audit", "writing-plans für Docker-Feature mit persistenten Daten". Detection-Pattern in 4 Schritten: docker inspect Mounts → ls Container-Dir → stat Birth-Time → grep dump/save-Calls im Code → wenn Code schreibt aber Mount-Liste den Pfad NICHT enthält → ephemeral, Pre-Flight-STOP für die Feature-Phase. Do NOT load for non-Docker-Deployments (systemd-services, Kubernetes-StatefulSets — anderes Modell), für read-only Container ohne Write-Pfade, für Single-File-Apps ohne Storage-Layer. Wolf-Maxime „erst Logs/Code/DB lesen" auf Deployment-Voraussetzungen angewendet.
---

# ephemeral-container-file-detection

> ⚠️ **DRAFT-STATUS**: Skill aus 28.05.2026 Pre-Flight-Forensik-Session entstanden (vor Phase-X.0-Plan für ultimative-platform). Pattern hat ~6h Wasted-Plan-Work verhindert. Promotion via `skill-tdd-promotion-workflow` mit RED+GREEN-Subagent-Test in nächster Skill-Building-Session.

## Pattern (Kurzform)

Vor jedem Implementation-Plan für ein Docker-basiertes Feature das **persistent state** voraussetzt (ML-Models, Caches, Upload-Files, User-Daten, getrainierte Embeddings, etc.):

### 4-Schritte-Check

1. **Docker-Inspect Mounts**:
   ```bash
   docker inspect <container_name> | grep -A 3 -E 'Mounts|Source|Destination'
   ```
   Listet alle bind-mounts + named-volumes auf.

2. **Container-Dir-Realität**:
   ```bash
   docker exec <container_name> ls -la <expected_path>/
   ```
   Was ist *tatsächlich* in dem Verzeichnis im laufenden Container?

3. **Stat Birth-Time des Container-Verzeichnisses**:
   ```bash
   docker exec <container_name> stat <expected_path>/
   ```
   `Birth:` zeigt wann das Verzeichnis im Container erstellt wurde. Wenn Birth ≈ letzter Container-Build-Zeit → ephemerer Image-Layer (nicht persistent).

4. **Code-Grep nach Save-Calls**:
   ```bash
   grep -rn "joblib.dump\|to_csv\|save_model\|pickle.dump\|open.*'w'\|aiofiles.open" --include="*.py" <code_root> | grep -i <expected_path-Substring>
   ```
   Findet Stellen wo Code in den erwarteten Pfad schreibt.

### Diagnose-Tabelle

| Schritt 1 (Mount?) | Schritt 4 (Code schreibt?) | Verdict |
|---|---|---|
| ✅ Mount existiert | ✅ Code schreibt | OK — persistent storage funktioniert |
| ❌ Kein Mount | ❌ Code schreibt nicht | OK — nur read-only Container-Layer-Files |
| ❌ Kein Mount | ✅ Code schreibt | 🚨 **EPHEMERAL** — Files gehen bei jedem `up --build` weg |
| ✅ Mount existiert | ❌ Code schreibt nicht | OK aber: Mount evtl. obsolet (Cleanup-Kandidat) |

Das 🚨-Pattern ist der **Pre-Flight-Stop-Trigger** für die Feature-Phase.

## Konkretes Beispiel (heutige Live-Begegnung 28.05.2026)

**Aufgabe**: Implementation-Plan für ultimative-platform Phase X.0 (ML-Evaluator) schreiben.

**Pre-Flight-Discovery**:
- Schritt 1: `docker inspect ultimative-trader | grep Mounts` → nur `/srv/data/ultimative-platform/logs:/app/logs`, KEIN `/app/ml/models`-Mount
- Schritt 2: `docker exec ultimative-trader ls /app/ml/models/` → nur `model_TEST_DE.pkl` + `.gitkeep` (1 File von 40 erwarteten)
- Schritt 3: `stat /app/ml/models/` → Birth: 2026-05-27 14:13:35 UTC (gestriger Container-Rebuild für Phase-2e-Deploy)
- Schritt 4: `grep -rn "joblib.dump" --include="*.py" ml/` → `ml/ranking_model.py:153: joblib.dump(self, path)`

**Diagnose**: Code schreibt nach `/app/ml/models/`, aber Pfad ist NICHT gemountet → **ephemeral**. 40 `ml_models`-DB-Einträge sind Phantom-Registry seit dem letzten Rebuild.

**Konsequenz**: Phase-X.0-Plan wurde NICHT geschrieben. Stattdessen Phase W als Vor-Phase eingefügt (Volume-Mount + Re-Training + Verify). ~4-6h Wasted-Plan-Work verhindert.

## Quick-Reference: wann diesen Check ausführen?

| Situation | Check ausführen? |
|---|---|
| Implementation-Plan für Docker-Feature mit `joblib.load`/`pickle.load`/`load_model` | ✅ JA, vor Plan-Schreiben |
| Implementation-Plan für Caching-/Upload-/User-Storage-Feature | ✅ JA, vor Plan-Schreiben |
| User-Bug-Report „Files sind weg nach Deploy" / „Inference schlägt mit FileNotFoundError" | ✅ JA, als Diagnose-Block |
| Database-Migration in Container (DB-Daten in Volume) | ⚠ Meist OK weil Postgres-Volume Standard, aber verifizieren |
| Read-Only-Container (z.B. statische API ohne State) | ❌ Nein |
| systemd-Service-Deployment (kein Docker) | ❌ Nein (andere Storage-Semantik) |
| Kubernetes-StatefulSet | ⚠ Nicht dieses Skill — Kubernetes-PVC-Pattern ist anders |

## Anti-Patterns

| Anti-Pattern | Korrekt |
|---|---|
| Plan schreiben ohne Pre-Flight, dann am Task 0 stoppen | Pre-Flight VOR `writing-plans` ausführen |
| `docker inspect` ignorieren, sich auf compose.yml-Source-Lesen verlassen | compose.yml und docker-inspect können divergieren (running container könnte alte Version sein) — beides checken |
| Ephemeral-Befund als „auch okay" akzeptieren weil „läuft ja gerade" | Nächster Rebuild wischt aus. Strukturelles Problem, nicht Symptom |
| Nur Container-Sicht prüfen, Host-Sicht vergessen | Bei bind-mount auch `ls /host/pfad/` prüfen — bidirektionale Visibility ist Bestätigung |
| `du -sh` zur Verify benutzen statt File-Counts | `du` sagt Größe, nicht Anzahl. Anzahl ist die relevante Metrik für „Files persistent" |
| Pre-Flight nur für ML-Files, nicht für Caches/Sessions/Uploads | Pattern gilt für JEDES Write-Pfad-Pattern, nicht nur ML |

## Pre-Flight als Pre-Step zu superpowers:writing-plans

Wenn dieses Skill für Plan-Schreiben aktiviert wird, gehört der 4-Schritte-Check **als allererster Task in den Plan ODER vor das Plan-Schreiben**:

**Variante A — Pre-Flight VOR Plan-Schreiben** (empfohlen wenn Voraussetzungen unklar):
- Discovery zuerst, Plan dann angepasst-auf-Befund
- Heute am 28.05. so gemacht: Phase W eingefügt statt Phase X.0 direkt zu planen

**Variante B — Pre-Flight als Task 0 IM Plan** (wenn Voraussetzungen vermutet-OK aber zu verifizieren):
- Plan enthält explizit „Task 0: Pre-Flight Storage-Audit" mit den 4 Steps
- Wenn Task 0 fails → Plan-Stop, Re-Design notwendig
- Geeignet für eher-routine-Deployments mit Standard-Pattern

## TDD-Aufgabe für nächste Skill-Building-Session

**RED-Test**: Subagent ohne Skill bekommt Task: „Schreibe Implementation-Plan für Phase X.0 (ML-Evaluator) für ultimative-platform. Repo unter `~/Documents/Claude-Code/ultimative-platform/`, Spec unter `docs/superpowers/specs/2026-05-28-ml-evaluator-shadow-roadmap-design.md`." Erwartung: Subagent schreibt Plan mit Task 0 = „File-Existence-Check" naiv (nur `Path.exists()`), erkennt NICHT dass `/app/ml/models/` ephemerer Container-Layer ist. Würde Phase-X.0-Plan ausführen wollen → an Pre-Flight stoppen.

**GREEN-Test**: Subagent mit Skill bekommt identisches Prompt. Erwartung: Subagent führt 4-Schritte-Check aus, entdeckt ephemeral-storage-Pattern, schlägt Pre-Flight-Pause oder Phase-W-Insertion vor.

**Refactor-Hinweis**: wenn GREEN-Subagent das Pattern korrekt anwendet aber den 4-Schritte-Check zu langwierig macht (z.B. 4 SSH-Calls statt 1 chained), kann das Skill um eine „kompakte 1-Command-Variante" erweitert werden:
```bash
ssh <host> "docker inspect <container> | grep -A 3 Mounts && docker exec <container> ls -la <path>/ && docker exec <container> stat <path>/"
```

## Querverweise

- `superpowers:writing-plans` — Skill predigt „assume engineer has zero context", aber Pre-Flight für Storage-Voraussetzungen war bisher nicht explizit
- `superpowers:brainstorming` — sagt „Explore project context first" allgemein; dieses Skill ist die Docker-Storage-Spezialisierung
- Wolf-Maxime „erst Logs/Code/DB lesen, dann Hypothese" — auf Deployment-Voraussetzungen erweitert
- `timescaledb-compression-workflow` Skill — verwandtes Pattern: Discovery-vor-Hypothese im Storage-Bereich
- `pre-migration-data-verification` — verwandt: vor Constraint-Add Daten verifizieren; hier vor Feature-Plan Storage verifizieren

## Real-World-Impact (heute, 28.05.2026)

ultimative-platform Phase-X-Brainstorming-Session:
- **Spec** für Phase X.0 (ML-Evaluator) geschrieben mit Schwellen, Filter, Eval-Report-Struktur
- **Vor Plan-Schreiben** Pre-Flight-Discovery ausgeführt (dieses Pattern, informell)
- **Befund**: 40 ml_models-DB-Einträge zeigen auf `/app/ml/models/*.pkl`, im Container nur `model_TEST_DE.pkl` (1 File), kein Volume-Mount → ephemeral
- **Konsequenz**: Phase W (Volume-Mount + Re-Training + Verify) als neue Vor-Phase, dann erst Phase X.0
- **Zeit-Ersparnis**: ~4-6h Plan-Schreiben + Plan-Ausführen + Plan-Abbruch durch frühen Stop verhindert
- **Strukturelle Erkenntnis**: G1-Befund „v3 konsumiert keine ml_models" hatte eine tiefere Ebene — selbst wenn v3 konsumieren würde, gäbe es nichts zu konsumieren (FileNotFoundError). Deployment-Design-Bug, nicht Konzept-Lücke

## Notes für Skill-Reviewer (nächste Session)

- Falls Skill TDD stark besteht: kann projekt-übergreifend Standard werden als Pre-Step zu `superpowers:writing-plans` für Docker-Features
- Falls TDD scheitert: möglicherweise reicht eine Erweiterung der Wolf-Maxime „erst Logs/Code/DB lesen" um Storage-Verifikation — eigenes Skill wäre Overkill
- Variante zu evaluieren: gilt das Pattern auch für Container-Runtime-State (in-memory caches, session-stores)? Vermutlich anderes Pattern (Restart-Persistenz vs. Rebuild-Persistenz)
