import pandas as pd
from dataclasses import dataclass
from typing import Optional, Set
from engine.config import LIKELIHOOD_SCORES


@dataclass
class ExpansionResult:
    starting_root: dict
    starting_variants_df: pd.DataFrame
    condition_ids: set
    discovered_roots_df: pd.DataFrame
    all_edges_df: pd.DataFrame


def get_root_uuid(root_snomed_name, data):
    row = data.nodes_symptom[
        (data.nodes_symptom['root_snomed_name'] == root_snomed_name) &
        (data.nodes_symptom['name'] == data.nodes_symptom['root_snomed_name'])
    ]
    return row.iloc[0]['uuid'] if len(row) > 0 else None


def symptom_expansion(symptom_name: str, data) -> Optional[ExpansionResult]:
    match = data.nodes_symptom[
        data.nodes_symptom['root_snomed_name'].str.lower() == symptom_name.lower()
    ]
    if len(match) == 0:
        return None

    canonical_name = match.iloc[0]['root_snomed_name']
    symptom_group = data.nodes_symptom[
        data.nodes_symptom['root_snomed_name'] == canonical_name
    ].copy()

    root_snomed_id = symptom_group.iloc[0]['root_snomed_id']
    all_uuids = symptom_group['uuid'].tolist()
    all_edges = data.edges_present_in[
        data.edges_present_in['symptom_uuid'].isin(all_uuids)
    ].copy()
    condition_ids = set(all_edges['condition_snomed_id'].unique())

    # Pre-build lookup: root_snomed_id -> set of condition_ids connected via any variant
    uuid_to_root = data.nodes_symptom.set_index('uuid')['root_snomed_id']
    edges_with_root = data.edges_present_in.copy()
    edges_with_root['root_snomed_id'] = edges_with_root['symptom_uuid'].map(uuid_to_root)

    # All edges for our condition pool
    pool_edges = edges_with_root[
        edges_with_root['condition_snomed_id'].isin(condition_ids)
    ]

    # Discover roots: unique root_snomed_ids connected to our conditions (excluding self)
    root_id_to_name = data.nodes_symptom.drop_duplicates('root_snomed_id').set_index(
        'root_snomed_id'
    )['root_snomed_name'].to_dict()

    root_cond_pairs = pool_edges[['root_snomed_id', 'condition_snomed_id']].drop_duplicates()
    root_cond_pairs = root_cond_pairs[root_cond_pairs['root_snomed_id'] != root_snomed_id]

    discovered_roots = {}
    for rid, grp in root_cond_pairs.groupby('root_snomed_id'):
        discovered_roots[rid] = {
            'root_snomed_id': rid,
            'root_snomed_name': root_id_to_name.get(rid, 'Unknown'),
            'linked_conditions': set(grp['condition_snomed_id'].unique()),
        }

    # Rank by total P(C|S) sum using root UUID edges
    root_name_to_uuid = data.nodes_symptom[
        data.nodes_symptom['name'] == data.nodes_symptom['root_snomed_name']
    ].set_index('root_snomed_name')['uuid'].to_dict()

    for rid, info in discovered_roots.items():
        root_uuid = root_name_to_uuid.get(info['root_snomed_name'])
        if root_uuid is None:
            info['total_likelihood_sum'] = 0
            continue
        root_edges = data.edges_present_in[
            (data.edges_present_in['symptom_uuid'] == root_uuid) &
            (data.edges_present_in['condition_snomed_id'].isin(condition_ids))
        ]
        info['total_likelihood_sum'] = root_edges[
            'likelihood_condition_given_symptom'
        ].map(LIKELIHOOD_SCORES).sum()

    disc_rows = [{
        'root_snomed_id': info['root_snomed_id'],
        'root_snomed_name': info['root_snomed_name'],
        'num_shared_conditions': len(info['linked_conditions']),
        'total_likelihood_sum': info['total_likelihood_sum'],
    } for info in discovered_roots.values()]

    discovered_df = (
        pd.DataFrame(disc_rows)
        .sort_values('total_likelihood_sum', ascending=False)
        .reset_index(drop=True)
        if disc_rows else pd.DataFrame()
    )

    return ExpansionResult(
        starting_root={'root_snomed_id': root_snomed_id, 'root_snomed_name': canonical_name},
        starting_variants_df=symptom_group,
        condition_ids=condition_ids,
        discovered_roots_df=discovered_df,
        all_edges_df=all_edges,
    )
