import pandas as pd
from engine.config import (
    LIKELIHOOD_SCORES, LIKELIHOOD_SCORES_COMPRESSED,
    RELATION_QUESTIONS, PREREQUISITE_QUESTIONS,
)


def compute_yes_eliminations(symptom_uuid, pool, confirmed_uuids, protection_counters, elim_config, data):
    eliminated = set()
    if elim_config['yes_eliminate_unconnected']:
        all_confirmed = set(confirmed_uuids) | {symptom_uuid}
        all_confirmed_edges = data.edges_present_in[
            data.edges_present_in['symptom_uuid'].isin(all_confirmed)
        ]
        connected = set(all_confirmed_edges['condition_snomed_id'].unique()) & pool
        eliminated = pool - connected
    return eliminated, protection_counters


def compute_no_eliminations(symptom_uuid, pool, protection_counters, elim_config, data):
    eliminated = set()
    edges = data.edges_present_in[
        (data.edges_present_in['symptom_uuid'] == symptom_uuid) &
        (data.edges_present_in['condition_snomed_id'].isin(pool))
    ]

    for _, edge in edges.iterrows():
        cid = edge['condition_snomed_id']
        psc = edge['likelihood_symptom_given_condition']
        pcs = edge['likelihood_condition_given_symptom']

        if psc not in elim_config['no_eliminate_psc_levels']:
            continue

        pcs_protected = (
            elim_config['protection_enabled'] and
            pcs in elim_config['protection_pcs_levels']
        )

        triage_protected = False
        if elim_config['triage_protection']:
            triage = data.nodes_condition[
                data.nodes_condition['snomed_id'] == cid
            ]['triage_level'].values
            if len(triage) > 0 and triage[0] in elim_config['triage_always_protect']:
                triage_protected = True

        if pcs_protected or triage_protected:
            increment = elim_config['protection_increment']
            if triage_protected and not pcs_protected:
                increment = elim_config['triage_protection_increment']
            counter = protection_counters.get(cid, 0) + increment
            protection_counters[cid] = counter
            if counter >= elim_config['protection_threshold']:
                eliminated.add(cid)
        else:
            eliminated.add(cid)

    return eliminated, protection_counters


def compute_question_value(symptom_uuid, pool, confirmed_uuids, protection_counters,
                           elim_config, questioning_config, data):
    edges = data.edges_present_in[
        (data.edges_present_in['symptom_uuid'] == symptom_uuid) &
        (data.edges_present_in['condition_snomed_id'].isin(pool))
    ]
    connected = set(edges['condition_snomed_id'].unique())
    if not connected:
        return 0.0, 0, 0, 0, 0.0

    pool_size = len(pool)
    method = questioning_config.get('question_scoring_method', 'ev')

    if method == 'normalized_symptom_score':
        all_edges = data.edges_present_in[
            data.edges_present_in['symptom_uuid'] == symptom_uuid
        ]
        symptom_score = 0.0
        for _, edge in all_edges.iterrows():
            cid = edge['condition_snomed_id']
            psc_val = LIKELIHOOD_SCORES_COMPRESSED.get(
                edge['likelihood_symptom_given_condition'], 0)
            cond = data.nodes_condition[data.nodes_condition['snomed_id'] == cid]
            if len(cond) > 0:
                pc_val = LIKELIHOOD_SCORES_COMPRESSED.get(
                    cond.iloc[0]['overall_likelihood'], 0)
            else:
                pc_val = 0
            symptom_score += psc_val * pc_val

        all_conf = set(confirmed_uuids) | {symptom_uuid}
        yes_connected = set(
            data.edges_present_in[
                data.edges_present_in['symptom_uuid'].isin(all_conf)
            ]['condition_snomed_id'].unique()
        ) & pool
        yes_elim = len(pool - yes_connected)

        no_elim_set = set()
        temp_prot = dict(protection_counters)
        for _, edge in edges.iterrows():
            cid = edge['condition_snomed_id']
            psc = edge['likelihood_symptom_given_condition']
            pcs = edge['likelihood_condition_given_symptom']
            if psc in elim_config['no_eliminate_psc_levels']:
                pcs_prot = (elim_config['protection_enabled'] and
                            pcs in elim_config['protection_pcs_levels'])
                triage_prot = False
                if elim_config['triage_protection']:
                    t = data.nodes_condition[
                        data.nodes_condition['snomed_id'] == cid
                    ]['triage_level'].values
                    if len(t) > 0 and t[0] in elim_config['triage_always_protect']:
                        triage_prot = True
                if pcs_prot or triage_prot:
                    c = temp_prot.get(cid, 0) + elim_config['protection_increment']
                    temp_prot[cid] = c
                    if c >= elim_config['protection_threshold']:
                        no_elim_set.add(cid)
                else:
                    no_elim_set.add(cid)
        no_elim = len(no_elim_set)

        return symptom_score, yes_elim, no_elim, len(connected), symptom_score

    else:
        p_yes = 0.0
        total_cond_weight = data.total_condition_weight
        for _, edge in edges.iterrows():
            cid = edge['condition_snomed_id']
            psc_val = LIKELIHOOD_SCORES.get(
                edge['likelihood_symptom_given_condition'], 0)
            cond = data.nodes_condition[data.nodes_condition['snomed_id'] == cid]
            if len(cond) > 0:
                pc_raw = LIKELIHOOD_SCORES.get(cond.iloc[0]['overall_likelihood'], 0)
                pc_val = pc_raw / total_cond_weight
            else:
                pc_val = 0
            p_yes += psc_val * pc_val
        p_yes = min(p_yes, 1.0)
        p_no = 1.0 - p_yes

        all_conf = set(confirmed_uuids) | {symptom_uuid}
        yes_connected = set(
            data.edges_present_in[
                data.edges_present_in['symptom_uuid'].isin(all_conf)
            ]['condition_snomed_id'].unique()
        ) & pool
        yes_elim = len(pool - yes_connected)

        no_elim_set = set()
        temp_prot = dict(protection_counters)
        for _, edge in edges.iterrows():
            cid = edge['condition_snomed_id']
            psc = edge['likelihood_symptom_given_condition']
            pcs = edge['likelihood_condition_given_symptom']
            if psc in elim_config['no_eliminate_psc_levels']:
                pcs_prot = (elim_config['protection_enabled'] and
                            pcs in elim_config['protection_pcs_levels'])
                triage_prot = False
                if elim_config['triage_protection']:
                    t = data.nodes_condition[
                        data.nodes_condition['snomed_id'] == cid
                    ]['triage_level'].values
                    if len(t) > 0 and t[0] in elim_config['triage_always_protect']:
                        triage_prot = True
                if pcs_prot or triage_prot:
                    c = temp_prot.get(cid, 0) + elim_config['protection_increment']
                    temp_prot[cid] = c
                    if c >= elim_config['protection_threshold']:
                        no_elim_set.add(cid)
                else:
                    no_elim_set.add(cid)
        no_elim = len(no_elim_set)

        expected_elim = p_yes * yes_elim + p_no * no_elim
        score = expected_elim / pool_size if pool_size > 0 else 0
        return score, yes_elim, no_elim, len(connected), p_yes


def build_variant_questions(root_snomed_name, data):
    symptom_group = data.nodes_symptom[
        data.nodes_symptom['root_snomed_name'] == root_snomed_name
    ].copy()
    if len(symptom_group) == 0:
        return []

    variants = symptom_group[
        (symptom_group['relation1_type'].notna()) &
        (symptom_group['uuid'].isin(data.uuids_with_edges))
    ]
    questions = []
    for relation_type, group in variants.groupby('relation1_type'):
        question_text = RELATION_QUESTIONS.get(relation_type, f"About the {relation_type}?")
        selection_type = group.iloc[0]['grouping1_selection_type']
        options = []
        for _, row in group.iterrows():
            if pd.notna(row.get('child2_name')):
                label = f"{row['child1_name']} > {row['child2_name']}"
            elif pd.notna(row.get('child1_name')):
                label = row['child1_name']
            else:
                label = row['name']
            options.append({'label': label, 'uuid': row['uuid'], 'name': row['name']})
        questions.append({
            'type': 'variant',
            'root_name': root_snomed_name,
            'relation_type': relation_type,
            'question': question_text,
            'selection_type': selection_type,
            'options': options,
            'score_uuid': group.iloc[0]['uuid'],
            'all_uuids': group['uuid'].tolist(),
        })
    return questions


def build_prerequisite_questions(candidate_pool, gender, data, confirmed_uuids=None, cf_mode='static'):
    STRENGTH_SCORES = {
        'very_high': 1.0, 'high': 0.8, 'medium': 0.6,
        'low': 0.4, 'rare': 0.2, 'zero': 0.0,
    }

    relevant = data.edges_has_prerequisite[
        data.edges_has_prerequisite['condition_snomed_id_src'].isin(candidate_pool)
    ]
    if len(relevant) == 0:
        return []

    if cf_mode == 'dynamic' and confirmed_uuids:
        confirmed_set = set(confirmed_uuids)
        confirmed_edges = data.edges_present_in[
            (data.edges_present_in['symptom_uuid'].isin(confirmed_set)) &
            (data.edges_present_in['condition_snomed_id'].isin(candidate_pool))
        ]
        cf_counts = confirmed_edges.groupby('condition_snomed_id')['symptom_uuid'].nunique().to_dict()
    else:
        cf_counts = data.edges_present_in.groupby('condition_snomed_id')['symptom_uuid'].nunique().to_dict()

    questions = []
    for prereq_id, group in relevant.groupby('condition_snomed_id_dst'):
        affected_conditions = set(group['condition_snomed_id_src'].unique()) & candidate_pool
        if not affected_conditions:
            continue

        prereq_cond = data.nodes_condition[data.nodes_condition['snomed_id'] == prereq_id]
        if len(prereq_cond) == 0:
            continue
        prereq_name = prereq_cond.iloc[0]['name']

        if gender:
            gender_col = _get_gender_column(gender)
            gender_weight = prereq_cond.iloc[0][gender_col]
            if pd.notna(gender_weight) and float(gender_weight) == 0.0:
                continue

        question_text = PREREQUISITE_QUESTIONS.get(
            prereq_name,
            f"Do you have or have you had: {prereq_name}?"
        )

        prereq_score = 0.0
        for _, row in group[group['condition_snomed_id_src'].isin(affected_conditions)].iterrows():
            cid = row['condition_snomed_id_src']
            strength = STRENGTH_SCORES.get(row['relation_strength'], 0)
            cond_row = data.nodes_condition[data.nodes_condition['snomed_id'] == cid]
            pc = LIKELIHOOD_SCORES.get(cond_row.iloc[0]['overall_likelihood'], 0) if len(cond_row) > 0 else 0
            cf = cf_counts.get(cid, 0)
            prereq_score += strength * pc * (1.0 / (cf + 1))

        questions.append({
            'type': 'prerequisite',
            'prereq_id': prereq_id,
            'prereq_name': prereq_name,
            'question': question_text,
            'affected_condition_ids': affected_conditions,
            'num_affected': len(affected_conditions),
            'prereq_score': prereq_score,
            'score_uuid': f"prereq_{prereq_id}",
        })

    questions.sort(key=lambda x: x['prereq_score'], reverse=True)
    return questions


def _get_gender_column(gender):
    return 'likelihood_male' if gender.upper() in ('M', 'MALE') else 'likelihood_female'
