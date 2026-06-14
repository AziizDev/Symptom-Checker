import pandas as pd
from engine.config import LIKELIHOOD_SCORES, RANKING_CONFIG


def get_age_bracket_column(age):
    brackets = [
        (1, 'likelihood_age_0_1'), (5, 'likelihood_age_1_5'),
        (12, 'likelihood_age_6_12'), (18, 'likelihood_age_13_18'),
        (30, 'likelihood_age_19_30'), (45, 'likelihood_age_30_45'),
        (60, 'likelihood_age_45_60'),
    ]
    for upper, col in brackets:
        if age <= upper:
            return col
    return 'likelihood_age_60_plus'


def get_gender_column(gender):
    return 'likelihood_male' if gender.upper() in ('M', 'MALE') else 'likelihood_female'


def rank_conditions(confirmed_uuids, denied_uuids, surviving_pool,
                    condition_points, age, gender, data, ranking_config=None):
    if ranking_config is None:
        ranking_config = RANKING_CONFIG

    if not surviving_pool:
        return pd.DataFrame(), pd.DataFrame()

    confirmed_edges = data.edges_present_in[
        (data.edges_present_in['symptom_uuid'].isin(confirmed_uuids)) &
        (data.edges_present_in['condition_snomed_id'].isin(surviving_pool))
    ].copy()

    confirmed_edges['pcs_score'] = confirmed_edges[
        'likelihood_condition_given_symptom'
    ].map(LIKELIHOOD_SCORES).fillna(0)

    pcs_agg = confirmed_edges.groupby('condition_snomed_id').agg(
        pcs_total=('pcs_score', 'sum'),
        num_symptom_matches=('symptom_uuid', 'nunique')
    ).reset_index()

    gender_col = get_gender_column(gender)
    age_col = get_age_bracket_column(age)

    rows = []
    for cid in surviving_pool:
        yn = condition_points.get(cid, 0)
        pcs_row = pcs_agg[pcs_agg['condition_snomed_id'] == cid]
        pcs = pcs_row['pcs_total'].values[0] if len(pcs_row) > 0 else 0
        matches = int(pcs_row['num_symptom_matches'].values[0]) if len(pcs_row) > 0 else 0

        cond = data.nodes_condition[data.nodes_condition['snomed_id'] == cid]
        name = cond['name'].values[0] if len(cond) > 0 else 'Unknown'
        triage = cond['triage_level'].values[0] if len(cond) > 0 else 'unknown'
        type_c = cond['type_condition'].values[0] if len(cond) > 0 else 'unknown'

        g_w = cond[gender_col].values[0] if len(cond) > 0 else 1.0
        a_w = cond[age_col].values[0] if len(cond) > 0 else 1.0
        g_w = g_w if pd.notna(g_w) else 1.0
        a_w = a_w if pd.notna(a_w) else 1.0

        pc = LIKELIHOOD_SCORES.get(
            cond['overall_likelihood'].values[0], 0
        ) if len(cond) > 0 else 0

        if ranking_config['demographic_method'] == 'multiplication':
            final = yn * pcs * float(g_w) * float(a_w) * pc if pcs > 0 else 0
        else:
            final = (yn + pcs) * pc * float(g_w) * float(a_w)

        rows.append({
            'condition_snomed_id': cid,
            'condition_name': name,
            'triage_level': triage,
            'type_condition': type_c,
            'num_symptom_matches': matches,
            'yn_points': round(yn, 2),
            'pcs_score': round(pcs, 2),
            'pc_weight': round(pc, 4),
            'gender_weight': round(float(g_w), 2),
            'age_weight': round(float(a_w), 2),
            'final_score': round(final, 4),
        })

    result = pd.DataFrame(rows).sort_values(
        'final_score', ascending=False
    ).reset_index(drop=True)

    detail = confirmed_edges.merge(
        data.nodes_symptom[['uuid', 'name', 'root_snomed_name']],
        left_on='symptom_uuid', right_on='uuid', how='left'
    ).merge(
        data.nodes_condition[['snomed_id', 'name']],
        left_on='condition_snomed_id', right_on='snomed_id', how='left',
        suffixes=('_symptom', '_condition')
    )
    detail = detail[[
        'name_symptom', 'root_snomed_name', 'name_condition',
        'likelihood_condition_given_symptom', 'pcs_score'
    ]].copy()
    detail.columns = ['symptom_variant', 'root_symptom', 'condition_name',
                      'likelihood_text', 'pcs_score']
    detail = detail.sort_values(
        ['condition_name', 'pcs_score'], ascending=[True, False]
    ).reset_index(drop=True)

    return result, detail
