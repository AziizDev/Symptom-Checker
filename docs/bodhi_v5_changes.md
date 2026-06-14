# BODHI Symptom Checker v5 — What Changed from v4

## Overview

v5 adds **two new features** to the questioning pipeline. Both are plug-and-play (can be turned off to get exact v4 behavior).

| Feature | What it does | Config toggle |
|---------|-------------|---------------|
| **Variant Follow-Up** | When a symptom is confirmed, immediately asks about its variants (duration, severity, location, etc.) | `variant_followup_enabled: True/False` |
| **Prerequisite Questions** | Asks about risk factors and medical history (pregnancy, diabetes, trauma, etc.) that can eliminate entire groups of conditions | `prerequisite_mode: 'pre_screen'/'integrated'/'both'/'off'` |

### What stayed the same

Functions 1 (Symptom Expansion) and 3 (Rank Conditions) are **identical** to v4. The elimination engine (`compute_yes_eliminations`, `compute_no_eliminations`, `compute_question_value`) is also **unchanged**. Only Function 2 (`ask_questions`) and its supporting helpers/config were modified.

---

## The v4 Problem

In v4, the questioning loop had a gap:

1. **Starting symptom variants were outscored.** Headache has 48 variants (location, severity, pain type, etc.), and they were all in the askable pool. But discovered symptoms like Fever (score 36.8) and Fatigue (33.3) always outscored them. Within the 10-question limit, the system never reached headache variants.

2. **Discovered symptom variants were never built.** If the user confirmed "Fever", the system never asked "How long have you had the fever?" or "What kind of fever is it?". Only the starting symptom's variants were in the pool. Discovered symptoms were treated as flat YES/NO with no follow-up.

3. **Risk factors were invisible.** The knowledge graph has 54 prerequisite edges (e.g., "Eclampsia requires Pregnant", "Diabetic Ketoacidosis requires Diabetes"). v4 never used this data. Conditions like Eclampsia stayed in a male patient's pool, wasting elimination capacity.

---

## How the Questioning Flow Works Now

v5 structures questioning into **three phases**, all within the same `ask_questions()` function:

```
User enters: "headache", Male, 22

Phase 1: Starting Variant Follow-Ups
  Q1 [follow-up variant] Where is the headache?       ← immediate drill-down
  Q2 [follow-up variant] What type of pain is it?
  Q3 [follow-up variant] How severe is it?

Phase 2: Prerequisite Pre-Screen
  Q4 [prerequisite] Have you had a recent head injury? ← eliminates Concussion, TBI if NO
  Q5 [prerequisite] Are you currently pregnant?        ← SKIPPED (male patient, gender filter)
  Q4 [prerequisite] Do you have high blood pressure?   ← eliminates Hypertensive Emergency if NO

Phase 3: Main Loop (same as v4)
  Q6 [discovered] Do you have Fever?                   ← normal scoring competition
  Q7 [follow-up variant] What are the characteristics? ← triggered because user said YES to Fever
  Q8 [discovered] Do you have Fatigue?
  ... continues until max_questions or early stop ...
```

All three phases share the same `questions_asked` counter and respect the same stop conditions (`max_questions`, `min_pool_size`, `score_threshold`).

---

## Cell-by-Cell Changes

### Cell: Configuration (`fdb4c8bb`)

**New keys added to `QUESTIONING_CONFIG`:**

```python
'variant_followup_enabled': True,   # flip to False to disable
'max_variant_followups': 3,         # max variant Qs per confirmed symptom
```

- `variant_followup_enabled`: Master switch. `True` = ask variant questions immediately when any symptom is confirmed. `False` = v4 behavior (variants only compete in scoring pool).
- `max_variant_followups`: Cap per confirmed symptom. Set to 3 so that confirming Fever doesn't consume all 10 questions with fever variants. The top 3 by score are picked; the rest are left for the main loop.

```python
'prerequisite_mode': 'pre_screen',
'max_prerequisite_prescreens': 3,
'prerequisite_elim_strengths': ['very_high', 'high'],
```

- `prerequisite_mode`: Controls when/how prerequisite questions are asked.
  - `'pre_screen'`: Ask the top N most impactful prerequisites upfront, before the main loop.
  - `'integrated'`: Add prerequisites to the main loop's scoring pool — they compete with symptoms.
  - `'both'`: Pre-screen top N, then remaining prerequisites also compete in the main loop.
  - `'off'`: Feature disabled. Exact v4 behavior.
- `max_prerequisite_prescreens`: Maximum number of prerequisite questions in the pre-screen phase.
- `prerequisite_elim_strengths`: When the patient says NO to a prerequisite, only eliminate conditions where the prerequisite relationship has one of these strengths. A `medium` strength prerequisite won't eliminate on NO — it's a softer connection.

**New dict: `PREREQUISITE_QUESTIONS`**

```python
PREREQUISITE_QUESTIONS = {
    'Pregnant':                       'Are you currently pregnant?',
    'Diabetes Type 2':                'Have you been diagnosed with Type 2 Diabetes?',
    'Hypertension':                   'Do you have high blood pressure (hypertension)?',
    'H/O Trauma':                     'Have you had any recent physical trauma or injury?',
    'Alcoholic (current consumer)':   'Do you consume alcohol regularly?',
    ...  # 25 total mappings
}
```

Maps prerequisite condition names (from `nodes_condition`) to human-readable questions. Without this, the system would ask "Do you have or have you had: Pregnant?" — grammatically awkward. The mapping provides doctor-like phrasing. Any prerequisite not in this dict gets the generic fallback: `"Do you have or have you had: {name}?"`.

---

### Cell: Data Loading (`19df454b`)

**Added:**

```python
edges_has_prerequisite = pd.read_csv('../csv/edges_has_prerequisite.csv')
```

This loads the prerequisite relationship data. The CSV has 54 rows with columns:
- `condition_snomed_id_src`: The disease that HAS the prerequisite (e.g., Eclampsia)
- `condition_snomed_id_dst`: The prerequisite itself (e.g., Pregnant)
- `relation_strength`: How strongly required (`very_high`, `high`, `medium`)
- `relation_polarity`: Always `positive` (prerequisite must be present)

```python
edges_has_prerequisite['relation_strength'] = edges_has_prerequisite['relation_strength'].str.lower()
edges_has_prerequisite['relation_polarity'] = edges_has_prerequisite['relation_polarity'].str.lower()
```

Normalize casing, same as we do for `edges_present_in`.

---

### Cell: Helper Functions (`03aa8239`)

**New function: `build_variant_questions(root_snomed_name)`**

This function was extracted from inline code that was duplicated inside `ask_questions`. Now it's reusable — called for both starting symptom variants AND follow-up variants for confirmed discovered symptoms.

```python
def build_variant_questions(root_snomed_name):
```
Takes a root symptom name (e.g., `"Fever"`) and returns a list of askable variant question dicts.

```python
    symptom_group = nodes_symptom[nodes_symptom['root_snomed_name'] == root_snomed_name].copy()
```
Get all rows in `nodes_symptom` that belong to this root symptom. For "Fever", this includes the root row plus variants like "Fever duration_since more than 1 month", "Fever characteristic with chills or rigors", etc.

```python
    if len(symptom_group) == 0:
        return []
```
Safety check — if the symptom name doesn't exist, return empty list.

```python
    variants = symptom_group[
        (symptom_group['relation1_type'].notna()) &
        (symptom_group['uuid'].isin(UUIDS_WITH_EDGES))
    ]
```
Filter to rows that:
1. Have a `relation1_type` (like `duration_since`, `severity`, `location`) — this means they're actual variants, not the root row.
2. Have edges in `edges_present_in` — if a variant UUID has no edges, asking about it provides zero diagnostic value.

```python
    questions = []
    for relation_type, group in variants.groupby('relation1_type'):
```
Group variants by relation type. All "duration" variants become one question ("How long?"), all "severity" variants become one question ("How severe?"), etc.

```python
        question_text = RELATION_QUESTIONS.get(relation_type, f"About the {relation_type}?")
```
Look up the human-readable question text. `RELATION_QUESTIONS['duration_since']` = `"How long have you had this symptom?"`.

```python
        selection_type = group.iloc[0]['grouping1_selection_type']
```
Either `'s'` (single-select: pick ONE option) or `'m'` (multi-select: pick multiple). Determines the input mode.

```python
        options = []
        for _, row in group.iterrows():
            if pd.notna(row.get('child2_name')):
                label = f"{row['child1_name']} > {row['child2_name']}"
            elif pd.notna(row.get('child1_name')):
                label = row['child1_name']
            else:
                label = row['name']
            options.append({'label': label, 'uuid': row['uuid'], 'name': row['name']})
```
Build display labels for each option. Uses the most specific name available: `child2_name` if it exists (two-level hierarchy like "Head > Frontal"), then `child1_name`, then the full `name`.

```python
        questions.append({
            'type': 'variant', 'root_name': root_snomed_name,
            'relation_type': relation_type, 'question': question_text,
            'selection_type': selection_type, 'options': options,
            'score_uuid': group.iloc[0]['uuid'], 'all_uuids': group['uuid'].tolist()
        })
```
Build the question dict. `score_uuid` is the UUID used for scoring (first variant in the group — representative). `all_uuids` is every variant UUID in this group.

---

**New function: `build_prerequisite_questions(candidate_pool, gender=None)`**

Finds which prerequisites from `edges_has_prerequisite` are relevant to the current condition pool.

```python
def build_prerequisite_questions(candidate_pool, gender=None):
    relevant = edges_has_prerequisite[
        edges_has_prerequisite['condition_snomed_id_src'].isin(candidate_pool)
    ]
```
Filter prerequisite edges to only those whose source condition (the disease) is currently in the pool. If Eclampsia isn't in the pool, there's no point asking about pregnancy.

```python
    if len(relevant) == 0:
        return []
```
No prerequisites relevant to the current pool — return empty.

```python
    questions = []
    for prereq_id, group in relevant.groupby('condition_snomed_id_dst'):
```
Group by prerequisite. Multiple diseases may share the same prerequisite (e.g., 9 conditions require "Pregnant").

```python
        affected_conditions = set(group['condition_snomed_id_src'].unique()) & candidate_pool
        if not affected_conditions:
            continue
```
Count how many pool conditions depend on this prerequisite. Intersect with `candidate_pool` in case conditions were eliminated between build and ask.

```python
        prereq_cond = nodes_condition[nodes_condition['snomed_id'] == prereq_id]
        if len(prereq_cond) == 0:
            continue
        prereq_name = prereq_cond.iloc[0]['name']
```
Look up the prerequisite's name from `nodes_condition`. If the prerequisite ID doesn't exist in the condition table, skip it.

```python
        if gender:
            gender_col = get_gender_column(gender)
            gender_weight = prereq_cond.iloc[0][gender_col]
            if pd.notna(gender_weight) and float(gender_weight) == 0.0:
                continue
```
**Gender filter.** If the patient is male, check the prerequisite's `likelihood_male` column. If it's `0.0`, this prerequisite is impossible for this gender (e.g., "Pregnant" has `likelihood_male = 0.0`). Skip the question entirely — don't waste a question slot asking a male patient if they're pregnant.

```python
        question_text = PREREQUISITE_QUESTIONS.get(
            prereq_name,
            f"Do you have or have you had: {prereq_name}?"
        )
```
Get the human-readable question. Uses the `PREREQUISITE_QUESTIONS` dict with a generic fallback.

```python
        questions.append({
            'type': 'prerequisite',
            'prereq_id': prereq_id,
            'prereq_name': prereq_name,
            'question': question_text,
            'affected_condition_ids': affected_conditions,
            'num_affected': len(affected_conditions),
            'score_uuid': f"prereq_{prereq_id}",
        })
```
Build the question dict. `score_uuid` uses a `"prereq_"` prefix to avoid collision with symptom UUIDs in the `asked_uuids` dedup set.

```python
    questions.sort(key=lambda x: x['num_affected'], reverse=True)
    return questions
```
Sort by impact — prerequisites affecting the most pool conditions come first. "Pregnant" (9 conditions) ranks above "H/O chickenpox" (1 condition).

---

### Cell: `ask_questions` — Function 2 (`265a8604`)

This is where the main changes live. The function now has three inner helpers and three questioning phases.

#### Inner Helper: `_ask_one_variant(vq, is_followup=False)`

Handles the display, input, scoring, elimination, and logging for a single variant question. Reused in four places:
1. Phase 1: Starting symptom variant follow-ups
2. Phase 3: Starting symptom variants picked by the main loop
3. Phase 3: Follow-up variants after a confirmed discovered symptom
4. Phase 3: Discovered symptom variant follow-ups (Fever confirmed → ask fever variants)

In v4, this logic was written inline twice — once for the variant branch and once it was missing entirely for discovered symptoms. Extracting it into a helper avoids ~45 lines of duplication.

**Key implementation detail — `candidate_pool.difference_update(eliminated)` instead of `candidate_pool -= eliminated`:**

```python
eliminated, _ = compute_no_eliminations(
    vq['score_uuid'], candidate_pool, protection_counters
)
candidate_pool.difference_update(eliminated)
```

The inner function modifies `candidate_pool` (which belongs to the outer `ask_questions` scope). In Python, `candidate_pool -= eliminated` would create a NEW local set, shadowing the outer variable. `difference_update()` modifies the set in-place, which is what we want — changes propagate back to the outer scope without needing `nonlocal`.

Similarly, `eliminated, _ = ...` unpacks into a local variable instead of overwriting `protection_counters`, so the outer dict stays intact.

#### Inner Helper: `_ask_one_prerequisite(pq)`

Handles prerequisite question display, input, and elimination.

```python
def _ask_one_prerequisite(pq):
    affected_in_pool = pq['affected_condition_ids'] & candidate_pool
    if not affected_in_pool:
        return False
```
Re-intersect with the current pool. Between when the question was built and when it's asked, some affected conditions may have been eliminated by other questions. If none remain, skip (return `False` = "didn't actually ask").

**On YES answer:**

```python
    if answer in ('y', 'yes'):
        for cid in affected_in_pool:
            if cid in condition_points:
                condition_points[cid] += config_r['yes_point']
        print(f"    -> Yes. {len(affected_in_pool)} conditions supported.")
```
Patient has this prerequisite. All affected conditions get +1 ranking point (evidence FOR them). No elimination — having a prerequisite doesn't rule anything out.

**On NO answer:**

```python
    else:
        elim_strengths = config_q.get('prerequisite_elim_strengths', ['very_high', 'high'])
        for _, row in edges_has_prerequisite[
            (edges_has_prerequisite['condition_snomed_id_dst'] == pq['prereq_id']) &
            (edges_has_prerequisite['condition_snomed_id_src'].isin(candidate_pool))
        ].iterrows():
            if row['relation_strength'] in elim_strengths:
                to_eliminate.add(row['condition_snomed_id_src'])
        candidate_pool.difference_update(to_eliminate)
```
Patient does NOT have this prerequisite. Look at each edge linking a pool condition to this prerequisite. If the edge strength is `very_high` or `high` (configurable), eliminate that condition — it requires this prerequisite and the patient doesn't have it. A `medium` strength edge is a softer link, so the condition survives.

Example: Patient says NO to "Are you currently pregnant?"
- Eclampsia requires Pregnant with `very_high` strength → **eliminated**
- Pre-eclampsia requires Pregnant with `very_high` strength → **eliminated**
- ... all 9 pregnancy conditions eliminated in one question

#### Build Askable Pool (Parts A, B, C)

```python
# Part A: Variant questions (starting symptom) — same as v4
# Part B: Discovered root symptoms — same as v4

# Part C: Prerequisite questions (NEW)
all_prereq_qs = []
if prereq_mode != 'off':
    all_prereq_qs = build_prerequisite_questions(candidate_pool, gender_input_global)
if prereq_mode in ('integrated', 'both'):
    askable.extend(all_prereq_qs)
```
Build prerequisite questions once. If mode is `integrated` or `both`, add them to the `askable` list so they compete with symptoms in the main loop. If mode is `pre_screen`, they stay in `all_prereq_qs` only — used by Phase 2 but NOT added to the main loop's pool.

#### Phase 1: Starting Variant Follow-Ups

```python
if config_q.get('variant_followup_enabled', False):
    starting_variant_qs = build_variant_questions(root_name)
```
Build variant questions for the starting symptom (same function that discovers variants for any root symptom).

```python
    scored_starting = []
    for svq in starting_variant_qs:
        if svq['score_uuid'] in asked_uuids:
            continue
        sv_score = compute_question_value(
            svq['score_uuid'], candidate_pool, confirmed_uuids,
            protection_counters, ELIM_CONFIG, QUESTIONING_CONFIG
        )[0]
        scored_starting.append((sv_score, svq))
    scored_starting.sort(key=lambda x: x[0], reverse=True)
```
Score each variant using the same `compute_question_value` function used in the main loop. Sort by score descending — ask the most diagnostically valuable variants first.

For example, with Headache:
- "Where is it located?" might score 5.2 (many conditions distinguish headache location)
- "What type of pain?" might score 4.8
- "How long have you had it?" might score 3.1
- "Which side?" might score 1.5

The top 3 get asked.

```python
    max_fups = config_q.get('max_variant_followups', 3)
    fup_count = 0
    for _, svq in scored_starting:
        if fup_count >= max_fups:
            break
        if questions_asked >= config_q['max_questions']:
            break
        if len(candidate_pool) <= config_q['min_pool_size']:
            break
        asked_uuids.add(svq['score_uuid'])
        questions_asked += 1
        _ask_one_variant(svq, is_followup=True)
        fup_count += 1
```
Ask up to `max_variant_followups` (default 3). Respects all stop conditions. Each question:
1. Gets marked as asked (`asked_uuids.add`) so the main loop won't ask it again
2. Increments `questions_asked` (counts toward `max_questions`)
3. Delegates to `_ask_one_variant` which handles display, input, scoring, elimination, and logging

#### Phase 2: Prerequisite Pre-Screen

```python
if prereq_mode in ('pre_screen', 'both') and all_prereq_qs:
    max_prescreens = config_q.get('max_prerequisite_prescreens', 3)
    prescreen_count = 0
    for pq in all_prereq_qs:
```
Iterate over prerequisites in impact order (most affected conditions first).

```python
        if prescreen_count >= max_prescreens:
            break
        if questions_asked >= config_q['max_questions']:
            break
        if len(candidate_pool) <= config_q['min_pool_size']:
            break
```
Three stop conditions: max pre-screens reached, overall max questions reached, or pool already small enough.

```python
        affected_now = pq['affected_condition_ids'] & candidate_pool
        if not affected_now:
            continue
```
Before asking, re-check how many affected conditions are still in the pool. If a previous prerequisite already eliminated them all, skip this one. **Important: `continue` does NOT increment `prescreen_count`** — skipped questions don't consume the pre-screen budget.

```python
        asked_uuids.add(pq['score_uuid'])
        questions_asked += 1
        asked = _ask_one_prerequisite(pq)
        if asked:
            prescreen_count += 1
```
If `_ask_one_prerequisite` returns `True`, the question was actually asked. Increment the pre-screen counter.

#### Phase 3: Main Loop — Prerequisite Scoring

The main loop is identical to v4 except for how prerequisites are scored:

```python
        scored = []
        for q in askable:
            if q['score_uuid'] in asked_uuids:
                continue
            if q['type'] == 'prerequisite':
                affected_now = q['affected_condition_ids'] & candidate_pool
                if affected_now:
                    scored.append((len(affected_now), 0, len(affected_now), len(affected_now), 0, q))
                continue
```
Prerequisite questions can't use `compute_question_value` (no symptom UUID). Their score is simply the **number of pool conditions they'd affect**. This means:
- "Pregnant" affecting 9 pool conditions gets score = 9
- Symptom scores like Fever = 36.8 still outscore it
- Prerequisites compete fairly at the tail end of questioning

The tuple format `(score, yes_elim, no_elim, connected, p_yes, q)` matches the symptom scoring tuple so sorting works uniformly.

#### Phase 3: Main Loop — Discovered Symptom Variant Follow-Up

This block triggers INSIDE the main loop, after a discovered symptom gets a YES answer:

```python
            if (q['type'] == 'discovered' and
                answer in ('y', 'yes') and
                config_q.get('variant_followup_enabled', False)):
```
Three conditions must all be true: it's a discovered symptom, patient said YES, and variant follow-up is enabled.

```python
                followup_qs = build_variant_questions(q['root_name'])
```
Build variant questions for this discovered symptom. Example: user confirmed Fever → builds "How long?", "What pattern?", "What characteristics?" for Fever.

```python
                scored_fups = []
                for fq in followup_qs:
                    if fq['score_uuid'] in asked_uuids:
                        continue
                    fs = compute_question_value(
                        fq['score_uuid'], candidate_pool, confirmed_uuids,
                        protection_counters, ELIM_CONFIG, QUESTIONING_CONFIG
                    )[0]
                    scored_fups.append((fs, fq))
                scored_fups.sort(key=lambda x: x[0], reverse=True)
```
Score and sort. Only variants not already asked and with edges in the current pool.

```python
                max_fups = config_q.get('max_variant_followups', 3)
                fup_count = 0
                for _, fq in scored_fups:
                    if fup_count >= max_fups:
                        break
                    if questions_asked >= config_q['max_questions']:
                        break
                    if len(candidate_pool) <= config_q['min_pool_size']:
                        break
                    asked_uuids.add(fq['score_uuid'])
                    questions_asked += 1
                    _ask_one_variant(fq, is_followup=True)
                    fup_count += 1
```
Ask up to 3 (configurable) of the best variant follow-ups. Same stop-condition pattern as Phase 1. Each follow-up counts toward `max_questions`.

---

## How Question Scoring Works

All question types go through scoring to determine which gets asked next. Here's how each type is scored:

### Symptom Questions (variant + discovered)

Scored by `compute_question_value()`. Two methods available (set in `question_scoring_method`):

**Method: `normalized_symptom_score` (default in v5)**

```
symptom_score = SUM over all conditions C connected to this symptom:
    P(S|C)_compressed * P(C)_compressed

Where:
    P(S|C)_compressed = LIKELIHOOD_SCORES_COMPRESSED[edge.likelihood_symptom_given_condition]
    P(C)_compressed   = LIKELIHOOD_SCORES_COMPRESSED[condition.overall_likelihood]
```

This gives a raw "importance" score. Fever scores 36.8 because it's connected to 145 conditions, many with high P(S|C) and high P(C). A rare variant of an uncommon symptom scores much lower.

The score is computed against ALL conditions (not just the current pool), making it stable across iterations.

**Method: `ev` (Expected Value)**

```
P(YES) = SUM over pool conditions connected to symptom:
    P(S|C) * P(C) / TOTAL_CONDITION_WEIGHT

Expected Elimination = P(YES) * yes_elim_count + P(NO) * no_elim_count
Score = Expected Elimination / pool_size
```

This measures expected pool reduction — how many conditions we expect to eliminate by asking this question.

### Prerequisite Questions

```
score = number of pool conditions affected by this prerequisite
```

Simple count. "Pregnant" affecting 9 conditions gets score 9. This is lower than most symptom scores (Fever = 36.8), so in `integrated` mode, prerequisites typically get asked after high-impact symptoms are exhausted. In `pre_screen` mode, they're asked first regardless of score.

---

## Plug-and-Play Configurations

To get **exact v4 behavior**, set:
```python
'variant_followup_enabled': False,
'prerequisite_mode': 'off',
```

To get **v5 with everything on** (recommended):
```python
'variant_followup_enabled': True,
'max_variant_followups': 3,
'prerequisite_mode': 'pre_screen',
'max_prerequisite_prescreens': 3,
```

To **only use prerequisites** (no variant follow-ups):
```python
'variant_followup_enabled': False,
'prerequisite_mode': 'both',
```

To **only use variant follow-ups** (no prerequisites):
```python
'variant_followup_enabled': True,
'prerequisite_mode': 'off',
```

---

## Data Flow Diagram

```
User Input: "headache", Male, 22
         |
         v
[Function 1: Symptom Expansion]
   - Finds 48 headache variants
   - Finds 110 connected conditions
   - Discovers 279 related root symptoms
         |
         v
[Function 2: ask_questions]
   |
   |-- Auto-confirm "Headache" (+1 point to 110 connected conditions)
   |
   |-- Phase 1: Starting Variant Follow-Ups
   |     build_variant_questions("Headache")
   |     Score each variant with compute_question_value()
   |     Ask top 3 via _ask_one_variant()
   |     Each answer: confirms/denies UUIDs, updates points, runs elimination
   |
   |-- Phase 2: Prerequisite Pre-Screen
   |     build_prerequisite_questions(pool, gender="M")
   |     Gender filter: skip "Pregnant" (likelihood_male=0.0)
   |     Ask top 3 by impact via _ask_one_prerequisite()
   |     NO answer: eliminate conditions with very_high/high prerequisite strength
   |     YES answer: +1 point to affected conditions
   |
   |-- Phase 3: Main Loop
   |     Score all remaining questions (variants + discovered + prerequisites)
   |     Pick highest score
   |     If variant  → _ask_one_variant()
   |     If prereq   → _ask_one_prerequisite()
   |     If discovered:
   |       Ask YES/NO
   |       If YES and variant_followup_enabled:
   |         build_variant_questions(confirmed_symptom)
   |         Ask top 3 follow-up variants
   |     Repeat until max_questions or early stop
   |
   v
[Function 3: Rank Conditions]
   - Uses confirmed_uuids from all phases (including variant selections)
   - More confirmed symptoms = more P(C|S) data = better ranking
```

---

## Test Run Comparison

**v4 with "Mouth breathing with nasal obstruction" (from handover doc):**
- 10 questions, all discovered symptoms (Fever, Fatigue, etc.)
- No variant questions ever asked
- Headache variants outscored by discovered symptoms

**v5 with same symptom (from actual test run):**
- Q1: Starting variant follow-up (duration — "more than 1 month?")
- Q2: Discovered symptom (Fever — YES)
- Q3-Q5: Fever variant follow-ups (characteristics, what helps, pattern)
- Q6: Discovered symptom (Discoloration of skin — NO, eliminated 1)
- Q7: Discovered symptom (Catarrhal nasal discharge — YES)
- Q8-Q10: Catarrhal nasal discharge variant follow-ups

Result: 6 confirmed symptoms (vs 1 in v4 with all-NO answers), 4 surviving conditions ranked accurately with Acute Rhinitis at #1 (score 10.4).

The key improvement: v5 gathers **much richer evidence** per confirmed symptom because it immediately drills down into variants, matching how a doctor would interview a patient.
