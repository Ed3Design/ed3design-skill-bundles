---
name: domain-rules-anti-patterns-first
description: Use when modeling a domain that has formal legal/regulatory rules — Renten/Pension, Steuer/Tax, Versicherungen, Arbeitsrecht, Erbrecht, Sozialrecht, Gesundheitsrecht, ALG/Sozialleistungen, Vertragsrecht, BGB, EStG, SGB, etc. Trigger on phrases like "Rente berechnen", "Steuer modellieren", "Versicherungsbeitrag", "Anspruch auf X", "Wartezeit", "Bemessungsgrundlage", "Renteneintritt", "Abschlag", "Erbschaft", "Schenkungssteuer", "Arbeitslosengeld", "Altersrente", "Hinterbliebenenrente", "ALG-Sperrzeit", "Fünftelregelung", "Progressionsvorbehalt", "Anlage V Steuer", "Werbungskosten", "Sonderausgaben", "Freibetrag", "Bemessungsgrenze". Do NOT load for general programming domain modeling (database schemas, API contracts), for pure math/physics modeling (no legal/regulatory aspect), or for project-internal business logic where Wolf is the rule-author. This skill encodes the Wolf-Claude experience pattern from absprung-app (24.05.2026): when Claude models a legal domain, it knows the POSITIVE rules from training but consistently misses the SPERR-KLAUSELN (anti-patterns, exceptions, traps). Result: 3+ Wolf-corrections in one session. Discipline: actively ask about the traps BEFORE coding the positive rules.
---

# Domain-Rules Anti-Patterns First

When modeling a legal/regulatory domain (Renten, Steuer, Versicherungen, Sozialrecht etc.), Claude knows the positive anspruchs-/berechnungs-/leistungs-Regeln reasonably well from training data. But the **Sperr-Klauseln** (Anti-Patterns, exceptions, traps, Mindestvoraussetzungen) — these are the rules where Claude is most likely to model incorrectly. They're often spread across multiple paragraphs of a Gesetz, depend on specific personal constellations, and aren't part of typical "summary" content.

This skill exists because in a single Renten-App-Session on 24.05.2026, Wolf had to correct three different Anti-Patterns that Claude initially missed:

1. **§51 Abs 3a SGB VI** — ALG-Zeit zählt NICHT zur 45-Jahre-Wartezeit für „besonders langjährig Versicherte" (Sperre gegen Last-Minute-ALG-Antrag)
2. **§166 SGB VI** — ALG erwirbt sehr wohl Entgeltpunkte (Claude hatte das als „vernachlässigbar" modelliert)
3. **§34 Abs 1 EStG** — Fünftelregelung bei Abfindung mit Günstigerprüfung (Claude hätte sie als reine Steuer-Vergünstigung modelliert)

Plus methodisch verwandt aus früheren Sessions: Brand-Foundation-Origin-Frage (Ed = Hund, nicht Initial); Multi-Choice-vs-offene-Frage-Stil.

## When to use

- Modeling Renten-/Pension-Berechnung (Entgeltpunkte, Wartezeiten, Abschläge, Hochwertungs-Faktor, Besteuerungsanteil)
- Modeling Einkommensteuer (Tarifformeln, Freibeträge, Sonderausgaben, Werbungskosten, außerordentliche Einkünfte)
- Modeling Versicherungsbeiträge / Sozialversicherungen (KV/PV/RV/AV)
- Modeling Erbschafts-/Schenkungssteuer, Freibeträge, Steuerklassen
- Modeling Vertragsrechtliche Konstrukte mit gesetzlichen Constraints
- Any "Lebensentscheidungs"-App wo eine falsche Rechnung dem User echtes Geld kostet

## When NOT to use

- Generic programming domains (database design, API contracts, file formats) — keine Anti-Patterns im Rechts-Sinne
- Pure math/physics modeling (Statik, Wärmeleitung, Schaltungen) — Naturgesetze ohne Sperr-Klauseln
- Wolf-internal business logic where Wolf IS the rule-author — er kennt die Trap selbst
- Quick prototypes wo Genauigkeit nicht zählt — die Skill-Disziplin verlangsamt sinnvolle Iteration

## Iron rule

**Bevor du eine positive Rechen-Regel implementierst, frage explizit nach Sperr-Klauseln + Anti-Patterns + Mindestvoraussetzungen.**

Konkrete Frage an Wolf:

> Bevor ich diese [Renten/Steuer/Versicherungs]-Berechnung implementiere — kennst du Sperr-Klauseln oder Sonderregeln die ich beachten muss? Speziell:
>
> 1. Welche Voraussetzungen müssen erfüllt sein (Wartezeiten, Beitragsjahre, Alter, Beziehungs-Status)?
> 2. Gibt es Sperren die typischerweise „kurz vor Ziel" greifen (Last-Minute-Strategien blockieren)?
> 3. Welche Sonderregeln gelten für Sonderfälle (Sonderversorgung, Ost/West-Hochwertung, Schwerbehinderung etc.)?
> 4. Gibt es eine „Günstigerprüfung" oder Wahlrecht zwischen mehreren Verfahren?

Wolf kennt das aus eigener DRV-Renteninformation, Steuerbescheiden, Verträgen mit Steuerberater oder selbst-rechercheirt — er hat das relevante Domain-Wissen das die positive Berechnung allein nicht abbildet.

## Domain-spezifische Cheat-Sheets — typische Anti-Patterns

### Renten (SGB VI) — typische Sperren

| Sperre | Paragraph | Wirkung |
|---|---|---|
| 45-Jahre-Wartezeit für besonders langjährig Versicherte | §51 Abs 3a SGB VI | ALG-Zeit zählt NICHT mit (max die letzten 2 Jahre vor Rente) |
| Vorgezogene Altersrente langjährig Versicherte | §236 SGB VI | Abschlag 0,3 % pro Monat vor Regelaltersgrenze (max 14,4 %) |
| Hinausschieben über Regelaltersgrenze | §77 SGB VI | Zuschlag 0,5 % pro Monat (max nicht begrenzt) |
| Versorgungsausgleich | §76 SGB VI | EP-Übertragung bei Scheidung, dauerhaft (kein „Rückgängig" wenn Ex-Partner stirbt vor Rente) |
| Ost/West-Hochwertung | §256a SGB VI | Reduziert sich kontinuierlich, 2025 = 1,0 (Angleichung erreicht) |
| ALG erwirbt EP | §166 SGB VI Abs 1a | 80% × BBG / Durchschnittsentgelt ≈ 1,5 EP/J. |
| Hinzuverdienstgrenze (vorgezogene Rente) | §34 SGB VI | seit 2023 vollständig entfallen |

### Steuer (EStG) — typische Sperren / Wahlrechte

| Anti-Pattern | Paragraph | Wirkung |
|---|---|---|
| Fünftelregelung Abfindung | §34 Abs 1 EStG | Günstigerprüfung gegen Regelversteuerung — bei hohem zvE oft kein Vorteil |
| Progressionsvorbehalt | §32b EStG | Steuerfreie Einkünfte (ALG, Kindergeld, Auslandseinkünfte) erhöhen Steuersatz auf andere Einkünfte |
| Verlustverrechnungsbeschränkung Kapitalvermögen | §20 Abs 6 EStG | Aktien-Verluste nur gegen Aktien-Gewinne |
| Spekulationsfrist Privat | §23 EStG | 1 Jahr für Wertpapiere (entfallen für Aktien seit 2009), 10 Jahre für Immobilien |
| Werbungskosten V&V | §9 EStG | AfA 2% (Gebäude), Erhaltungsaufwand sofort, Anschaffungs-/Herstellungs-Aufwand über AfA |
| Besteuerungsanteil Rente | §22 Nr. 1 EStG | Stufenweise Anhebung, 100% ab Rentenbeginn 2058 |
| Splittingtarif | §32a Abs 5 EStG | Nur bei Eheleuten, Zusammenveranlagung |

### Sozialversicherung — typische Sperren

| Sperre | Wirkung |
|---|---|
| ALG-Sperrzeit | 12 Wochen bei Eigenkündigung ohne wichtigen Grund (kann durch Aufhebungsvertrag vermieden werden, aber Risiko-Klauseln in Vereinbarung) |
| Abfindung-Sperrzeit | wenn Abfindung über bestimmten Grenzen → ALG-Anspruch um Monate verzögert |
| BBG / Versicherungspflichtgrenze | jährlich angepasst, beeinflusst KV-PV-RV-AV-Beiträge |
| Beitragsbemessungsgrundlage ALG | 80% des Bemessungsentgelts (BBG-gekappt) |

## Workflow

### Phase 1: Domain-Identifikation
- Welche Rechtsbereiche sind betroffen? (z.B. Renten = SGB VI, Steuer = EStG, ALG = SGB III)
- Welche Person-spezifischen Constellation sind relevant? (Jahrgang, Versicherten-Status, Beitragsbiografie, Familienstand)

### Phase 2: Anti-Pattern-Catalog
- Lade das passende Cheat-Sheet oben (oder erweitere es)
- Frage Wolf explizit nach Sperren die in seiner spezifischen Konstellation greifen
- Dokumentiere im Code-Kommentar UND im Vault-Spec: welche Sperre WIE modelliert ist

### Phase 3: Positive Regeln (jetzt erst)
- Implementiere die Berechnungs-Formeln
- Validiere gegen Wolfs Sheet / Renteninformation / Steuerbescheid (Kontrollrechnung)

### Phase 4: Transparenz
- UI muss zeigen welche Sperren gegriffen haben (z.B. „7,2 % Abschlag wegen 45-J.-Sperre" statt nur „Brutto-Rente XYZ")
- Nicht-erfüllte Anspruchsvoraussetzungen explizit anzeigen

## Anti-patterns

- ❌ **Nur die positiven Anspruchs-Bedingungen aus Wikipedia/Training modellieren** — du wirst die spezifischen Sperren übersehen
- ❌ **"Vernachlässigbar"-Annahmen ohne Wolf-Bestätigung** — z.B. „ALG erwirbt keine EP" war falsch
- ❌ **Pauschal-Steuersatz statt echtem Tarif** — Pauschal ist OK für schnelle Schätzung, aber Wolf braucht für Entscheidungs-Apps die echte §32a-Formel
- ❌ **Annahme: alle Sondervorschriften sind in Standard-Berechnung enthalten** — z.B. Versorgungsausgleich, Sonderversorgung NVA, Ost/West-Hochwertung
- ❌ **Modellierung ohne Verweis auf Paragraph** — Code-Kommentar sollte den §-Stichwort enthalten damit künftige Iteration die Regel wiederfindet
- ❌ **Reine Berechnung ohne Anspruchs-Voraussetzungs-Prüfung** — User soll sehen warum welche Variante welche Konditionen hat

## Real-world impact

- **24.05.2026 Absprung-App-Session**: 3 substantielle Wolf-Korrekturen wegen fehlender Sperren-Berücksichtigung. Plan B-A war erst „abschlagsfrei" modelliert (FALSCH), dann mit 7,2 % Abschlag korrekt (Wolf zeigte §51 Abs 3a). Plan B-A → Plan B-B Differenz wurde von 10k Lifetime auf 170k Lifetime korrigiert. Ohne diese Korrektur hätte Wolf eine falsche Verhandlungs-Strategie aufgebaut.
- **Verwandte Patterns aus früheren Sessions**: Brand-Foundation-Origin-Frage (gestern: Ed = Hund, nicht Initial); Multi-Choice-vs-offene-Frage (gestern: Wolf-Stil bevorzugt offen).
- **Lehre**: bei Domain-Modellierung ist die `Frag-erst-die-Sperren`-Disziplin der Hebel gegen 3-4 Wolf-Korrekturen pro Session.
