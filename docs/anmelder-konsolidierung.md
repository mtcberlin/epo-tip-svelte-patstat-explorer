# Anmelder-Konsolidierung in PATSTAT Explorer

**Zielgruppe:** PATSTAT-Analyst:innen / Patent-Domänenexpert:innen
**Zweck:** Diese Doku erklärt die Methodik hinter der „Applicant Search" und der
Anmelder-Konsolidierung — was sie tut, *warum* sie es so tut, und welche SQL-Abfragen
dabei tatsächlich gegen PATSTAT laufen. Sie ist als Schulungsunterlage gedacht.

---

## 1. Das Problem: PATSTAT kennt keine Firmen, nur Namen

PATSTAT führt **keine Entity-Resolution** durch. Eine einzige Organisation taucht in der
Tabelle `tls206_person` als viele unterschiedliche Datensätze auf — pro Schreibweise,
pro Land, pro Tochtergesellschaft, pro Tippfehler ein eigener `person_id`.

Beispiel „Siemens Healthineers" (Stand Trainingsbeispiel, 21 Treffer):

| person_name | Land | Familien |
|---|---|---|
| Siemens Healthineers AG | DE | 1.017 |
| SIEMENS HEALTHINEERS AG | DE | 579 |
| Siemens Healthineers International AG | CH | 192 |
| SIEMENS HEALTHINEERS INTERNATIONAL AG | CH | 53 |
| SIEMENS HEALTHINEERS INTERNATIONAL AG | US | 18 |
| Siemens Healthineers Endovascular Robotics, Inc. | US | 15 |
| SIEMENS HEALTHINEERS NEDERLAND B.V. | NL | 13 |
| … | … | … |

Wer nur **einen** dieser Namen abfragt, unterschätzt das Portfolio dramatisch. Wer alle
Treffer eines Suchworts naiv zusammenwirft, vermischt eventuell fremde Firmen oder
Tochtergesellschaften. Die **Anmelder-Konsolidierung** ist der kontrollierte Mittelweg:
breit suchen → bewusst gruppieren → konsolidiert auswerten.

---

## 2. Die drei Tabellen, die alles tragen

Die gesamte Methodik beruht auf einem Drei-Tabellen-Join:

```
tls206_person          tls207_pers_appln              tls201_appln
(wer)                  (welche Rolle, welche Anm.)    (die Anmeldung)
─────────────          ─────────────────────────      ──────────────
person_id        ───►  person_id                      
person_name            appln_id              ───►     appln_id
person_ctry_code       applt_seq_nr  (Anmelder >0)    docdb_family_id
                       invt_seq_nr   (Erfinder >0)    appln_filing_year
                                                      appln_auth
```

- **`tls206_person`** — die Namen und Ländercodes. Hier sitzen die Varianten.
- **`tls207_pers_appln`** — die Verknüpfungstabelle Person↔Anmeldung. Das Feld
  `applt_seq_nr > 0` bedeutet **Anmelder-Rolle** (Applicant). `invt_seq_nr > 0` wäre die
  Erfinder-Rolle. Wir filtern überall auf `applt_seq_nr > 0`.
- **`tls201_appln`** — die Anmeldung selbst: Familien-ID, Anmeldejahr, Anmeldebehörde.

### Warum immer `COUNT(DISTINCT docdb_family_id)`?

Dieselbe Erfindung wird oft in mehreren Ländern angemeldet (DE, US, CN, EP, WO …). Alle
diese Anmeldungen teilen sich **eine** `docdb_family_id` (DOCDB-Patentfamilie). Würden wir
Anmeldungen zählen, würde ein international breit angemeldetes Patent das Ergebnis
aufblähen. **Die Patentfamilie ist die korrekte Zähleinheit für „wie viele Erfindungen".**
Deshalb steht in *jeder* Query der Pipeline `COUNT(DISTINCT a.docdb_family_id)`.

---

## 3. Der Workflow in drei Stufen

```
 Stufe 1            Stufe 1.5             Stufe 2 (optional)     Stufe 3
 ────────           ─────────             ──────────────────     ───────
 Varianten          Gruppieren            Trend-Vorschau         Konsolidierte
 finden        ──►  (Auto/Manuell)   ──►  (Sanity-Check)    ──►  Tiefenanalyse
 (LIKE-Prefix)      (Mensch entscheidet)  (1 Chart)              (Trend/Jurisd./CPC)
```

Alle Abfragen laufen über denselben Pfad:
`Browser → POST /api/query → SvelteKit-Validierung → sidecar.py → PATSTAT BigQuery (PROD)`.

---

### Stufe 1 — Varianten-Entdeckung

Du gibst ein Suchwort ein (z.B. `Siemens Healthineers`) und optional einen
Anmeldejahr-Bereich. Daraus entsteht **eine** Query, die alle Namensvarianten mitsamt
ihrer Familienzahl auflistet:

```sql
SELECT p.person_name AS name,
       p.person_ctry_code AS country,
       COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls206_person p
JOIN tls207_pers_appln pa ON p.person_id = pa.person_id
JOIN tls201_appln a ON pa.appln_id = a.appln_id
WHERE pa.applt_seq_nr > 0
    AND UPPER(p.person_name) LIKE 'SIEMENS HEALTHINEERS%'
    AND a.appln_filing_year BETWEEN 2014 AND 2024   -- nur wenn Jahresfilter gesetzt
GROUP BY p.person_name, p.person_ctry_code
ORDER BY families DESC
LIMIT 200
```

Wichtige Details für die Interpretation:

- **Prefix-Suche.** Es ist ein `LIKE 'SUCHWORT%'` — nur Namen, die mit dem Suchwort
  *beginnen*. „Healthineers Siemens" oder „X Siemens Healthineers" würden **nicht**
  gefunden. Suchwort daher möglichst am Namensanfang wählen.
- **Groß-/Kleinschreibung egal.** Eingabe wird auf Großbuchstaben normalisiert und mit
  `UPPER(person_name)` verglichen. `siemens` findet auch `SIEMENS`.
- **Jahresfilter ist optional.** Er wird nur angehängt, wenn der Bereich vom Default
  (1970–2024) abweicht. Achtung: der Jahresfilter wirkt hier auf die *Trefferliste* —
  eine Variante mit 0 Familien im Zeitfenster taucht nicht auf.
- **Deckel bei 200.** `LIMIT 200`, sortiert nach Familienzahl absteigend. Sehr breite
  Suchworte (z.B. nur „Siemens") können also Varianten im Long Tail abschneiden.

Ergebnis: die linke Trefferliste in der UI, jede Zeile mit Land und Familienzahl.

---

### Stufe 1.5 — Gruppieren (die eigentliche Konsolidierungs­entscheidung)

Hier gibt es **keine SQL** — das ist die menschliche bzw. heuristische Entscheidung,
welche Varianten dieselbe Organisation sind. Drei Wege:

1. **Manuell** — Checkboxen an/aus, „All" / „None".
2. **Auto-suggest** — eine Heuristik gruppiert Varianten mit gleichem „Kernnamen".
3. **Anzeigename (Parent)** wählen — der Name, unter dem die Gruppe später erscheint.
   Default ist die Variante mit den meisten Familien („most filings"); alternativ ein
   frei eingegebener „Custom name" (z.B. „Siemens Healthineers Group").

#### Wie „Auto-suggest" den Kernnamen bestimmt

Aus jedem Namen werden Rechtsform- und Füllwörter entfernt; es bleibt das **erste**
inhaltstragende Wort. Verglichen wird dann über dieses eine Kernwort.

Entfernt werden u.a. (Liste `LEGAL_SUFFIXES`):

> AG, GMBH, GMBH&CO, INC, LTD, LIMITED, CO, CORP, CORPORATION, SA, NV, BV, SE, PLC,
> LLC, KG, OHG, SRL, SPA, AB, AS, OY, PTY, LP, LLP, AKTIENGESELLSCHAFT, GESELLSCHAFT,
> MBH, KABUSHIKI, KAISHA, KK, COMPANY, INDUSTRIES, INDUSTRIAL, ELECTRONICS, ELECTRIC,
> INTERNATIONAL, HOLDINGS, GROUP, GLOBAL, OF, THE, AND, DE, DER, DES, ET, UND

**Wichtige Konsequenz / Fallstrick:** Es wird nur das **erste** Kernwort betrachtet.
`Siemens Healthineers AG` → Kern `SIEMENS`. Das heißt: Auto-suggest für „Siemens
Healthineers" gruppiert potenziell *alle* mit `SIEMENS` beginnenden Anmelder mit —
auch „Siemens AG" oder „Siemens Mobility". Auto-suggest ist also bewusst **breit** und
muss vom Menschen nachkontrolliert werden (Checkboxen abwählen). Für saubere
Konsolidierung ist die manuelle Kontrolle der Goldstandard.

---

### Stufe 2 — Trend-Vorschau (optionaler Sanity-Check)

„Preview Trend" prüft die getroffene Auswahl, **bevor** man in die Tiefenanalyse geht.
Eine Query, die die zusammengefasste Familienzahl pro Jahr liefert:

```sql
SELECT a.appln_filing_year AS year,
       COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls201_appln a
JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
JOIN tls206_person p ON pa.person_id = p.person_id
WHERE p.person_name IN ('Siemens Healthineers AG','SIEMENS HEALTHINEERS AG', /* … alle ausgewählten Namen … */)
  AND pa.applt_seq_nr > 0
  AND a.appln_filing_year BETWEEN 1990 AND 2024
GROUP BY a.appln_filing_year
ORDER BY year
```

Die Konsolidierung selbst ist hier sichtbar: aus den vielen ausgewählten Varianten wird
**eine `IN`-Liste**. `COUNT(DISTINCT docdb_family_id)` über alle Varianten hinweg sorgt
dafür, dass eine Familie, die unter zwei Namensvarianten desselben Konzerns angemeldet
wurde, **nur einmal** zählt — das ist der eigentliche Mehrwert der Konsolidierung
gegenüber „Familienzahlen der Varianten einfach addieren".

---

### Stufe 3 — Konsolidierte Tiefenanalyse

Die ausgewählten Namen werden in die Analyse-Ansicht übergeben. Aus ihnen wird ein
WHERE-Filter gebaut:

- **Genau ein Name:** `p.person_name = 'NAME'`
- **Mehrere Namen:** `p.person_name IN ('NAME1','NAME2', …)`

Damit laufen drei Abfragen parallel:

**3a — Filing-Trend (Familien pro Jahr)**

```sql
SELECT a.appln_filing_year AS year,
       COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls201_appln a
JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
JOIN tls206_person p ON pa.person_id = p.person_id
WHERE <Namensfilter>
  AND pa.applt_seq_nr > 0
  AND a.appln_filing_year BETWEEN 1990 AND 2024
GROUP BY a.appln_filing_year
ORDER BY year
```

**3b — Top-Anmeldebehörden / Jurisdiktionen**

```sql
SELECT a.appln_auth AS authority,
       COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls201_appln a
JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
JOIN tls206_person p ON pa.person_id = p.person_id
WHERE <Namensfilter>
  AND pa.applt_seq_nr > 0
GROUP BY a.appln_auth
ORDER BY families DESC
LIMIT 15
```

**3c — Top-Technologiefelder (CPC-4-Steller)**

```sql
SELECT SUBSTR(c.cpc_class_symbol, 1, 4) AS cpc,
       COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls201_appln a
JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
JOIN tls206_person p ON pa.person_id = p.person_id
JOIN tls224_appln_cpc c ON a.appln_id = c.appln_id
WHERE <Namensfilter>
  AND pa.applt_seq_nr > 0
GROUP BY cpc
ORDER BY families DESC
LIMIT 15
```

Alle drei nutzen denselben konsolidierten Namensfilter — die Konsolidierungsentscheidung
aus Stufe 1.5 wird also über alle Auswertungsdimensionen konsistent durchgezogen.

---

## 4. Durchgängiges Beispiel: „Siemens Healthineers"

1. Suchwort `Siemens Healthineers`, Jahre 2014–2024 → **21 Treffer** (Stufe 1).
2. „All" wählt zunächst alle; per Auto-suggest/manuell auf die echten
   Healthineers-Entitäten eingegrenzt → **16 Namen gruppiert**.
3. Anzeigename = `Siemens Healthineers AG` (most filings, 1.017 Familien).
4. „Preview Trend" zeigt: **1.920 Familien gesamt** über die 16 Varianten —
   *konsolidiert*, also ohne Doppelzählung familienübergreifend.
5. „Analyse Consolidated" → Trend-, Jurisdiktions- und CPC-Charts für die Gruppe.

> Beachte: 1.920 ist **kleiner** als die simple Summe aller Varianten-Familien, weil
> Familien, die unter mehreren Varianten geführt werden, nur einmal zählen. Genau das
> ist der Beleg, dass die Konsolidierung funktioniert.

---

## 5. Fallstricke & Qualitätskontrolle

| Risiko | Symptom | Gegenmaßnahme |
|---|---|---|
| **Über-Konsolidierung** | Auto-suggest matcht nur 1. Kernwort → fremde Sparten dabei | Varianten manuell abwählen; Länder/Familienzahl prüfen |
| **Unter-Konsolidierung** | Tochter mit anderem Namensstamm fehlt (z.B. „Endovascular Robotics") | Mehrere Suchworte fahren, Treffer manuell ergänzen |
| **Prefix-Grenze** | Variante beginnt nicht mit dem Suchwort | Suchwort kürzen / am Namensanfang ansetzen |
| **`LIMIT 200`** | Sehr breites Suchwort, Long-Tail-Varianten fehlen | Suchwort spezifischer machen |
| **Jahresfilter in Stufe 1** | Variante mit Filings nur außerhalb des Fensters fehlt in Liste | Filter zunächst weit lassen, erst in Analyse einengen |
| **Tochtergesellschaft = eigene Firma?** | Methodische Frage, keine Datenfrage | Im Trainingskontext bewusst entscheiden und dokumentieren |

**Sanity-Check-Faustregel:** Die konsolidierte Familienzahl (Stufe 2/3) ist immer
**≤ Summe der Einzel-Familienzahlen** aus der Trefferliste. Ist sie *gleich* der Summe,
gab es keine familienübergreifenden Überschneidungen (selten bei echten Konzernen) —
das ist ein Hinweis, die Auswahl noch einmal zu prüfen.

---

## 6. Technischer Anhang (Kurzreferenz)

- **API-Pfad:** `POST /api/query` (SvelteKit) → `sidecar.py /api/query` →
  `PatstatClient(env="PROD").sql_query(sql, use_legacy_sql=False)` (Google BigQuery
  Standard SQL).
- **Sicherheitsschranke:** nur `SELECT`, max. 10.000 Zeichen, keine Multi-Statements.
- **Quellcode:** Stufe 1 & 2 in `src/routes/search/+page.svelte`; Stufe 3 in
  `src/routes/applicant/+page.svelte`; Namensfilter-Logik in `src/lib/context.ts`
  (`nameWhereClause`).
</content>
</invoke>
