# Skill-Methodik: Anmelder-Konsolidierung als reproduzierbares Verfahren

**Zielgruppe:** Claude-Skill-Entwickler
**Zweck:** Eine in sich geschlossene, algorithmische Spezifikation der mehrstufigen
Anmelder-Konsolidierung, damit ein Agent (Claude-Skill) das Verfahren *ohne* die UI
reproduzieren kann — nur über SQL gegen PATSTAT. Diese Datei ist die Quelle der
Wahrheit für die Skill-Erweiterung; sie ist aus dem Code von PATSTAT Explorer
abgeleitet (`src/routes/search/+page.svelte`, `src/routes/applicant/+page.svelte`,
`src/lib/context.ts`, `src/routes/api/query/+server.ts`, `sidecar.py`).

---

## 0. Mentales Modell in einem Satz

> Breite Prefix-Suche über `tls206_person` → pro Namensvariante Familienzahl →
> Varianten zu *einer* Entität gruppieren (Heuristik + menschliche/agentische Prüfung)
> → konsolidierte Kennzahlen über eine `IN`-Liste mit familienweiter Deduplizierung.

Zähleinheit ist **immer** die DOCDB-Patentfamilie:
`COUNT(DISTINCT a.docdb_family_id)`. Anmelder-Rolle **immer**
`pa.applt_seq_nr > 0`.

---

## 1. Ausführungsumgebung & harte Constraints

Jede Query geht als `{"sql": "..."}` an den Query-Endpoint. Vor Ausführung gilt
(siehe `src/routes/api/query/+server.ts`):

- **Nur `SELECT`.** Der Validator prüft `^SELECT\b` (case-insensitive). `WITH …`
  (CTE) am Anfang wird vom Endpoint **abgelehnt** — CTEs daher vermeiden oder in
  Subqueries umschreiben.
- **Max. 10.000 Zeichen** pro SQL-String. Lange `IN`-Listen im Blick behalten.
- **Keine Multi-Statements.** `;` gefolgt von einem weiteren SQL-Keyword wird
  geblockt. Genau eine Anweisung pro Request.
- **Dialekt:** Google **BigQuery Standard SQL** (`use_legacy_sql=False`),
  ausgeführt von `PatstatClient(env="PROD")` in `sidecar.py`.
- **Konvention `LIMIT`:** explorative Queries immer mit `LIMIT` (Projektkonvention
  ≤ 500; die Discovery-Query nutzt `LIMIT 200`).
- Antwort ist JSON; der SvelteKit-Layer liefert `{rows, count}`, der Skill sollte
  `data.rows ?? data` behandeln.

---

## 2. Eingabe-Normalisierung (exakt nachbauen)

### 2.1 Suchwort für die Discovery-Query (Stufe 1)

```
escaped = userInput.trim().replace(/'/g, "''").toUpperCase()
```

- `trim()`, alle einfachen Anführungszeichen verdoppeln (`'` → `''`),
  in **Großbuchstaben**.
- Verglichen wird gegen `UPPER(p.person_name)` mit angehängtem `%`
  → reine **Prefix**-Suche.

### 2.2 Einzelnen Namen für `IN`-Liste / Gleichheit escapen

```
sqlName = "'" + name.replace(/'/g, "''") + "'"
```

Kein `UPPER()` und kein `%` — in Stufe 2/3 wird auf **exakte** `person_name`-Werte
gefiltert (die Werte, die Stufe 1 zurückgegeben hat, inkl. Original-Schreibweise).

### 2.3 Jahresfilter (bedingt)

Default-Fenster ist 1970–2024. Den Zusatz **nur** anhängen, wenn der Nutzer davon
abweicht (`from > 1970` ODER `to < 2024`):

```
yearFilter = (from > 1970 || to < 2024)
  ? `AND a.appln_filing_year BETWEEN ${from} AND ${to}`
  : ''
```

---

## 3. Stufe 1 — Discovery-Query (Varianten + Familienzahlen)

Template (Platzhalter in `<…>`):

```sql
SELECT p.person_name AS name,
       p.person_ctry_code AS country,
       COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls206_person p
JOIN tls207_pers_appln pa ON p.person_id = pa.person_id
JOIN tls201_appln a ON pa.appln_id = a.appln_id
WHERE pa.applt_seq_nr > 0
    AND UPPER(p.person_name) LIKE '<ESCAPED_PREFIX>%'
    <YEAR_FILTER>
GROUP BY p.person_name, p.person_ctry_code
ORDER BY families DESC
LIMIT 200
```

Rückgabe: Liste von `{name, country, families}`. Das ist die Kandidatenmenge für die
Gruppierung.

---

## 4. Stufe 1.5 — Gruppierungs-Heuristik (`coreNameOf` + Auto-Suggest)

Diese Stufe ist clientseitig/algorithmisch — **keine SQL**. Sie liefert dem Agenten
einen Vorschlag, welche Varianten zusammengehören. Der Agent sollte den Vorschlag
*prüfen* (Länder, Familienzahlen, offensichtliche Fremdfirmen), nicht blind übernehmen.

### 4.1 Konstante: `LEGAL_SUFFIXES` (vollständig, Großbuchstaben)

```
AG, GMBH, GMBH&CO, INC, LTD, LIMITED, CO, CORP, CORPORATION, SA, NV, BV, SE, PLC,
LLC, KG, OHG, SRL, SPA, AB, AS, OY, PTY, LP, LLP, AKTIENGESELLSCHAFT, GESELLSCHAFT,
MBH, KABUSHIKI, KAISHA, KK, COMPANY, INDUSTRIES, INDUSTRIAL, ELECTRONICS, ELECTRIC,
INTERNATIONAL, HOLDINGS, GROUP, GLOBAL, OF, THE, AND, DE, DER, DES, ET, UND
```

### 4.2 `coreNameOf(name)` — Pseudocode (1:1 aus dem Code)

```
function coreNameOf(name):
    words = name.toUpperCase()
                .replace(/[.,()]/g, ' ')      # Punkt, Komma, Klammern → Space
                .split(/\s+/)
                .filter(nonEmpty)
    core = []
    for w in words:
        if w in LEGAL_SUFFIXES: continue       # Rechtsform/Stopword überspringen
        core.push(w)
        if core.length == 1: break             # NUR das erste Kernwort!
    return core.join(' ')
```

> **Kritischer Punkt:** Es wird **nur das erste** inhaltstragende Wort behalten
> (`break` bei `core.length == 1`). `coreNameOf("Siemens Healthineers AG") == "SIEMENS"`.
> Auto-Suggest ist dadurch absichtlich **breit** und over-matcht (gruppiert „Siemens
> AG", „Siemens Mobility" mit). Der Skill muss nach dem Vorschlag eine
> Plausibilitätsprüfung machen (siehe §7), sonst entsteht Über-Konsolidierung.

### 4.3 Auto-Suggest-Auswahl

```
targetCore = coreNameOf(anchorName)              # anchor = vom Nutzer/Skill gewählt
selected   = { a.name for a in candidates if coreNameOf(a.name) == targetCore }
parent     = anchorName                          # Anzeigename
```

`parent` (Anzeigename) ist standardmäßig die Variante mit den **meisten Familien**
(`ORDER BY families DESC` → erstes Element der ausgewählten Menge), kann aber ein
frei gesetzter Label-String sein.

---

## 5. Namensfilter-Konstruktion (für Stufe 2 & 3)

Aus der finalen Auswahl `selectedNames` (Original-Schreibweise!) wird der WHERE-Filter
gebaut (Logik aus `nameWhereClause` in `src/lib/context.ts`):

```
if selectedNames.length == 0:   filter = "1=0"                       # nichts matchen
elif selectedNames.length == 1: filter = "p.person_name = " + sqlName(selectedNames[0])
else:                           filter = "p.person_name IN (" +
                                          selectedNames.map(sqlName).join(",") + ")"
```

`sqlName()` = Escaping aus §2.2. (Optionaler Person-Alias-Parameter: Default `p`.)

URL-Transport in der UI nutzt `names=NAME1|||NAME2|||…&label=PARENT` — für den Skill
irrelevant, aber nützlich zu wissen, falls Deep-Links erzeugt werden sollen.

---

## 6. Stufe 2 & 3 — Konsolidierte Auswertungs-Queries

Alle nutzen denselben `<NAME_FILTER>` aus §5. Damit ist die Konsolidierung über alle
Dimensionen konsistent.

### 6.1 Trend / Sanity-Preview (Familien pro Jahr)

```sql
SELECT a.appln_filing_year AS year,
       COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls201_appln a
JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
JOIN tls206_person p ON pa.person_id = p.person_id
WHERE <NAME_FILTER>
  AND pa.applt_seq_nr > 0
  AND a.appln_filing_year BETWEEN 1990 AND 2024
GROUP BY a.appln_filing_year
ORDER BY year
```

### 6.2 Top-Jurisdiktionen (Anmeldebehörden)

```sql
SELECT a.appln_auth AS authority,
       COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls201_appln a
JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
JOIN tls206_person p ON pa.person_id = p.person_id
WHERE <NAME_FILTER>
  AND pa.applt_seq_nr > 0
GROUP BY a.appln_auth
ORDER BY families DESC
LIMIT 15
```

### 6.3 Top-Technologiefelder (CPC-4-Steller)

```sql
SELECT SUBSTR(c.cpc_class_symbol, 1, 4) AS cpc,
       COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls201_appln a
JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
JOIN tls206_person p ON pa.person_id = p.person_id
JOIN tls224_appln_cpc c ON a.appln_id = c.appln_id
WHERE <NAME_FILTER>
  AND pa.applt_seq_nr > 0
GROUP BY cpc
ORDER BY families DESC
LIMIT 15
```

### 6.4 Konsolidierte Gesamt-Familienzahl (für §7-Check, eigene Hilfs-Query)

```sql
SELECT COUNT(DISTINCT a.docdb_family_id) AS families
FROM tls201_appln a
JOIN tls207_pers_appln pa ON a.appln_id = pa.appln_id
JOIN tls206_person p ON pa.person_id = p.person_id
WHERE <NAME_FILTER>
  AND pa.applt_seq_nr > 0
```

---

## 7. Validierung / Selbstkontrolle (Skill-Logik)

Nach der Gruppierung **vor** dem Reporting prüfen:

1. **Dedup-Plausibilität:** `consolidated_families` (§6.4) muss
   `≤ Σ families_i` (Summe der Einzel-Familienzahlen aus Stufe 1 für die
   ausgewählten Varianten) sein. Verletzung ⇒ Bug im Filter/Escaping.
2. **Echte Überlappung erwartet:** Bei einem realen Konzern ist meist
   `consolidated_families < Σ families_i` (familienübergreifende Doppelungen).
   `consolidated == Σ` ⇒ Hinweis auf evtl. fälschlich zusammengefasste, in
   Wahrheit unverbundene Entitäten → Auswahl überprüfen.
3. **Over-Match-Check (gegen §4.2-Falle):** Wenn Auto-Suggest genutzt wurde, die
   ausgewählten `name`/`country`-Paare gegen den erwarteten Geschäftsbereich
   sichten; verdächtige Varianten (anderer Sektor, unplausibles Land) ausschließen
   und Filter neu bauen.
4. **`IN`-Listen-Länge:** SQL-String < 10.000 Zeichen halten (Constraint §1). Bei
   sehr vielen Varianten ggf. in mehrere Abfragen splitten und
   `COUNT(DISTINCT family_id)` **nicht** über Teilmengen aufaddieren (würde
   Dedup brechen) — stattdessen Filter so kürzen, dass eine Query reicht.

---

## 8. Schritt-für-Schritt-Rezept für den Skill

```
EINGABE: suchwort, [jahrVon, jahrBis], [anker/label]

1. escaped   = normalize(suchwort)                         # §2.1
   yearFilter = buildYearFilter(jahrVon, jahrBis)           # §2.3
2. kandidaten = runSQL( DISCOVERY_TEMPLATE )                # §3  → [{name,country,families}]
3. anker      = anker ?? kandidaten[0].name                 # meiste Familien
   vorschlag  = { k.name : k in kandidaten
                          if coreNameOf(k.name)==coreNameOf(anker) }   # §4
4. auswahl    = pruefe_und_bereinige(vorschlag, kandidaten) # §7.3 (Sektor/Land/Plausibilität)
   label      = label ?? anker
5. filter     = buildNameFilter(auswahl)                    # §5
6. total      = runSQL( TOTAL_TEMPLATE(filter) )            # §6.4
   assert total <= sum(k.families for k in auswahl)          # §7.1
7. trend      = runSQL( TREND_TEMPLATE(filter) )            # §6.1
   jurisd     = runSQL( JURISDICTION_TEMPLATE(filter) )     # §6.2
   cpc        = runSQL( CPC_TEMPLATE(filter) )              # §6.3
8. REPORT unter `label`: total, trend, jurisd, cpc
   + Liste der konsolidierten Namen (Transparenz!)
```

**Transparenzpflicht:** Im Output immer die konkrete Liste der zusammengefassten
`person_name`-Varianten ausgeben, damit die Konsolidierungsentscheidung
nachvollziehbar/überprüfbar bleibt.

---

## 9. Mini-Referenz: relevante PATSTAT-Felder

| Tabelle | Feld | Bedeutung |
|---|---|---|
| `tls206_person` | `person_id` | PK Person/Organisation (kein Entity-Resolution!) |
| `tls206_person` | `person_name` | Name (viele Varianten je Firma) |
| `tls206_person` | `person_ctry_code` | Ländercode der Person |
| `tls207_pers_appln` | `person_id`, `appln_id` | Verknüpfung Person ↔ Anmeldung |
| `tls207_pers_appln` | `applt_seq_nr` | `> 0` = Anmelder-Rolle |
| `tls207_pers_appln` | `invt_seq_nr` | `> 0` = Erfinder-Rolle (hier ungenutzt) |
| `tls201_appln` | `appln_id` | PK Anmeldung |
| `tls201_appln` | `docdb_family_id` | DOCDB-Familie → **Zähleinheit** |
| `tls201_appln` | `appln_filing_year` | Anmeldejahr (für Trend/Filter) |
| `tls201_appln` | `appln_auth` | Anmeldebehörde/Jurisdiktion |
| `tls224_appln_cpc` | `cpc_class_symbol` | CPC-Symbol (4-Steller via `SUBSTR(...,1,4)`) |
</content>
