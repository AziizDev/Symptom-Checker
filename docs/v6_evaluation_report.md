# BODHI Symptom Checker v6 — Evaluation Report

**Date:** 2026-06-09  
**Evaluator:** Automated Test Harness (v6_evaluation_harness.py)  
**Data:** 4,037 symptoms | 10,352 edges | 779 conditions  
**Scenarios Executed:** 73  
**Conditions Tested:** Acute Rhinitis (82272006), GERD (235595009), Tension Headache (398057008)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [v5 vs v6 Algorithm Changes](#2-v5-vs-v6-algorithm-changes)
3. [Test Methodology](#3-test-methodology)
4. [Default Configuration Tested](#4-default-configuration-tested)
5. [Condition 1: Acute Rhinitis](#5-condition-1-acute-rhinitis)
6. [Condition 2: GERD](#6-condition-2-gerd)
7. [Condition 3: Tension Headache](#7-condition-3-tension-headache)
8. [Cross-Condition Analysis](#8-cross-condition-analysis)
9. [Configuration Variation Results](#9-configuration-variation-results)
10. [Unrelated Chief Complaint Tests](#10-unrelated-chief-complaint-tests)
11. [v5 vs v6 Head-to-Head Comparison](#11-v5-vs-v6-head-to-head-comparison)
12. [Findings and Recommendations](#12-findings-and-recommendations)

---

## 1. Executive Summary

### Aggregate Results (All 73 Scenarios)

| Condition | Scenarios | Survived | Eliminated | Top-1 | Top-3 | Top-5 |
|-----------|-----------|----------|------------|-------|-------|-------|
| Acute Rhinitis | 29 | 93.1% | 6.9% | **62.1%** | 72.4% | 82.8% |
| GERD | 29 | 82.8% | 17.2% | **44.8%** | 79.3% | 79.3% |
| Tension Headache | 15 | 73.3% | 26.7% | **53.3%** | 60.0% | 66.7% |

### v5 vs v6 Comparison at a Glance

| Metric | v5 | v6 | Delta |
|--------|----|----|-------|
| **Acute Rhinitis Top-1** | 27.6% | **62.1%** | **+34.5pp** |
| Acute Rhinitis Top-3 | 65.5% | 72.4% | +6.9pp |
| Acute Rhinitis Top-5 | 69.0% | 82.8% | +13.8pp |
| **GERD Top-1** | 37.9% | **44.8%** | **+6.9pp** |
| GERD Top-3 | 79.3% | 79.3% | 0pp |
| GERD Top-5 | 79.3% | 79.3% | 0pp |
| **Tension Headache Top-1** | 60.0% | **53.3%** | **-6.7pp** |
| Tension Headache Top-3 | 66.7% | 60.0% | -6.7pp |
| Tension Headache Top-5 | 66.7% | 66.7% | 0pp |

### Key Takeaways

1. **v6's weighted Y/N points + hybrid ranking formula dramatically improve Acute Rhinitis.** The Croup-beats-Rhinitis bug from v5 is fixed: Croup's age_weight=0.10 for adults now multiplicatively suppresses its score (0.10x vs v5's additive +0.10). Acute Rhinitis jumps from 27.6% Top-1 to 62.1%.

2. **GERD moderately improves.** Barrett's oesophagus no longer beats GERD for 25M (Barrett's age_weight=0.25 is now a 0.25x multiplier instead of +0.25). GERD moves from 37.9% to 44.8% Top-1.

3. **Tension Headache slightly regresses** (-6.7pp Top-1). The multiplicative P(C) weight (0.8 for "high" prevalence) reduces Tension Headache's absolute score compared to v5's additive formula. For the 10M demographic, Tension Headache drops from Rank #1 to Rank #5 because age_weight=0.10 is now a multiplier.

4. **Demographics now have real impact.** The multiplicative formula means age_weight=0.0 zeroes out a condition's score entirely. This is medically more appropriate (age-impossible conditions get 0) but can be harsh for borderline cases.

5. **Elimination behavior is identical** to v5 — survival/elimination rates are the same across all 73 scenarios. The elimination engine was not changed.

6. **Unrelated chief complaints still correctly eliminate** the target in all 6 unrelated-CF scenarios.

---

## 2. v5 vs v6 Algorithm Changes

### Change 1: Weighted Y/N Points

| Component | v5 | v6 |
|-----------|----|----|
| Root YES | `+1.0` (flat) per connected condition | `+1.0 * P(C\|S)` per connected condition |
| Discovered/Variant YES | `+1.0` (flat) per connected condition | `+1.0 * P(C\|S)` per connected condition |
| Discovered/Variant NO | `-0.2` (flat) per connected condition | `-0.2 * P(S\|C)` per connected condition |
| Prerequisite YES/NO | `+1.0` / `-0.2` (flat) | `+1.0` / `-0.2` (flat, unchanged) |

**Impact:** Conditions with higher diagnostic specificity (P(C|S)) get more YES points. A condition with P(C|S)=very_high (1.0) gets +1.0 per YES, while one with P(C|S)=low (0.4) gets only +0.4. This makes yn_points diagnostic-strength-aware.

### Change 2: Ranking Formula (addition mode)

| | v5 | v6 |
|--|----|----|
| **Formula** | `yn + pcs + age_weight + gender_weight` | `(yn + pcs) * P(C) * age_weight * gender_weight` |
| **Nature** | Pure addition | Hybrid: add evidence, multiply by priors |
| **Demographics** | Additive (+0 to +1.0 each) | Multiplicative (0x to 1x each) |
| **P(C)** | Not used in ranking | Multiplier (0.2 for rare to 1.0 for very_high) |

**Impact:** Age-inappropriate conditions (age_weight=0.0) get zeroed out entirely. Rare conditions (P(C)=0.2) are suppressed 5x vs very common ones (P(C)=1.0). This is the single biggest change in v6.

### Change 3: Prerequisite Scoring

| | v5 | v6 |
|--|----|----|
| **Score** | `num_affected` (count of conditions) | `sum(strength * P(C) * 1/(CF_count+1))` |
| **Ranking** | By count (more conditions = higher priority) | By diagnostic value (weight by prevalence and symptom visibility) |

**Impact:** Prerequisites for conditions with fewer chief complaint symptoms (hard-to-reach conditions) are prioritized. Minimal impact on the 3 tested conditions.

---

## 3. Test Methodology

### Answer Strategies

| Strategy | Description | Purpose |
|----------|-------------|---------|
| **connected** | YES to symptoms connected to target, pick matching variant options, NO to unconnected. | Simulates an "ideal patient" who has the condition. |
| **all_yes** | YES to everything, pick first variant option. | Stress test: does over-confirmation dilute ranking? |
| **all_no** | NO to everything, skip all variants. | Stress test: how aggressive is elimination? |
| **mixed_30pct** | Connected strategy with 30% random noise (seeded). | Simulates realistic uncertain patient. |
| **unrelated_cf** | Start with unrelated chief complaint. YES to connected symptoms if discovered. | Tests recovery from wrong starting symptom. |

### Chief Complaints Tested Per Condition

| Condition | Primary CF | Secondary CFs | Unrelated CFs |
|-----------|-----------|---------------|---------------|
| Acute Rhinitis | Nasal congestion | Sneezing, Fever | Headache, Abdominal pain |
| GERD | Heartburn | Regurgitation, Abdominal pain | Headache, Nasal congestion |
| Tension Headache | Headache | (only 1 root symptom) | Nasal congestion, Abdominal pain |

### Demographics Tested

| Profile | Age | Gender | Notes |
|---------|-----|--------|-------|
| Young adult male | 25 | M | Baseline |
| Middle-aged female | 40 | F | Cross-gender |
| Child | 10 | M | Tests age-bracket (6-12) |
| Elderly female | 65 | F | Tests 60+ bracket |

---

## 4. Default Configuration Tested

```
Elimination:
  yes_eliminate_unconnected: True
  no_eliminate_psc_levels: [very_high, high]
  protection_enabled: True (P(C|S) high/very_high)
  protection_increment: 0.2, threshold: 0.4

Ranking:
  yes_point: +1.0 (* P(C|S) for symptom Qs, flat for prerequisites)
  no_point: -0.2 (* P(S|C) for symptom Qs, flat for prerequisites)
  demographic_method: addition
  FORMULA: (yn_points + pcs_score) * P(C) * age_weight * gender_weight

Questioning:
  max_questions: 10, top_n_discovered: 20
  min_pool_size: 3, score_threshold: 10
  question_scoring: normalized_symptom_score
  variant_followup: ON (max 3)
  prerequisite_mode: pre_screen (max 3)
```

---

## 5. Condition 1: Acute Rhinitis

**SNOMED:** 82272006  
**Type:** acute | **Triage:** opd_managed | **Overall Likelihood:** very_high (P(C)=1.0)

### Baseline Results (connected strategy, default config)

| Chief Complaint | 25M | 40F | 10M | 65F |
|----------------|-----|-----|-----|-----|
| Nasal congestion | **Rank #1** (5.20) | **Rank #1** (5.20) | **Rank #1** (5.20) | **Rank #1** (5.20) |
| Sneezing | **Rank #1** (4.80) | **Rank #1** (4.80) | **Rank #1** (4.80) | **Rank #1** (4.80) |
| Fever | Rank #4 (1.20) | Rank #4 (1.20) | Rank #5 (1.20) | Rank #6 (1.20) |

**vs v5:**
- Nasal congestion: v5 Rank #2 → **v6 Rank #1** (fixed!)
- Sneezing: Rank #1 → Rank #1 (unchanged)
- Fever: Rank #18 → Rank #4 (improved from #18!)

### Detailed Question Log: Nasal Congestion, connected, 25M

```
Pool: 22 -> 13 surviving | 10 questions asked
Confirmed: 9 symptoms | Denied: 8

Q 1 [follow-up variant] Nasal congestion — duration    => Selected: <3 days, 3-7 days    | pool:22 | target:IN_POOL
Q 2 [follow-up variant] Nasal congestion — laterality   => Selected: unilateral            | pool:22 | target:IN_POOL
Q 3 [follow-up variant] Nasal congestion — aggravated   => Selected: nasal decongestant    | pool:22 | target:IN_POOL
Q 4 [prerequisite]      Nasal decongestants usage        => NO                             | pool:21 | target:IN_POOL
Q 5 [discovered]        Fever                            => YES                            | pool:21 | target:IN_POOL
Q 6 [follow-up variant] Fever — characteristic           => Selected: with chills/rigors   | pool:21 | target:IN_POOL
Q 7 [follow-up variant] Fever — relieved                 => Selected: by medication        | pool:21 | target:IN_POOL
Q 8 [follow-up variant] Fever — severity                 => Selected: mild                 | pool:21 | target:IN_POOL
Q 9 [discovered]        Fatigue                          => NO                             | pool:20 | target:IN_POOL
Q10 [discovered]        Headache                         => NO                             | pool:13 | target:IN_POOL

FINAL TOP 5:
  #1: Acute rhinitis                    score=5.20 (yn=+2.20, pcs=3.00, pc=1.00, age=1.00, gen=1.00) <<<
  #2: Upper respiratory infection       score=4.32 (yn=+2.12, pcs=2.20, pc=1.00, age=1.00, gen=1.00)
  #3: Rhinosporidiosis                  score=0.80 (yn=+1.00, pcs=1.00, pc=0.40, age=1.00, gen=1.00)
  #4: Vasomotor Rhinitis                score=0.72 (yn=+0.60, pcs=0.60, pc=0.60, age=1.00, gen=1.00)
  #5: Facial bones fracture             score=0.64 (yn=+0.80, pcs=0.80, pc=0.40, age=1.00, gen=1.00)
```

**Why v6 Rank #1 (fixed from v5 Rank #2):**
- v5: Croup scored 8.10 (yn=+5.0, pcs=2.0, age=0.10, gen=1.00) beating Rhinitis at 8.00 — the flat +5.0 yn_points overcame Croup's terrible age fit
- v6: Croup is no longer in Top 5. Its score is suppressed by `P(C)=0.6 * age=0.10 = 0.06x` multiplier. Even with high yn_points, the multiplicative penalty kills it.
- Acute Rhinitis benefits from `P(C)=1.0 * age=1.0 = 1.0x` — no penalty at all.

### Strategy Comparison (Nasal Congestion, 25M)

| Strategy | v6 Result | v6 Score | v5 Result | Pool | Questions |
|----------|-----------|----------|-----------|------|-----------|
| connected | **Rank #1** | 5.20 | Rank #2 | 22->13 | 10 |
| all_yes | Rank #2 | 4.40 | Rank #6 | 22->22 | 10 |
| all_no | **Rank #1** | 1.36 | Rank #1 | 22->9 | 10 |
| mixed_30pct | **Rank #1** | 5.20 | Rank #5 | 22->20 | 10 |

**Notable improvements:** Connected moved from #2 to #1. mixed_30pct moved from #5 to #1. The weighted formula is much more robust to noise.

---

## 6. Condition 2: GERD

**SNOMED:** 235595009  
**Type:** chronic_with_acute_aggravation | **Triage:** opd_managed | **Overall Likelihood:** high (P(C)=0.8)

### Baseline Results (connected strategy, default config)

| Chief Complaint | 25M | 40F | 10M | 65F |
|----------------|-----|-----|-----|-----|
| Heartburn | **Rank #1** (6.56) | Rank #2 (6.56) | **Rank #1** (1.64) | Rank #2 (4.92) |
| Regurgitation | **Rank #1** (11.68) | **Rank #1** (11.68) | **Rank #1** (2.92) | **Rank #1** (8.76) |
| Abdominal pain | Rank #2 (3.36) | Rank #2 (3.36) | **Rank #1** (0.84) | Rank #3 (2.52) |

**vs v5:**
- Heartburn 25M: v5 Rank #2 → **v6 Rank #1** (fixed!)
- Heartburn 40F: Rank #2 → Rank #2 (same — Gastritis wins at 40F)
- Regurgitation: Rank #1 → Rank #1 (unchanged, already perfect)
- Abdominal pain: Rank #1 → Rank #2 (slight regression — Gastritis has P(C)=1.0 vs GERD's 0.8)

### Detailed Question Log: Heartburn, connected, 25M

```
Pool: 9 -> 9 surviving (NO elimination) | 10 questions asked
Confirmed: 12 symptoms | Denied: 23

Q 1 [follow-up variant] Heartburn — duration_since    => Selected: >1 month               | pool:9
Q 2 [follow-up variant] Heartburn — aggravated        => Selected: after caffeine          | pool:9
Q 3 [follow-up variant] Heartburn — relieved           => Selected: by antacid             | pool:9
Q 4 [discovered]        Vomit                          => YES                              | pool:9
Q 5 [follow-up variant] Vomit — characteristic         => Selected: bloody in vomit        | pool:9
Q 6 [follow-up variant] Vomit — aggravated             => Selected: on food intake         | pool:9
Q 7 [follow-up variant] Vomit — duration_since         => Selected: <1 day                 | pool:9
Q 8 [discovered]        Abdominal pain                 => YES                              | pool:9
Q 9 [follow-up variant] Abdominal pain — location      => Selected: upper abdomen, epigastric | pool:9
Q10 [follow-up variant] Abdominal pain — severity      => Selected: mild                   | pool:9

FINAL TOP 5:
  #1: GERD                       score=6.56 (yn=+3.00, pcs=5.20, pc=0.80, age=1.00, gen=1.00) <<<
  #2: Gastritis                  score=6.48 (yn=+2.80, pcs=4.40, pc=1.00, age=0.90, gen=1.00)
  #3: Gastric ulcer              score=2.40 (yn=+3.00, pcs=5.00, pc=0.60, age=0.50, gen=1.00)
  #4: Irritable bowel syndrome   score=1.32 (yn=+1.40, pcs=0.80, pc=0.60, age=1.00, gen=1.00)
  #5: Hiatus hernia              score=1.20 (yn=+2.00, pcs=2.00, pc=0.40, age=0.75, gen=1.00)
```

**Why v6 Rank #1 (fixed from v5 Rank #2):**
- v5: Barrett's oesophagus scored 12.85 (yn=+7.0, pcs=4.60, age=0.25, gen=1.00) beating GERD at 12.20
- v6: Barrett's drops out of Top 5 entirely. Its P(C)=0.4 (rare) and age=0.25 multiply to 0.10x, collapsing its score despite high yn_points.
- GERD's P(C)=0.8 and age=1.0 give it a 0.80x multiplier — much stronger.
- **New competitor:** Gastritis (P(C)=1.0, age=0.90) is now the closest rival at score 6.48 vs GERD's 6.56. The margin is just 0.08 points.

### Why GERD loses to Gastritis for 40F and 65F

For the 40F demographic, Gastritis scores 7.20 vs GERD's 6.56:
- Gastritis: `(2.80 + 4.40) * 1.0 * 1.0 * 1.0 = 7.20` (P(C)=1.0 very_high, age=1.0)
- GERD: `(3.00 + 5.20) * 0.8 * 1.0 * 1.0 = 6.56` (P(C)=0.8 high)
- GERD has higher evidence (8.20 vs 7.20) but its `P(C)=0.8` multiplier reduces it below Gastritis's `P(C)=1.0`.

### Strategy Comparison (Heartburn, 25M)

| Strategy | v6 Result | v6 Score | v5 Result | Pool | Questions |
|----------|-----------|----------|-----------|------|-----------|
| connected | **Rank #1** | 6.56 | Rank #2 | 9->9 | 10 |
| all_yes | Rank #2 | 4.80 | Rank #2 | 9->9 | 10 |
| all_no | **ELIMINATED** | - | ELIMINATED | 9->3 | 5 |
| mixed_30pct | **Rank #1** | 6.56 | Rank #2 | 9->9 | 10 |

**Notable:** mixed_30pct improved from Rank #2 to Rank #1. The v6 formula is more robust to noise for GERD.

---

## 7. Condition 3: Tension Headache

**SNOMED:** 398057008  
**Type:** chronic_with_acute_aggravation | **Triage:** opd_managed | **Overall Likelihood:** high (P(C)=0.8)

### Baseline Results (connected strategy, default config)

| Chief Complaint | 25M | 40F | 10M | 65F |
|----------------|-----|-----|-----|-----|
| Headache | **Rank #1** (2.76) | **Rank #1** (3.31) | **Rank #5** (0.37) | **Rank #1** (2.48) |

**vs v5:**
- 25M: Rank #1 → Rank #1 (same, but score dropped from 7.55 to 2.76)
- 40F: Rank #1 → Rank #1 (same)
- **10M: Rank #1 → Rank #5 (REGRESSION)**
- 65F: Rank #1 → Rank #1 (same)

### Detailed Question Log: Headache, connected, 25M

```
Pool: 110 -> 58 surviving | 10 questions asked
Confirmed: 5 symptoms | Denied: 10

Q 1 [follow-up variant] Headache — onset           => Selected: sudden onset          | pool:109 (was 110)
Q 2 [follow-up variant] Headache — pain_type       => Selected: sharp/stabbing        | pool:109
Q 3 [follow-up variant] Headache — duration_since  => Selected: 1-3 weeks, 3-12 weeks | pool:109
Q 4 [prerequisite]      Head injury                => NO                              | pool:107
Q 5 [prerequisite]      Hypertension               => NO                              | pool:106
Q 6 [prerequisite]      Seizure                    => NO                              | pool:105
Q 7 [discovered]        Fever                      => NO                              | pool: 81
Q 8 [discovered]        Fatigue                    => NO                              | pool: 71
Q 9 [discovered]        Malaise                    => NO                              | pool: 69
Q10 [discovered]        Vomit                      => NO                              | pool: 58

FINAL TOP 5:
  #1: Tension Headache          score=2.76 (yn=+1.80, pcs=2.80, pc=0.80, age=0.75, gen=1.00) <<<
  #2: Cluster Headache          score=2.56 (yn=+1.40, pcs=1.80, pc=0.80, age=1.00, gen=1.00)
  #3: Occipital neuralgia       score=1.92 (yn=+1.40, pcs=1.80, pc=0.80, age=0.50, gen=1.00)
  #4: Myopia (disorder)         score=1.44 (yn=+0.80, pcs=1.00, pc=0.80, age=0.90, gen=1.00)
  #5: Primary Stabbing Headache score=1.36 (yn=+0.80, pcs=1.20, pc=0.80, age=0.50, gen=1.00)
```

**Why 10M drops to Rank #5:**
- Tension Headache 10M: `(1.80 + 2.80) * 0.8 * 0.10 * 1.0 = 0.368`
- Cluster Headache 10M: `(1.40 + 1.80) * 0.8 * 0.25 * 1.0 = 0.640`
- The age_weight=0.10 for 10-year-old Tension Headache (rare in children) becomes a devastating 0.10x multiplier. In v5, this was just +0.10 additive, which had minimal impact.

### Strategy Comparison (Headache, 25M)

| Strategy | v6 Result | v6 Score | v5 Result | Pool | Questions |
|----------|-----------|----------|-----------|------|-----------|
| connected | **Rank #1** | 2.76 | Rank #1 | 110->58 | 10 |
| all_yes | Rank #9 | 2.16 | Rank #11 | 110->109 | 10 |
| all_no | **ELIMINATED** | - | ELIMINATED | 110->55 | 10 |
| mixed_30pct | **ELIMINATED** | - | ELIMINATED | 110->65 | 10 |

**Same weakness as v5:** mixed_30pct (30% noise) still causes elimination. The large pool (110 conditions) + single root symptom makes Tension Headache fragile to incorrect NO answers.

---

## 8. Cross-Condition Analysis

### Score Composition Under v6 Formula

`final_score = (yn_points + pcs_score) * P(C) * age_weight * gender_weight`

| Component | Role | Typical Range | v6 Impact |
|-----------|------|--------------|-----------|
| yn_points | Evidence from YES/NO answers (now P(C\|S)-weighted) | -0.5 to +5.0 | Less dominant than v5 (weighted, not flat) |
| pcs_score | P(C\|S) sum from confirmed symptoms | 0.0 to 9.8 | Major contributor to evidence |
| P(C) | Overall condition prevalence | 0.2 to 1.0 | **NEW: multiplier, not additive** |
| age_weight | Demographic fit for age | 0.0 to 1.0 | **Changed from additive to multiplicative** |
| gender_weight | Demographic fit for gender | 0.0 to 1.0 | **Changed from additive to multiplicative** |

### What Makes v6 Better or Worse Per Condition

| Factor | Acute Rhinitis (better) | GERD (better) | Tension Headache (mixed) |
|--------|------------------------|---------------|--------------------------|
| P(C) | 1.0 (very_high) — no penalty | 0.8 (high) — mild 0.8x | 0.8 (high) — mild 0.8x |
| Key competitor P(C) | Croup: 0.6, URI: 1.0 | Gastritis: 1.0, Barrett's: 0.4 | Cluster: 0.8, Myopia: 0.8 |
| Age demographic | Always favorable | Always favorable | Kills score for children (age=0.10) |
| Weighted yn helps? | Yes — target gets higher P(C\|S) weight | Yes — GERD's P(C\|S)=very_high gives it edge | Moderate — P(C\|S)=high, same as competitors |

### Key Ranking Battles (connected, 25M)

| Battle | v5 Winner | v6 Winner | Why v6 Differs |
|--------|-----------|-----------|----------------|
| Acute Rhinitis vs Croup | Croup (#1) | **Rhinitis (#1)** | Croup's age=0.10 now 0.10x multiplier |
| GERD vs Barrett's | Barrett's (#1) | **GERD (#1)** | Barrett's P(C)=0.4 * age=0.25 = 0.10x |
| GERD vs Gastritis (40F) | Barrett's (#1) | Gastritis (#1), GERD #2 | Gastritis P(C)=1.0 > GERD P(C)=0.8 |
| Tension Headache vs Cluster | T.Headache (#1) | **T.Headache (#1)** | Both same P(C), T.Headache has better pcs |
| T.Headache vs Cluster (10M) | T.Headache (#1) | Cluster (#1), **T.Headache #5** | T.Headache age=0.10 vs Cluster age=0.25 |

---

## 9. Configuration Variation Results

### Acute Rhinitis (CF=Nasal congestion, connected, 25M)

| Config | v6 Rank | v6 Score | v5 Rank | Pool | Notes |
|--------|---------|----------|---------|------|-------|
| **default** | **#1** | **5.20** | #2 | 22->13 | **Fixed from v5** |
| protection_OFF | #1 | 5.20 | #2 | 22->13 | No change |
| max_q_5 | #1 | 5.20 | #1 | 22->21 | Same result |
| variants_OFF | #1 | 4.40 | #1 | 22->9 | Score drops but still #1 |
| rank_multiply | #1 | 6.60 | #1 | 22->13 | Higher absolute score |
| wider_no_elim | #1 | 5.20 | #2 | 22->12 | 1 more eliminated |
| no_score_threshold | #1 | 5.20 | #2 | 22->13 | No change |

**v6 achieves Rank #1 across ALL config variations.** The demographic multiplier is so effective that no config tweak changes the outcome.

### GERD (CF=Heartburn, connected, 25M)

| Config | v6 Rank | v6 Score | v5 Rank | Pool | Notes |
|--------|---------|----------|---------|------|-------|
| **default** | **#1** | **6.56** | #2 | 9->9 | **Fixed from v5** |
| protection_OFF | #1 | 6.56 | #2 | 9->9 | No change |
| max_q_5 | #2 | 3.36 | #2 | 9->9 | Fewer Qs = less evidence for GERD |
| variants_OFF | #2 | 5.12 | #2 | 9->6 | Without variant details, Gastritis wins |
| rank_multiply | #1 | 12.48 | #1 | 9->9 | Full multiplication boosts GERD further |
| wider_no_elim | #1 | 6.56 | #2 | 9->9 | No change |
| no_score_threshold | #1 | 6.56 | #2 | 9->9 | No change |

**max_q_5 and variants_OFF cause GERD to drop to #2.** GERD needs sufficient variant questions to build its yn_points advantage over Gastritis.

### Tension Headache (CF=Headache, connected, 25M)

| Config | v6 Rank | v6 Score | v5 Rank | Pool | Notes |
|--------|---------|----------|---------|------|-------|
| **default** | **#1** | **2.76** | #1 | 110->58 | Same rank, lower absolute score |
| protection_OFF | #1 | 2.76 | #1 | 110->56 | 2 more eliminated |
| max_q_5 | #2 | 2.76 | #1 | 110->106 | **Regressed**: insufficient elimination |
| variants_OFF | #1 | 0.96 | **#3** | 110->57 | **Improved from v5 #3!** |
| rank_multiply | #1 | 3.02 | #1 | 110->58 | Slight score increase |
| wider_no_elim | #1 | 2.76 | #1 | 110->36 | Much more aggressive elimination |
| no_score_threshold | #1 | 2.76 | #1 | 110->58 | No change |

**Surprising finding:** variants_OFF now achieves Rank #1 (was #3 in v5). In v5, without variants, flat yn_points let competitors accumulate equal scores. In v6, the P(C|S)-weighted points give Tension Headache a natural advantage even without variant differentiation.

---

## 10. Unrelated Chief Complaint Tests

All 6 unrelated-CF scenarios correctly ELIMINATE the target condition. Identical to v5.

| Target | Chief Complaint | Result | Pool | Questions |
|--------|----------------|--------|------|-----------|
| Acute Rhinitis | Headache | ELIMINATED | 110->89 | 10 |
| Acute Rhinitis | Abdominal pain | ELIMINATED | 79->61 | 10 |
| GERD | Headache | ELIMINATED | 110->61 | 10 |
| GERD | Nasal congestion | ELIMINATED | 22->9 | 10 |
| Tension Headache | Nasal congestion | ELIMINATED | 22->13 | 10 |
| Tension Headache | Abdominal pain | ELIMINATED | 79->43 | 10 |

---

## 11. v5 vs v6 Head-to-Head Comparison

### Every Scenario — Rank Changes

| Condition | CF | Strategy | Demo | v5 Rank | v6 Rank | Change |
|-----------|-----|---------|------|---------|---------|--------|
| Acute Rhinitis | Nasal congestion | connected | 25M | #2 | **#1** | **+1** |
| Acute Rhinitis | Nasal congestion | connected | 40F | #2 | **#1** | **+1** |
| Acute Rhinitis | Nasal congestion | connected | 10M | #2 | **#1** | **+1** |
| Acute Rhinitis | Nasal congestion | connected | 65F | #2 | **#1** | **+1** |
| Acute Rhinitis | Nasal congestion | all_yes | 25M | #6 | **#2** | **+4** |
| Acute Rhinitis | Nasal congestion | all_no | 25M | #1 | #1 | 0 |
| Acute Rhinitis | Nasal congestion | mixed_30pct | 25M | #5 | **#1** | **+4** |
| Acute Rhinitis | Sneezing | connected | all | #1 | #1 | 0 |
| Acute Rhinitis | Sneezing | mixed_30pct | 25M | ? | #2 | — |
| Acute Rhinitis | Fever | connected | 25M | #18 | **#4** | **+14** |
| Acute Rhinitis | Fever | connected | 40F | #19 | **#4** | **+15** |
| Acute Rhinitis | Fever | connected | 10M | #19 | **#5** | **+14** |
| Acute Rhinitis | Fever | connected | 65F | #19 | **#6** | **+13** |
| Acute Rhinitis | Fever | all_no | 25M | ? | **#1** | — |
| GERD | Heartburn | connected | 25M | #2 | **#1** | **+1** |
| GERD | Heartburn | connected | 40F | #2 | #2 | 0 |
| GERD | Heartburn | connected | 10M | #2 | **#1** | **+1** |
| GERD | Heartburn | connected | 65F | #3 | #2 | **+1** |
| GERD | Heartburn | mixed_30pct | 25M | #2 | **#1** | **+1** |
| GERD | Regurgitation | connected | all | #1 | #1 | 0 |
| GERD | Abdominal pain | connected | 25M | #1 | #2 | **-1** |
| GERD | Abdominal pain | connected | 40F | #1 | #2 | **-1** |
| GERD | Abdominal pain | connected | 10M | ? | **#1** | — |
| Tension Headache | Headache | connected | 25M | #1 | #1 | 0 |
| Tension Headache | Headache | connected | 40F | #1 | #1 | 0 |
| Tension Headache | Headache | connected | 10M | #1 | **#5** | **-4** |
| Tension Headache | Headache | connected | 65F | #1 | #1 | 0 |
| Tension Headache | Headache | all_yes | 25M | #11 | **#9** | **+2** |

**Summary of rank changes:**
- **Improved:** 20+ scenarios moved up in rank
- **Same:** ~15 scenarios unchanged
- **Regressed:** 3 scenarios moved down (GERD Abdominal pain 25M/40F: #1->#2, Tension Headache 10M: #1->#5)

---

## 12. Findings and Recommendations

### What v6 Fixed

1. **The Croup-beats-Rhinitis bug is eliminated.** Croup's age_weight=0.10 for adults now applies as a 0.10x multiplier, dropping its score from 8.10 (v5) to ~1.20 (v6). Acute Rhinitis achieves Rank #1 across all demographics for Nasal congestion.

2. **The Barrett's-beats-GERD bug is mostly fixed.** Barrett's P(C)=0.4 * age=0.25 = 0.10x crushes its score. GERD now wins for 25M. (Gastritis still beats GERD for 40F/65F — see below.)

3. **Large-pool performance improved for Acute Rhinitis + Fever.** Rank #18 → Rank #4. The P(C)=1.0 multiplier for Acute Rhinitis (very_high prevalence) helps it stand out even in a crowded pool of 145 conditions.

4. **mixed_30pct robustness improved.** Acute Rhinitis + Nasal congestion mixed_30pct: Rank #5 → Rank #1. The weighted points provide a natural noise buffer.

### What v6 Introduced as New Issues

1. **Gastritis now competes with GERD (40F, 65F).**
   - Gastritis has P(C)=1.0 (very_high) vs GERD's P(C)=0.8 (high).
   - When evidence is similar (yn+pcs within 20%), P(C) becomes the tiebreaker.
   - Medically, this is debatable: GERD and Gastritis often coexist, and distinguishing them requires endoscopy, not symptom questions.
   - **Recommendation:** This is acceptable clinically — both are correct differential diagnoses for heartburn.

2. **Tension Headache regression for children (10M: Rank #1 → #5).**
   - age_weight=0.10 as a multiplier is too aggressive for a condition that IS possible in children (just less common).
   - The 0.10x multiplier means Tension Headache scores 0.368 while Cluster Headache scores 0.640 (age=0.25).
   - **Recommendation:** Consider a floor on the demographic multiplier, e.g., `max(age_weight, 0.3)`, to prevent near-zero scores for age-possible conditions.

3. **GERD + Abdominal pain: Rank #1 → #2.**
   - Gastritis (P(C)=1.0) now beats GERD (P(C)=0.8) when starting from a broad pool (79 conditions).
   - With Abdominal pain as CF, variant follow-ups don't differentiate GERD from Gastritis well enough.
   - **Recommendation:** Acceptable — both are valid top differentials for epigastric pain.

4. **Absolute scores are lower in v6.** Because the formula multiplies instead of adds, typical top scores dropped from 7-20 (v5) to 1-12 (v6). This is cosmetic and doesn't affect ranking, but may affect score_threshold tuning.

### Recommendations

| # | Recommendation | Impact | Risk |
|---|----------------|--------|------|
| 1 | **Add a floor to demographic multipliers:** `max(weight, 0.3)` | Prevents age-impossible zeroing (fixes Tension Headache 10M) | May keep some truly age-inappropriate conditions ranked higher |
| 2 | **Adjust score_threshold from 10 to 5** | Score threshold was never hit in v6 (max scores ~6-12). Lowering it may enable useful early stopping. | May stop questioning too early for some conditions |
| 3 | **Consider a P(C) dampening function** | Instead of raw P(C) as multiplier, use `P(C)^0.5` (square root). This reduces the gap between rare (0.2→0.45) and very_high (1.0→1.0) conditions. | Rare conditions become more competitive in rankings |
| 4 | **Keep variant_followup enabled** | v6 still depends on variant Qs for GERD differentiation (Heartburn: #1 with variants, #2 without) | — |
| 5 | **mixed_30pct elimination of Tension Headache** remains an issue | Same as v5: 110-condition pool + 1 root symptom = fragile. Consider larger protection thresholds for large pools. | More conservative elimination may keep false positives |

### Overall Assessment

v6 is a **net positive upgrade** from v5:
- **+34.5pp** improvement for Acute Rhinitis Top-1 accuracy
- **+6.9pp** improvement for GERD Top-1 accuracy
- **-6.7pp** regression for Tension Headache Top-1 (fixable with demographic floor)
- Fixed the two most prominent v5 bugs (Croup and Barrett's ranking above target)
- Same elimination safety (unrelated CFs still correctly eliminated)

The multiplicative demographic formula is the right architectural direction. The recommended `max(weight, 0.3)` floor would address the Tension Headache regression without reverting the Croup/Barrett's fixes.

---

## Appendix: File Inventory

| File | Description |
|------|-------------|
| `notebooks/v6_evaluation_harness.py` | Full automated test harness with v6 engine functions |
| `notebooks/v6_eval_run.py` | Focused evaluation runner (73 scenarios) |
| `notebooks/v6_evaluation_results.json` | Complete results with question logs for all 73 scenarios |
| `notebooks/v6_evaluation_summary.csv` | Summary table for all scenarios (CSV) |
| `docs/v6_evaluation_report.md` | This report |
