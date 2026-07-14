# Symptom Checker Engine

**BODHI** (Bharat Ontology for Disease & Healthcare Informatics) is a medical knowledge graph and diagnostic reasoning engine that maps symptoms to conditions through a structured ontology. **BODHI-S** is the symptom-checker module. it takes a patient's chief complaint, asks targeted follow-up questions, and ranks the most likely conditions using probabilistic elimination and scoring.

---

## Live App

The engine is deployed and can be used directly in the browser, no setup or installation required:

### **https://b-symptom-checker.streamlit.app/**

To run it locally instead, see [Setup](#setup).

---

## Table of Contents

- [Live App](#live-app)
- [Overview](#overview)
- [Knowledge Graph](#knowledge-graph)
- [How the Algorithm Works](#how-the-algorithm-works)
  - [Specialities](#specialities)
- [Notebook Versions (v4 -> v8)](#notebook-versions-v4--v8)
- [Streamlit Web App](#streamlit-web-app)
- [CLI Agent](#cli-agent)
- [Data Formats](#data-formats)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Setup](#setup)

---

## Overview

The system works in three stages:

1. **Symptom Expansion**: The patient's chief complaint (e.g., "Headache") is matched to the ontology. All variants of that symptom (location, severity, onset, duration, pain type, etc.) and all connected conditions are discovered. Related symptoms shared by those conditions are also identified as "discovered" symptoms to ask about.

2. **Questioning**: A multi-phase questioning engine asks the most diagnostically valuable questions. Questions include variant follow-ups ("Where is the headache?"), prerequisite screening ("Have you had a head injury?"), discovered symptom checks ("Do you have fever?"), and adaptive follow-ups. Each answer triggers elimination of unlikely conditions and accumulates evidence points.

3. **Ranking**: Surviving conditions are ranked using a formula that combines yes/no evidence points, P(C|S) scores from confirmed symptoms, condition prevalence P(C), and demographic weights (age bracket, gender). The top conditions are presented with triage levels (emergency, worrisome, OPD-managed), and each condition is mapped to the medical **speciality** that treats it.

---

## Knowledge Graph

The BODHI ontology is a property graph with three node types and five edge types:

### Nodes

| Type | Count | Key Properties |
|------|-------|---------------|
| **Symptom** | 4,037 | `uuid`, `root_snomed_id`, `root_snomed_name`, `name`, `triage_level`, variants (`relation1_type`, `child1_name`, `grouping1_selection_type`, up to 3 levels) |
| **Condition** | 779 | `snomed_id`, `name`, `type_condition`, `triage_level`, `overall_likelihood`, demographic weights (`likelihood_male/female`, `likelihood_age_*` for 8 brackets) |
| **Speciality** | 39 | `id`, `name`. Medical speciality categories (e.g., Neurologist, ENT). Used to label each ranked condition with the speciality that treats it |

### Edges

| Edge Type | Count | Description |
|-----------|-------|-------------|
| **PRESENT_IN** | 10,352 | Symptom -> Condition. Properties: `likelihood_symptom_given_condition` (P(S\|C)), `likelihood_condition_given_symptom` (P(C\|S)), `strong_predictor` |
| **HAS_PREREQUISITE** | 53 | Condition -> Condition. A condition requires a prerequisite (e.g., Eclampsia requires Pregnant). Properties: `relation_strength`, `relation_polarity` |
| **RELATED_TO** | 221 | Condition -> Condition associations |
| **TREATED_BY** | 1,558 | Condition -> Speciality. Which medical speciality treats a condition. Properties: `weight` (ordinal, `very_high` -> `rare`). Covers 567 of 779 conditions |
| **IS_INFLUENCED_BY** | 1,020 | Condition -> Risk factor |

### Symptom Variants

Symptoms have a hierarchical variant structure. For example, "Headache" has 14 variant dimensions:

```
Headache (root)
├── location: frontal, temporal, occipital, vertex, ...
├── severity: mild, moderate, severe
├── onset: sudden, gradual
├── pain_type: sharp/stabbing, dull/aching, throbbing, ...
├── duration_since: <1 day, 1-3 days, 1-3 weeks, ...
├── aggravated: by light, by noise, by movement, ...
├── relieved: by medication, by rest, by dark room, ...
├── characteristic: with aura, thunderclap, ...
├── temporal_pattern: constant, intermittent, ...
└── ...
```

Each variant option is a distinct symptom UUID with its own edges to conditions, enabling fine-grained differential diagnosis.

### Likelihood Scales

All likelihoods use a 6-level ordinal scale:

| Level | Score |
|-------|-------|
| very_high | 0.80 |
| high | 0.65 |
| medium | 0.50 |
| low | 0.35 |
| rare | 0.20 |
| zero | 0.00 |

---

## How the Algorithm Works

### Stage 1: Symptom Expansion

Given a chief complaint (e.g., "Nasal congestion"):
1. Find all symptom variants under that root (e.g., 11 variants for nasal congestion)
2. Find all conditions connected via PRESENT_IN edges (e.g., 22 conditions)
3. Discover other root symptoms connected to those conditions (e.g., 279 discovered roots like Fever, Headache, Fatigue)
4. Rank discovered symptoms by total P(C|S) relevance to the condition pool

### Stage 2: Questioning (4 phases)

| Phase | Questions | Purpose |
|-------|-----------|---------|
| **Phase 1: Variant Follow-Ups** | Top 3 variant questions for the chief complaint | Drill into the starting symptom (location, severity, duration) |
| **Phase 2: Prerequisite Pre-Screen** | Top 3 prerequisite questions | Eliminate conditions requiring absent preconditions (pregnancy, trauma, diabetes) |
| **Phase 3: Main Loop** | Scored discovered symptoms + remaining variants | Ask the most diagnostically valuable question each round |
| **Phase 4: Adaptive** | Up to 2 extra questions | Refine when the main budget is exhausted |

### Elimination Rules

- **YES-side**: When a symptom is confirmed, eliminate all conditions NOT connected to ANY confirmed symptom
- **NO-side**: When a symptom is denied, eliminate conditions where P(S|C) is very_high or high (configurable), unless protected
- **Protection**: Conditions with P(C|S) = high or very_high get a protection counter (0.2 per hit, threshold 0.6). they need 3 strikes before elimination
- **Triage protection** (optional): Emergency-triage conditions get extra protection against elimination
- **Prerequisite elimination**: When a patient says NO to a prerequisite (e.g., "not pregnant"), conditions requiring it with high/very_high strength are eliminated

### Ranking Formula

```
final_score = (yn_points + pcs_score) * P(C) * age_weight * gender_weight
```

| Component | Description |
|-----------|-------------|
| `yn_points` | Accumulated ±1/nom. of symptoms connected to that condition per YES/NO answer, weighted by P(C\|S) and normalized by root count |
| `pcs_score` | Sum of P(C\|S) scores for all confirmed symptom UUIDs connected to this condition |
| `P(C)` | Overall condition prevalence (0.2 for rare -> 1.0 for very_high) |
| `age_weight` | Demographic fit for the patient's age bracket (0.0 -> 1.0) |
| `gender_weight` | Demographic fit for the patient's gender (0.0 -> 1.0) |

The multiplicative formula ensures age/gender-inappropriate conditions are strongly suppressed (e.g., Croup in a 25-year-old gets 0.10x, pregnancy conditions in males get 0.0x).

### Specialities

Every ranked condition is labelled with the medical speciality that treats it, resolved from the `TREATED_BY` edges:

1. Take all `TREATED_BY` edges for the condition and score each `weight` on the standard ordinal scale (`very_high` 0.80 -> `rare` 0.20)
2. Pick the highest-weighted speciality. Ties are broken alphabetically
3. Conditions with no `TREATED_BY` edge render as `-`

The speciality appears in three places: as a badge on each condition card, as a grouped **Specialities** list (top-5 conditions grouped by speciality, expand one to see its conditions), and in the Clinical Summary.

**Known limitations of the current mapping:**

- The `weight` column barely discriminates: 541 of 567 conditions have a `very_high` top weight, so it effectively means *"this speciality treats it"* rather than *"this is the primary speciality"*.
- **186 of 567 conditions (33%) are tied at the top weight**, and the tie is broken *alphabetically*, which is clinically arbitrary. For example, condition `368009` lists Cardiologist, Paediatrician and Internal medicine specialist all at `very_high`, and resolves to Cardiologist purely because "C" < "I" < "P".
- Only 567 of 779 conditions have a speciality, but the missing 212 are almost entirely non-diagnosable nodes (risk factors, family history, lifestyle: e.g. *"Athlete"*, *"exposure to air pollution"*). Of the 555 conditions actually reachable from symptoms, **553 have a speciality**, so `-` is rare in practice.

---

## Notebook Versions (v4 -> v8)

The algorithm has been iteratively developed across notebook versions. Each version is a self-contained implementation of the full pipeline (data loading, expansion, questioning, elimination, ranking).

### v4 - Baseline

The foundational version establishing the core three-function architecture:
1. **Symptom Expansion**: Finds variants, conditions, and discovered symptoms
2. **Ask Questions**: Scores and asks up to 10 questions from a pool of variant + discovered symptom questions
3. **Rank Conditions**: Scores surviving conditions using `yn_points + pcs + age_weight + gender_weight` (pure addition)

**Limitations**: No variant follow-ups for discovered symptoms, no prerequisite screening, flat +1/-0.2 points regardless of diagnostic strength, additive demographics easily overridden by yn_points.

### v6 - Weighted Points + Hybrid Ranking

v6 introduced two major algorithmic changes:

**1. Weighted Y/N Points**
- YES points: `+1.0 * P(C|S)` instead of flat +1.0. Conditions with higher diagnostic specificity get more credit.
- NO points: `-0.2 * P(S|C)` instead of flat -0.2. Conditions where the denied symptom is more expected get penalized more.

**2. Hybrid Ranking Formula**
- Changed from `yn + pcs + age + gender` (pure addition) to `(yn + pcs) * P(C) * age * gender` (multiply by priors).
- Demographics became multiplicative: age_weight=0.10 for a 25-year-old with Croup now applies as 0.10x (devastating) instead of +0.10 (negligible).
- Condition prevalence P(C) became a multiplier: rare conditions (P(C)=0.2) are suppressed 5x vs very common ones.

**3. Improved Prerequisite Scoring**
- Score = `sum(strength * P(C) * 1/(CF_count+1))` instead of simple condition count.
- Prerequisites for hard-to-reach conditions (fewer chief complaint symptoms) are prioritized.

**Results vs v5** (73 test scenarios):
- Acute Rhinitis Top-1: 27.6% -> **62.1%** (+34.5pp). fixed the Croup-beats-Rhinitis bug
- GERD Top-1: 37.9% -> **44.8%** (+6.9pp). fixed the Barrett's-beats-GERD bug
- Tension Headache Top-1: 60.0% -> **53.3%** (-6.7pp). slight regression for children (age=0.10 as multiplier too aggressive)

### v7 - Weighted Discovered-Symptom Points

v7 ("wd" = weighted discovered) refined how YES/NO points are calculated specifically for **discovered root symptoms** and their variant follow-ups:

**Key Changes from v6:**

1. **Root-count normalization**: Y/N points are divided by the number of distinct root symptoms connected to each condition (`1/root_count`). This prevents conditions connected to many symptoms from accumulating disproportionate points. a condition linked to 15 root symptoms gets `+1/15 ≈ 0.067` per YES, while one linked to 3 roots gets `+1/3 ≈ 0.33`.

2. **Variant follow-up point weighting**: When a variant is confirmed (e.g., "headache located in frontal region"), the points are weighted by both P(C|S) and normalized by root count, replacing the flat +1.0 per connected condition from v6.

3. **Prerequisite CF-mode**: Added `prerequisite_cf_mode: 'dynamic'` which recalculates prerequisite relevance based on the symptoms confirmed so far (not just the static condition pool).

4. **Red flag screening system**: Added a post-questioning phase that checks for alarm symptoms (high fever, dysphagia, blood in vomit, neurological signs) and triggers targeted screening questions for conditions in the top-5 ranking.

5. **Question budget system**: Replaced the single `max_questions` limit with a structured budget: `base_max` (9), `adaptive_max` (2), `screening_max` (2), `global_max` (13). The budget mode (`full`, `no_adaptive`, `base_only`) controls which phases are active.

6. **Assessment presets**: Three presets. Standard (14 Qs), Safety-first (18 Qs, triage protection ON), Quick screen (6 Qs, no extras).

**This is the version deployed in the Streamlit web app and CLI agent.**

### v8. Experimental Improvements

v8 is an experimental iteration exploring further refinements:

1. **Improved initial condition scoring**: The root symptom auto-confirmation step uses P(C|S)-weighted point assignment (not flat +1), giving conditions with stronger diagnostic links to the chief complaint a head start.

2. **Refined prerequisite questioning**: Prerequisites can be delayed until after N discovered questions (`prerequisite_after_n_discovered`), allowing the pool to narrow organically before screening for preconditions. The dynamic CF-mode recalculates prerequisite relevance with each confirmed symptom.

3. **Enhanced variant follow-up scoring**: Variant questions are scored using `compute_question_value()` against the live candidate pool, ensuring that only diagnostically relevant variants are asked as the pool changes.

4. **Tighter protection thresholds**: Protection threshold raised to 0.6 (from 0.4 in earlier versions), requiring 3 strikes before eliminating a protected condition. more resilient to noisy patient answers.

5. **Score threshold early stopping**: When any condition reaches a configurable score threshold (default: 5), the questioning can stop early, preventing over-questioning when the diagnosis is already clear.

### Version Comparison Summary

| Feature | v4 | v6 | v7 | v8 |
|---------|----|----|----|----|
| Y/N point weighting | Flat +1/-0.2 | P(C\|S)-weighted | P(C\|S)-weighted + root-count normalized | P(C\|S)-weighted + root-count normalized |
| Ranking formula | `yn + pcs + age + gender` | `(yn + pcs) * P(C) * age * gender` | `(yn + pcs) * P(C) * age * gender` | `(yn + pcs) * P(C) * age * gender` |
| Variant follow-ups | Starting only | Starting + discovered | Starting + discovered | Starting + discovered |
| Prerequisite screening | None | Pre-screen (static) | Pre-screen (dynamic CF-mode) | Pre-screen (delayed + dynamic) |
| Red flag screening | None | None | Post-questioning screening | Post-questioning screening |
| Question budget | Single max | Single max | Structured (base + adaptive + screening) | Structured (base + adaptive + screening) |
| Protection threshold | 0.4 | 0.4 | 0.6 | 0.6 |
| Presets | None | None | Standard / Safety-first / Quick screen | Standard / Safety-first / Quick screen |

---

## Streamlit Web App

The `streamlit/` directory contains a full web application with:

- **Chat-based UI**: Conversational interface powered by Azure OpenAI (GPT-4o). The LLM rephrases medical questions into patient-friendly language and interprets free-text answers.
- **General intake questions**: Collects age, gender, weight, and other demographics before symptom intake. Questions are driven by an Excel file with conditional branching logic.
- **LLM-powered symptom matching**: Patient descriptions are matched to BODHI root symptoms using an LLM with the full symptom lookup CSV as context.
- **Multi-symptom support**: When multiple symptoms are mentioned, the one with the most condition connections is used as the chief complaint; others are auto-confirmed during questioning.
- **Live questioning**: Questions are rendered as chat messages with progress indicators. Variant questions show option lists; discovered/prerequisite questions are yes/no.
- **Results page**: Split into two tabs.
  - **Clinical Summary** (doctor-facing): patient age/gender/chief complaint, the suggested specialities, the question-and-answer history, and the suggested differential with triage and speciality. Deliberately shows **no engine internals** (no scores, no pool sizes, no network graph), and is labelled as decision support, not a diagnosis.
  - **Engine Detail** (debug): condition cards with triage badges and speciality, score breakdowns (Y/N, P(C|S), P(C), age, gender), the specialities list, the symptom-condition network, question logs, and scoring detail tables.
- **Doctor authentication**: Token-based auth via Supabase. Doctors register with name/email; sessions are logged to the database.
- **Session logging**: All questions, answers, results, and evaluations are logged to Supabase for analysis.
- **Evaluation form**: After each assessment, the doctor rates the intended diagnosis rank and provides feedback.
- **Admin sidebar**: PIN-protected configuration panel with preset selection and advanced settings (question budget, protection, variant follow-ups, prerequisite mode).

### Running the Web App

```bash
cd streamlit
pip install -r requirements.txt
streamlit run app.py
```

Requires:
- Azure OpenAI API credentials in `agent/.env`
- Supabase credentials in `streamlit/.streamlit/secrets.toml` (optional. runs in local mode without it)

---

## CLI Agent

The `agent/` directory contains a terminal-based agent that wraps the same diagnostic engine with an LLM conversation layer:

- Uses Azure OpenAI (GPT-4o) to present questions naturally and parse free-text responses
- Logs each session to an Excel file for offline review
- Supports the full pipeline: intake parsing -> symptom expansion -> multi-phase questioning -> ranking -> LLM-generated result summary

### Running the CLI Agent

```bash
cd agent
pip install -r requirements.txt
python agent.py
```

---

## Data Formats

The knowledge graph is available in multiple formats:

| Format | Path | Use Case |
|--------|------|----------|
| **CSV** | `csv/` | Primary format used by the engine. 8 files (nodes + edges) |
| **Neo4j Cypher** | `neo4j/bodhi_s.cypher` | Import script for Neo4j graph database |
| **RDF/Turtle** | `rdf/bodhi.ttl` | Semantic web format with SNOMED-CT URIs |
| **JSONL** | `jsonl/triples.jsonl`, `jsonl/nl_facts.jsonl` | Triple format and natural language facts |
| **PyTorch Geometric** | `pyg/bodhi.pt` | Graph neural network-ready tensor format |

---

## Project Structure

```
bodhi-s/
├── csv/                          # Knowledge graph data (CSV)
│   ├── nodes_symptom.csv         # 4,037 symptoms with variants
│   ├── nodes_condition.csv       # 779 conditions with demographics
│   ├── nodes_speciality.csv      # 39 medical specialities
│   ├── edges_present_in.csv      # 10,352 symptom->condition edges
│   ├── edges_has_prerequisite.csv # 53 prerequisite relationships
│   ├── edges_related_to.csv      # 221 condition associations
│   ├── edges_treated_by.csv      # 1,558 treatment edges
│   └── edges_is_influenced_by.csv # 1,020 risk factor edges
├── notebooks/                    # Algorithm development notebooks
│   ├── bodhi_symptom_checker_v4.ipynb   # Baseline algorithm
│   ├── bodhi_symptom_checker_v6.ipynb   # Weighted points + hybrid ranking
│   ├── bodhi_symptom_checker_v7_wd.ipynb # Root-count normalization + red flags
│   ├── bodhi_symptom_checker_v8.ipynb   # Experimental refinements
│   └── test_case_analysis_bodhi.ipynb   # Test case analysis
├── streamlit/                    # Web application
│   ├── app.py                    # Main Streamlit entry point
│   ├── engine/                   # Core algorithm modules
│   │   ├── config.py             # All configuration constants
│   │   ├── data_loader.py        # CSV loading + caching
│   │   ├── expansion.py          # Stage 1: Symptom expansion
│   │   ├── elimination.py        # Elimination, question scoring, variant/prereq builders
│   │   ├── questioning.py        # Stage 2: Multi-phase questioning engine
│   │   ├── ranking.py            # Stage 3: Condition ranking
│   │   └── presets.py            # Assessment presets (Standard/Safety-first/Quick)
│   ├── ui/                       # Streamlit UI components
│   │   ├── chat.py               # Main chat interface + LLM integration
│   │   ├── auth.py               # Doctor authentication
│   │   ├── components.py         # Condition cards, triage badges
│   │   ├── intake.py             # (Legacy) intake UI
│   │   ├── questioning.py        # (Legacy) questioning UI
│   │   └── results.py            # (Legacy) results UI
│   ├── prompts/                  # LLM prompt templates
│   │   ├── intake_conversation.txt # Intake parsing prompt
│   │   └── rephrase_question.txt   # Question rephrasing prompt
│   ├── db/                       # Database layer
│   │   ├── supabase_client.py    # Supabase connection
│   │   └── models.py             # DB operations (sessions, questions, results, evaluations)
│   └── requirements.txt
├── agent/                        # CLI agent
│   ├── agent.py                  # Main agent loop
│   ├── qa_state.py               # Session state + Excel logging
│   ├── prompts/                  # Agent LLM prompts
│   │   ├── system_prompt.txt     # System prompt for conversation
│   │   ├── intake_parsing.txt    # Intake parsing prompt
│   │   └── questioning.txt       # Answer mapping prompt
│   ├── tools/diagnostic/         # Engine modules (mirrored from streamlit/engine)
│   ├── data/                     # Agent-local data copy
│   └── requirements.txt
├── docs/                         # Evaluation reports
│   ├── bodhi_v5_changes.md       # v5 changelog (variant follow-ups + prerequisites)
│   ├── v5_evaluation_report.md   # v5 test results (73 scenarios)
│   ├── v6_evaluation_report.md   # v6 test results (73 scenarios)
│   ├── bodhi_v4_handover.docx    # v4 handover documentation
│   └── bodhi_v4_test_report.docx # v4 test report
├── neo4j/                        # Neo4j export
├── rdf/                          # RDF/Turtle export
├── jsonl/                        # JSONL triple export
├── pyg/                          # PyTorch Geometric export
└── README.md
```

---

## Configuration

All algorithm parameters are in `streamlit/engine/config.py`. Key settings:

### Elimination

| Parameter | Default | Description |
|-----------|---------|-------------|
| `yes_eliminate_unconnected` | `True` | Remove conditions not connected to any confirmed symptom |
| `no_eliminate_psc_levels` | `[very_high, high]` | P(S\|C) levels that trigger NO-side elimination |
| `protection_enabled` | `True` | Protect conditions with high P(C\|S) from immediate elimination |
| `protection_threshold` | `0.6` | Counter value needed to eliminate a protected condition |
| `triage_protection` | `False` | Extra protection for emergency-triage conditions |

### Questioning

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_questions` | `9` | Base question limit (before adaptive/screening) |
| `variant_followup_enabled` | `True` | Ask variant follow-ups when a symptom is confirmed |
| `max_variant_followups` | `3` | Max variant questions per confirmed symptom |
| `prerequisite_mode` | `pre_screen` | When to ask prerequisites: `off`, `pre_screen`, `integrated`, `both` |
| `question_scoring_method` | `normalized_symptom_score` | How to score question value: `normalized_symptom_score` or `ev` |

### Question Budget

| Parameter | Default | Description |
|-----------|---------|-------------|
| `mode` | `full` | Budget mode: `full` (adaptive + screening), `no_adaptive`, `base_only` |
| `global_max` | `13` | Hard ceiling across all question phases |
| `adaptive_max` | `2` | Extra questions after base budget |
| `screening_max` | `2` | Screening questions. Currently unused. no slots are reserved |

### Ranking

| Parameter | Default | Description |
|-----------|---------|-------------|
| `yes_point` | `1.0` | Base points for YES answer (multiplied by P(C\|S) and 1/root_count) |
| `no_point` | `-0.2` | Base points for NO answer |
| `demographic_method` | `addition` | Formula type: uses hybrid `(yn+pcs)*P(C)*age*gender` |

### Assessment Presets

| Preset | Max Qs | Triage Protection | Prerequisite Mode | Use Case |
|--------|--------|-------------------|-------------------|----------|
| **Standard** | 14 | Off | Pre-screen | Balanced assessment |
| **Safety-first** | 18 | On | Pre-screen | Thorough with triage protection |
| **Quick screen** | 6 | Off | Off | Fast triage |

---

## Setup

### Prerequisites

- Python 3.11+
- Azure OpenAI API access (for LLM-powered interfaces)
- Supabase account (optional, for session logging)

### Environment Variables

Create `agent/.env`:
```
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT1=gpt-4o
```

### Database (Optional)

Create `streamlit/.streamlit/secrets.toml`:
```toml
[supabase]
url = "your_supabase_url"
key = "your_supabase_anon_key"

[admin]
pin = "your_admin_pin"
```

The app runs in local mode (no auth, no logging) when Supabase is not configured.
