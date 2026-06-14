# BODHI Symptom Checker v5 — Evaluation Report

**Date:** 2026-06-09  
**Evaluator:** Automated Test Harness (v5_evaluation_harness.py)  
**Data:** 4,037 symptoms | 10,352 edges | 779 conditions  
**Scenarios Executed:** 73  
**Conditions Tested:** Acute Rhinitis (82272006), GERD (235595009), Tension Headache (398057008)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Test Methodology](#2-test-methodology)
3. [Default Configuration Tested](#3-default-configuration-tested)
4. [Condition 1: Acute Rhinitis](#4-condition-1-acute-rhinitis)
5. [Condition 2: GERD](#5-condition-2-gerd)
6. [Condition 3: Tension Headache](#6-condition-3-tension-headache)
7. [Cross-Condition Analysis](#7-cross-condition-analysis)
8. [Configuration Variation Results](#8-configuration-variation-results)
9. [Unrelated Chief Complaint Tests](#9-unrelated-chief-complaint-tests)
10. [Findings and Recommendations](#10-findings-and-recommendations)

---

## 1. Executive Summary

### Aggregate Results (All 73 Scenarios)

| Condition | Scenarios | Survived | Eliminated | Top-1 | Top-3 | Top-5 |
|-----------|-----------|----------|------------|-------|-------|-------|
| Acute Rhinitis | 29 | 93.1% | 6.9% | 27.6% | 65.5% | 69.0% |
| GERD | 29 | 82.8% | 17.2% | 37.9% | 79.3% | 79.3% |
| Tension Headache | 15 | 73.3% | 26.7% | 60.0% | 66.7% | 66.7% |

### Key Takeaways

1. **The algorithm works well when the chief complaint is specific to the condition.** Sneezing -> Acute Rhinitis (Rank #1, 100%), Regurgitation -> GERD (Rank #1, 100%), Headache -> Tension Headache (Rank #1, 100% with connected strategy).

2. **Broad chief complaints dilute accuracy.** Fever as CF for Acute Rhinitis drops it to Rank #18 (pool=145), Abdominal pain for GERD still achieves Rank #1 but with a wider pool (79->44).

3. **The "all_no" strategy is destructive for conditions with high P(S|C) symptoms.** GERD gets eliminated when all_no is used with Heartburn (P(S|C)=very_high triggers elimination). This is expected behavior.

4. **Variant follow-up questions are critical.** Disabling them drops Tension Headache from Rank #1 to Rank #3, and the score falls from 7.55 to 3.55.

5. **Demographics have minimal impact on ranking** under the addition method (age/gender contribute 0-1.0 each to final scores of 3-20).

6. **Unrelated chief complaints always lead to elimination** of the target condition, which is correct behavior.

---

## 2. Test Methodology

### Answer Strategies

| Strategy | Description | Purpose |
|----------|-------------|---------|
| **connected** | Answer YES to symptoms connected to the target condition in BODHI; pick the variant options that match the target's connected symptom variants. Answer NO to unconnected symptoms. | Simulates an "ideal patient" who actually has the condition. |
| **all_yes** | Answer YES to every question, pick the first option for every variant. | Stress test: what happens when all symptoms are confirmed? Tests if over-confirmation dilutes ranking. |
| **all_no** | Answer NO to everything (skip all variants). | Stress test: tests how aggressive the elimination engine is. |
| **mixed_30pct** | Connected strategy with 30% random noise (flips answers). | Simulates a realistic patient who is uncertain or makes mistakes. |
| **unrelated_cf** | Start with a chief complaint NOT connected to the target. Answer YES to connected symptoms if they appear as discovered questions. | Tests whether the algorithm can recover when the starting symptom is wrong. |

### Chief Complaints Tested Per Condition

| Condition | Primary CF | Secondary CFs | Unrelated CFs |
|-----------|-----------|---------------|---------------|
| Acute Rhinitis | Nasal congestion | Sneezing, Fever | Headache, Abdominal pain |
| GERD | Heartburn | Regurgitation, Abdominal pain | Headache, Nasal congestion |
| Tension Headache | Headache | (only 1 root symptom) | Nasal congestion, Abdominal pain |

### Demographics Tested

| Profile | Age | Gender | Notes |
|---------|-----|--------|-------|
| Young adult male | 25 | M | Baseline for all strategy comparisons |
| Middle-aged female | 40 | F | Cross-gender validation |
| Child | 10 | M | Tests age-bracket scoring (6-12 bracket) |
| Elderly female | 65 | F | Tests 60+ age bracket |

---

## 3. Default Configuration Tested

```
Elimination:
  yes_eliminate_unconnected: True
  no_eliminate_psc_levels: [very_high, high]
  protection_enabled: True
  protection_pcs_levels: [very_high, high]
  protection_increment: 0.2
  protection_threshold: 0.4

Ranking:
  yes_point: +1.0
  no_point: -0.2
  demographic_method: addition
  final_score = yn_points + sum(P(C|S)) + age_weight + gender_weight

Questioning:
  max_questions: 10
  top_n_discovered: 20
  min_pool_size: 3
  score_threshold: 10
  question_scoring_method: normalized_symptom_score
  variant_followup: ON (max 3 per symptom)
  prerequisite_mode: pre_screen (max 3)
```

---

## 4. Condition 1: Acute Rhinitis

**SNOMED:** 82272006  
**BODHI Name:** Acute rhinitis  
**Type:** acute | **Triage:** opd_managed | **Overall Likelihood:** very_high

### Connected Symptoms in BODHI

| Root Symptom | P(S\|C) | P(C\|S) | Strong Predictor |
|-------------|---------|---------|-----------------|
| Catarrhal nasal discharge | very_high | high | No |
| Nasal congestion | high | high | No |
| Sneezing | high | medium | No |
| Mouth breathing with nasal obstruction | high | medium | No |
| Fever | low | medium | No |
| Snoring | low | medium | No |

**Observation:** No strong predictors. P(C|S) tops out at "high" (0.8), never "very_high". This means Acute Rhinitis does not have any pathognomonic symptom — other conditions share the same symptoms.

### Baseline Results (connected strategy, default config)

| Chief Complaint | 25M | 40F | 10M | 65F |
|----------------|-----|-----|-----|-----|
| Nasal congestion | **Rank #2** (8.00) | Rank #2 (8.00) | Rank #2 (8.00) | Rank #2 (8.00) |
| Sneezing | **Rank #1** (7.80) | Rank #1 (7.80) | Rank #1 (7.80) | Rank #1 (7.80) |
| Fever | **Rank #18** (3.60) | Rank #19 (3.60) | Rank #19 (3.60) | Rank #19 (3.60) |

### Detailed Question Log: Nasal Congestion, connected, 25M

```
Pool: 22 conditions -> 13 surviving | 10 questions asked
Confirmed: 9 symptoms | Denied: 8

Q 1 [follow-up variant] Nasal congestion — duration  => Selected: <3 days, 3-7 days    | pool:22 | target:IN_POOL
Q 2 [follow-up variant] Nasal congestion — laterality => Selected: unilateral            | pool:22 | target:IN_POOL
Q 3 [follow-up variant] Nasal congestion — aggravated => Selected: nasal decongestant    | pool:22 | target:IN_POOL
Q 4 [prerequisite]      Nasal decongestants usage      => NO                             | pool:21 | target:IN_POOL
Q 5 [discovered]        Fever                          => YES                            | pool:21 | target:IN_POOL
Q 6 [follow-up variant] Fever — characteristic         => Selected: with chills/rigors   | pool:21 | target:IN_POOL
Q 7 [follow-up variant] Fever — relieved               => Selected: by medication        | pool:21 | target:IN_POOL
Q 8 [follow-up variant] Fever — severity               => Selected: mild                 | pool:21 | target:IN_POOL
Q 9 [discovered]        Fatigue                        => NO                             | pool:20 | target:IN_POOL
Q10 [discovered]        Headache                       => NO                             | pool:13 | target:IN_POOL

FINAL TOP 5:
  #1: Croup (Laryngotracheobronchitis)    score=8.10 (yn=+5.0, pcs=2.00, age=0.10, gen=1.00)
  #2: Acute rhinitis                      score=8.00 (yn=+3.0, pcs=3.00, age=1.00, gen=1.00) <<<
  #3: Upper respiratory infection          score=7.00 (yn=+2.8, pcs=2.20, age=1.00, gen=1.00)
  #4: Acute otitis media                  score=5.45 (yn=+2.8, pcs=1.40, age=0.25, gen=1.00)
  #5: Cervical lymphadenitis              score=5.25 (yn=+3.0, pcs=1.00, age=0.25, gen=1.00)
```

**Why Rank #2?** Croup beats Acute rhinitis by 0.10 points because:
- Croup earns yn=+5.0 vs Acute rhinitis yn=+3.0 (Croup benefits from more YES-connected symptoms in the pool)
- But Croup's age_weight=0.10 (rare in adults) vs Acute rhinitis age=1.00
- The addition method allows Croup's high yn_points to overcome its poor age fit
- **This is a scoring issue**: a 25-year-old should almost never get Croup (#1), suggesting the addition method underweights demographics for age-inappropriate conditions.

### Detailed Question Log: Sneezing, connected, 25M

```
Pool: 8 conditions -> 5 surviving | 10 questions asked
Confirmed: 5 symptoms | Denied: 10

FINAL TOP 3:
  #1: Acute rhinitis          score=7.80 (yn=+3.0, pcs=2.80, age=1.00, gen=1.00) <<<
  #2: Vasomotor Rhinitis      score=5.80 (yn=+2.0, pcs=1.80, age=1.00, gen=1.00)
  #3: Foreign body in nose    score=5.10 (yn=+2.0, pcs=1.00, age=1.10, gen=1.00)
```

**Why Sneezing works better:** Sneezing starts with only 8 conditions in the pool (vs 22 for Nasal congestion). The smaller, more focused pool makes elimination more effective and keeps irrelevant conditions from accumulating points.

### Strategy Comparison (Nasal Congestion, 25M)

| Strategy | Result | Score | Pool | Questions |
|----------|--------|-------|------|-----------|
| connected | Rank #2 | 8.00 | 22->13 | 10 |
| all_yes | Rank #6 | - | 22->22 | 10 |
| all_no | **Rank #1** | - | 22->9 | 10 |
| mixed_30pct | Rank #5 | - | 22->20 | 10 |

**Notable:** all_no achieves Rank #1 because aggressive elimination removes most competitors, and Acute rhinitis survives due to protection (P(C|S)=high). all_yes never eliminates anything (pool stays at 22), so ranking relies purely on accumulated points — bad for conditions with medium P(C|S).

---

## 5. Condition 2: GERD

**SNOMED:** 235595009  
**BODHI Name:** Gastroesophageal reflux disease  
**Type:** chronic_with_acute_aggravation | **Triage:** opd_managed | **Overall Likelihood:** high

### Connected Symptoms in BODHI

| Root Symptom | P(S\|C) | P(C\|S) | Strong Predictor |
|-------------|---------|---------|-----------------|
| Heartburn | very_high | very_high | **Yes** |
| Regurgitation | very_high | very_high | **Yes** |
| Abdominal pain | high | medium | No |
| Hiccoughs | high | high | No |
| Indigestion | high | medium | No |
| Vomit | high | low | No |
| Chest pain | medium | medium | No |
| Nausea | medium | medium | No |
| Burping | medium | high | No |
| Dysphagia | low | low | No |

**Observation:** GERD has 2 strong predictors (Heartburn, Regurgitation) with P(C|S)=very_high. This gives it a significant diagnostic advantage. It also has the richest symptom network (35 variants across 10 root symptoms).

### Baseline Results (connected strategy, default config)

| Chief Complaint | 25M | 40F | 10M | 65F |
|----------------|-----|-----|-----|-----|
| Heartburn | **Rank #2** (12.20) | Rank #2 (12.20) | Rank #2 (11.45) | Rank #3 (11.95) |
| Regurgitation | **Rank #1** (19.80) | Rank #1 (19.80) | Rank #1 (19.05) | Rank #1 (19.55) |
| Abdominal pain | **Rank #1** (6.60) | Rank #1 (6.60) | Rank #1 (5.85) | Rank #1 (6.35) |

### Detailed Question Log: Heartburn, connected, 25M

```
Pool: 9 conditions -> 9 surviving (NO conditions eliminated) | 10 questions asked
Confirmed: 12 symptoms | Denied: 23

Q 1 [follow-up variant] Heartburn — duration_since    => Selected: >1 month                | pool:9
Q 2 [follow-up variant] Heartburn — aggravated        => Selected: after caffeine           | pool:9
Q 3 [follow-up variant] Heartburn — relieved           => Selected: by antacid              | pool:9
Q 4 [discovered]        Vomit                          => YES                               | pool:9
Q 5 [follow-up variant] Vomit — characteristic         => Selected: bloody in vomit         | pool:9
Q 6 [follow-up variant] Vomit — aggravated             => Selected: on food intake          | pool:9
Q 7 [follow-up variant] Vomit — duration_since         => Selected: <1 day                  | pool:9
Q 8 [discovered]        Abdominal pain                 => YES                               | pool:9
Q 9 [follow-up variant] Abdominal pain — location      => Selected: upper abdomen, epigastric | pool:9
Q10 [follow-up variant] Abdominal pain — severity      => Selected: mild                    | pool:9

FINAL TOP 5:
  #1: Barrett's oesophagus     score=12.85 (yn=+7.0, pcs=4.60, age=0.25, gen=1.00)
  #2: GERD                     score=12.20 (yn=+5.0, pcs=5.20, age=1.00, gen=1.00) <<<
  #3: Gastric ulcer            score=11.50 (yn=+5.0, pcs=5.00, age=0.50, gen=1.00)
  #4: Gastritis                score=10.30 (yn=+4.0, pcs=4.40, age=0.90, gen=1.00)
  #5: Hiatus hernia            score= 7.75 (yn=+4.0, pcs=2.00, age=0.75, gen=1.00)
```

**Why Rank #2?** Barrett's oesophagus beats GERD because:
- Barrett's accumulates yn=+7.0 vs GERD's +5.0 (Barrett's is connected to more of the confirmed symptoms)
- GERD has higher pcs (5.20 vs 4.60) and better age fit (1.00 vs 0.25)
- But under addition, Barrett's yn advantage (+2.0) > GERD's age advantage (+0.75)
- **Note:** Barrett's is a complication of GERD, so ranking them close together is medically reasonable.

**Why no elimination?** Pool stays at 9 throughout. The Heartburn pool (9 conditions) is small and tightly related (all upper GI). YES answers don't eliminate because most conditions share the confirmed symptoms. NO answers on variant follow-ups don't trigger elimination because those are "variant skips," not root-level NO answers.

### GERD Elimination Case: Heartburn + all_no

```
Q 1-3 [variant]     Heartburn variants  => SKIP     | pool:7 (2 eliminated by variant skip)
Q 4   [discovered]  Vomit               => NO       | pool:6 | target: ELIMINATED
Q 5   [discovered]  Abdominal pain      => NO       | pool:3 | target: ELIMINATED (early stop)
```

**GERD eliminated at Q4.** When patient says NO to Vomit, GERD is eliminated because:
- Vomit has P(S|C)=high for GERD → triggers NO-side elimination
- P(C|S)=low for Vomit->GERD → no protection (protection requires P(C|S) high/very_high)
- This is correct behavior: a patient without vomiting + without heartburn variant details is less likely to have GERD

### Strategy Comparison (Heartburn, 25M)

| Strategy | Result | Score | Pool | Questions |
|----------|--------|-------|------|-----------|
| connected | Rank #2 | 12.20 | 9->9 | 10 |
| all_yes | Rank #2 | - | 9->9 | 10 |
| all_no | **ELIMINATED** | - | 9->3 | 5 |
| mixed_30pct | Rank #2 | - | 9->9 | 10 |

---

## 6. Condition 3: Tension Headache

**SNOMED:** 398057008  
**BODHI Name:** Tension Headache  
**Type:** chronic_with_acute_aggravation | **Triage:** opd_managed | **Overall Likelihood:** high

### Connected Symptoms in BODHI

| Root Symptom | P(S\|C) | P(C\|S) | Strong Predictor |
|-------------|---------|---------|-----------------|
| Headache | very_high | high | No |

**Observation:** Tension Headache has only 1 root symptom (Headache), but it has 14 variants covering duration, location, pain type, aggravating factors, and temporal pattern. The algorithm must rely entirely on variant follow-ups to differentiate it from the other 109 headache-linked conditions.

### Baseline Results (connected strategy, default config)

| Chief Complaint | 25M | 40F | 10M | 65F |
|----------------|-----|-----|-----|-----|
| Headache | **Rank #1** (7.55) | **Rank #1** (7.70) | **Rank #1** (6.90) | **Rank #1** (7.45) |

**Tension Headache achieves Rank #1 across all demographics.** This is a strong result.

### Detailed Question Log: Headache, connected, 25M

```
Pool: 110 conditions -> 56 surviving | 10 questions asked
Confirmed: 5 symptoms | Denied: 10

Q 1 [follow-up variant] Headache — onset           => Selected: sudden onset           | pool:109
Q 2 [follow-up variant] Headache — pain_type       => Selected: sharp/stabbing         | pool:109
Q 3 [follow-up variant] Headache — duration_since  => Selected: 1-3 weeks, 3-12 weeks  | pool:109
Q 4 [prerequisite]      Head injury                => NO                               | pool:107
Q 5 [prerequisite]      Hypertension               => NO                               | pool:106
Q 6 [prerequisite]      Seizure                    => NO                               | pool:105
Q 7 [discovered]        Fever                      => NO                               | pool: 81
Q 8 [discovered]        Fatigue                    => NO                               | pool: 71
Q 9 [discovered]        Malaise                    => NO                               | pool: 69
Q10 [discovered]        Vomit                      => NO                               | pool: 56

FINAL TOP 5:
  #1: Tension Headache          score=7.55 (yn=+3.0, pcs=2.80, age=0.75, gen=1.00) <<<
  #2: Cluster Headache          score=6.40 (yn=+3.0, pcs=1.40, age=1.00, gen=1.00)
  #3: Occipital neuralgia       score=6.30 (yn=+3.0, pcs=1.80, age=0.50, gen=1.00)
  #4: Myopia (disorder)         score=4.90 (yn=+2.0, pcs=1.00, age=0.90, gen=1.00)
  #5: Cavernous sinus thrombosis score=4.60 (yn=+1.6, pcs=1.00, age=1.00, gen=1.00)
```

**Why it works:** The variant follow-ups for Headache are highly differentiating. By confirming "sudden onset," "sharp/stabbing pain," and "1-3 weeks duration," the algorithm accumulates P(C|S) scores specific to Tension Headache. The NO answers on Fever, Fatigue, Malaise, Vomit eliminate infectious and systemic causes (54 conditions eliminated total).

### Strategy Comparison (Headache, 25M)

| Strategy | Result | Score | Pool | Questions |
|----------|--------|-------|------|-----------|
| connected | **Rank #1** | 7.55 | 110->56 | 10 |
| all_yes | Rank #11 | - | 110->109 | 10 |
| all_no | **ELIMINATED** | - | 110->53 | 10 |
| mixed_30pct | **ELIMINATED** | - | 110->64 | 10 |

**Concerning:** mixed_30pct (30% noise) causes elimination. With 110 conditions in the pool and only 1 root symptom, any wrong NO answer on a key question (like a variant follow-up) can trigger elimination via the NO-side rule. This sensitivity is a weakness for conditions with large starting pools.

---

## 7. Cross-Condition Analysis

### What Makes a Condition Easy or Hard to Diagnose?

| Factor | Easy (Tension Headache) | Medium (GERD) | Harder (Acute Rhinitis) |
|--------|------------------------|---------------|------------------------|
| Pool size | Large (110) but well-narrowed by NO answers | Small (6-9) | Medium (8-22) |
| Strong predictors | 0 | 2 (Heartburn, Regurgitation) | 0 |
| Variant richness | 14 variants (excellent differentiation) | 35 variants across 10 roots | 11 variants across 6 roots |
| Competing conditions | Many but different symptom profiles | Few but very similar (Barrett's, Gastritis) | Overlapping (URI, Croup, Allergic rhinitis) |
| Best CF result | Rank #1 (100%) | Rank #1 from Regurgitation (100%) | Rank #1 from Sneezing (100%) |

### Score Composition Analysis

Under the addition method: `final_score = yn_points + pcs_score + age_weight + gender_weight`

| Component | Typical Range | Weight in Final Score | Issue |
|-----------|--------------|----------------------|-------|
| yn_points | -2.0 to +7.0 | Dominant (~40-60%) | Favors conditions connected to many confirmed symptoms |
| pcs_score | 0.0 to 5.2 | Significant (~20-35%) | Correctly reflects diagnostic strength |
| age_weight | 0.0 to 1.0 | Minor (~5-15%) | Too small to override bad yn_points |
| gender_weight | 0.0 to 1.0 | Minor (~5-15%) | Nearly always 1.0, rarely differentiating |

**Key Insight:** The yn_points component dominates ranking. Conditions that happen to be connected to many of the patient's confirmed symptoms get high yn_points regardless of whether those symptoms are diagnostically meaningful for that specific condition. This is why Croup beats Acute rhinitis (Croup shares more connections) and Barrett's beats GERD.

---

## 8. Configuration Variation Results

### Acute Rhinitis (CF=Nasal congestion, connected, 25M)

| Config | Rank | Score | Pool | Notes |
|--------|------|-------|------|-------|
| **default (baseline)** | **#2** | **8.00** | **22->13** | |
| protection_OFF | #2 | 8.00 | 22->13 | No change — protection wasn't triggered for target |
| max_q_5 | **#1** | 8.00 | 22->21 | Fewer questions = less elimination = less noise, but Croup doesn't accumulate enough yn |
| variants_OFF | **#1** | 7.20 | 22->9 | Without variants, fewer confirmed symptoms = lower yn for Croup |
| rank_multiply | **#1** | 9.00 | 22->13 | Multiplication penalizes Croup's age=0.10 harshly |
| wider_no_elim | #2 | 8.00 | 22->12 | 1 more condition eliminated, but ranking unchanged |
| no_score_threshold | #2 | 8.00 | 22->13 | Score threshold wasn't reached in baseline anyway |

**Best config change for Acute Rhinitis:** `rank_multiply` or `variants_OFF` both achieve Rank #1.

### GERD (CF=Heartburn, connected, 25M)

| Config | Rank | Score | Pool | Notes |
|--------|------|-------|------|-------|
| **default (baseline)** | **#2** | **12.20** | **9->9** | |
| protection_OFF | #2 | 12.20 | 9->9 | No change |
| max_q_5 | #2 | 7.60 | 9->9 | Fewer questions = lower score but same rank |
| variants_OFF | #2 | 10.20 | 9->6 | Removes 3 conditions but Barrett's still wins |
| rank_multiply | **#1** | 26.00 | 9->9 | Barrett's age=0.25 gets penalized harshly |
| wider_no_elim | #2 | 12.20 | 9->9 | No change (conditions already share symptoms) |
| no_score_threshold | #2 | 12.20 | 9->9 | No change |

**Best config change for GERD:** `rank_multiply` achieves Rank #1.

### Tension Headache (CF=Headache, connected, 25M)

| Config | Rank | Score | Pool | Notes |
|--------|------|-------|------|-------|
| **default (baseline)** | **#1** | **7.55** | **110->56** | |
| protection_OFF | #1 | 7.55 | 110->54 | 2 more eliminated, rank unchanged |
| max_q_5 | #1 | 7.55 | 110->106 | Only 4 eliminated in 5 Qs, but still #1 |
| **variants_OFF** | **#3** | **3.55** | **110->55** | **DEGRADED** |
| rank_multiply | #1 | 6.30 | 110->56 | Same rank, lower absolute score |
| wider_no_elim | #1 | 7.55 | 110->35 | Much more aggressive elimination |
| no_score_threshold | #1 | 7.55 | 110->56 | No change |

**Critical finding for Tension Headache:** Disabling variant follow-ups drops rank from #1 to #3 and halves the score (7.55 -> 3.55). This is because Headache has 14 variants, and without asking about duration, pain type, and onset, the algorithm cannot differentiate Tension Headache from Iridocyclitis, Astigmatism, and other headache conditions.

---

## 9. Unrelated Chief Complaint Tests

All 6 unrelated CF scenarios result in **ELIMINATION** of the target condition.

| Target | Chief Complaint | Result | Pool | Questions |
|--------|----------------|--------|------|-----------|
| Acute Rhinitis | Headache | ELIMINATED | 110->88 | 10 |
| Acute Rhinitis | Abdominal pain | ELIMINATED | 79->61 | 10 |
| GERD | Headache | ELIMINATED | 110->60 | 10 |
| GERD | Nasal congestion | ELIMINATED | 22->9 | 10 |
| Tension Headache | Nasal congestion | ELIMINATED | 22->13 | 10 |
| Tension Headache | Abdominal pain | ELIMINATED | 79->43 | 10 |

**This is correct behavior.** If the patient starts with a completely unrelated symptom and the algorithm never discovers a symptom connected to the target, the target should be eliminated. The YES-elimination rule (remove conditions not connected to ANY confirmed symptom) ensures this.

**Note:** The `unrelated_cf` strategy tries to say YES to connected symptoms IF they come up as discovered questions, but the algorithm selects questions by scoring (normalized_symptom_score), and the connected symptoms for the unrelated target may not rank high enough to be asked within 10 questions.

---

## 10. Findings and Recommendations

### What Works Well

1. **Variant follow-up system:** Excellent at differentiating within shared symptom groups. Critical for Tension Headache (14 Headache variants) and GERD (35 variants). *Do not disable this.*

2. **Elimination engine:** The YES-side elimination (remove conditions not connected to any confirmed symptom) is the main pool-narrowing mechanism. It correctly eliminates 40-50% of the pool over 10 questions.

3. **Protection counter system:** Prevents premature elimination of important conditions. When a condition has P(C|S)=high/very_high, it gets 2 chances before elimination (counter must reach 0.4 with 0.2 increments).

4. **Small focused pools:** Conditions with specific chief complaints (Sneezing->8, Heartburn->9, Regurgitation->6) consistently achieve Rank #1 or #2. The algorithm excels when the starting pool is under ~20.

5. **Prerequisite screening:** Effectively eliminates conditions requiring specific preconditions (head injury, hypertension, seizure). Removes 2-5 conditions per prerequisite question.

### What Needs Improvement

1. **Addition-based ranking underweights demographics.**
   - Croup (age_weight=0.10 for a 25-year-old) beats Acute rhinitis (age_weight=1.00) because yn_points dominate.
   - Barrett's (age_weight=0.25 for a 25-year-old) beats GERD (age_weight=1.00) for the same reason.
   - **Recommendation:** Consider `demographic_method: multiplication` or a hybrid approach. Multiplication correctly penalizes age-inappropriate conditions but may zero out scores when demographic weight is 0.0.

2. **Large starting pools reduce accuracy.**
   - Fever pool = 145 conditions. Acute Rhinitis drops to Rank #18.
   - Headache pool = 110 conditions. Works for Tension Headache (Rank #1) only because of excellent variant follow-ups.
   - **Recommendation:** Consider a 2-phase approach: first narrow by asking 2-3 broad discriminating questions, then switch to targeted questioning.

3. **mixed_30pct (noisy answers) causes Tension Headache elimination.**
   - With 110 conditions and only 1 root symptom, a single wrong NO answer on a high-impact question can trigger cascading elimination.
   - **Recommendation:** Consider making elimination more conservative for conditions that haven't been directly contradicted, or increasing protection thresholds when pool is large.

4. **No conditions eliminated when starting pool is already small (GERD from Heartburn: 9->9).**
   - When all 9 conditions share most of the same symptoms, YES-side elimination can't remove any (all are connected to confirmed symptoms).
   - This is not necessarily a problem — the ranking system correctly differentiates them — but it means the elimination engine provides no value for tightly-related condition clusters.

5. **10-question limit may be insufficient for large pools.**
   - Fever (145->91): 54 conditions eliminated but 91 survive after 10 questions.
   - Headache (110->56): 54 eliminated, 56 survive.
   - **Recommendation:** Consider dynamic question limits based on pool size, or adding a "rapid-fire" phase with simple YES/NO for common discriminators.

### Recommended Configuration Changes

| Change | Impact | Risk |
|--------|--------|------|
| Switch to `multiplication` ranking | Fixes Croup/Barrett's beating target conditions | May zero-out conditions with 0.0 demographic weight |
| Increase `max_questions` to 15 for pools > 50 | Better narrowing for Fever/Headache pools | Longer patient interaction |
| Increase `protection_threshold` to 0.6 | More resilient to noisy answers | May keep false positives alive longer |
| Add `min_pool_size: 5` (from 3) | Prevents over-elimination in small pools | Keeps more conditions to rank |

---

## Appendix: File Inventory

| File | Description |
|------|-------------|
| `notebooks/v5_evaluation_harness.py` | Full automated test harness with all engine functions |
| `notebooks/v5_eval_run.py` | Focused evaluation runner (73 scenarios) |
| `notebooks/v5_evaluation_results.json` | Complete results with question logs for all 73 scenarios |
| `notebooks/v5_evaluation_summary.csv` | Summary table for all scenarios (CSV) |
| `docs/v5_evaluation_report.md` | This report |
