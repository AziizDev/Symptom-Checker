"""
Algorithm test: replays the Sneezing test case against v6 engine.

Run: python test_engine.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class FakeStreamlit:
    @staticmethod
    def cache_data(func=None, **kwargs):
        if func is None:
            return lambda f: f
        return func

sys.modules['streamlit'] = FakeStreamlit()
sys.modules['streamlit'].cache_data = FakeStreamlit.cache_data

from engine.data_loader import DataBundle
from engine.config import LIKELIHOOD_SCORES
from engine.presets import get_merged_config
from engine.expansion import symptom_expansion
from engine.questioning import QuestioningEngine
from engine.ranking import rank_conditions
import pandas as pd


def load_data_direct():
    csv_dir = os.path.join(os.path.dirname(__file__), '..', 'csv')
    csv_dir = os.path.abspath(csv_dir)

    nodes_symptom = pd.read_csv(os.path.join(csv_dir, 'nodes_symptom.csv'))
    edges_present_in = pd.read_csv(os.path.join(csv_dir, 'edges_present_in.csv'))
    nodes_condition = pd.read_csv(os.path.join(csv_dir, 'nodes_condition.csv'))
    edges_has_prerequisite = pd.read_csv(os.path.join(csv_dir, 'edges_has_prerequisite.csv'))

    edges_present_in['likelihood_condition_given_symptom'] = (
        edges_present_in['likelihood_condition_given_symptom'].str.lower()
    )
    edges_present_in['likelihood_symptom_given_condition'] = (
        edges_present_in['likelihood_symptom_given_condition'].str.lower()
    )
    nodes_condition['overall_likelihood'] = nodes_condition['overall_likelihood'].str.lower()
    edges_has_prerequisite['relation_strength'] = edges_has_prerequisite['relation_strength'].str.lower()
    edges_has_prerequisite['relation_polarity'] = edges_has_prerequisite['relation_polarity'].str.lower()

    uuids_with_edges = set(edges_present_in['symptom_uuid'].unique())
    total_condition_weight = nodes_condition['overall_likelihood'].map(LIKELIHOOD_SCORES).sum()
    symptom_names = sorted(
        nodes_symptom[nodes_symptom['name'] == nodes_symptom['root_snomed_name']]
        ['root_snomed_name'].unique().tolist()
    )

    return DataBundle(
        nodes_symptom=nodes_symptom,
        nodes_condition=nodes_condition,
        edges_present_in=edges_present_in,
        edges_has_prerequisite=edges_has_prerequisite,
        uuids_with_edges=uuids_with_edges,
        total_condition_weight=total_condition_weight,
        symptom_names=symptom_names,
    )


def test_sneezing_scenario():
    print("=" * 60)
    print("  V6 SMOKE TEST: Sneezing scenario (M, 22)")
    print("=" * 60)

    data = load_data_direct()
    config = get_merged_config('Standard')
    expansion = symptom_expansion('Sneezing', data)

    assert expansion is not None, "Expansion failed for 'Sneezing'"
    print(f"  Expansion: {len(expansion.condition_ids)} conditions, "
          f"{len(expansion.discovered_roots_df)} discovered symptoms")

    engine = QuestioningEngine(data, config)
    state = engine.initialize(expansion, 'M', 22)

    answers = []
    q_num = 0
    while not state.finished:
        q = state.current_question
        if q is None:
            break
        q_num += 1
        q_type = q['type']
        q_text = q.get('question', q.get('root_name', ''))

        if q_type == 'discovered':
            root = q['root_name']
            if root == 'Fever':
                ans = True
            elif root == 'Fatigue':
                ans = False
            elif root == 'Headache':
                ans = False
            elif root == 'Cough':
                ans = True
            else:
                ans = False
        elif q_type == 'variant':
            relation = q.get('relation_type', '')
            root = q.get('root_name', '')
            if root == 'Fever' and relation == 'relieved':
                ans = [0]
            elif root == 'Cough' and relation == 'characteristic':
                ans = [1]
            else:
                ans = []
        elif q_type == 'prerequisite':
            ans = False
        else:
            ans = False

        print(f"  Q{q_num} [{q_type}] {q_text[:50]} -> {ans}")
        state = engine.process_answer(state, ans)

    print(f"\n  Questions asked: {state.questions_asked}")
    print(f"  Surviving pool: {len(state.candidate_pool)}")
    print(f"  Confirmed UUIDs: {len(state.confirmed_uuids)}")

    result_df, detail_df = rank_conditions(
        state.confirmed_uuids, state.denied_uuids, state.candidate_pool,
        state.condition_points, 22, 'M', data, config['ranking']
    )

    print(f"\n  Top 5:")
    for i, row in result_df.head(5).iterrows():
        print(f"    {i+1}. {row['condition_name']} = {row['final_score']:.4f} "
              f"(Y/N:{row['yn_points']:+.2f} PCS:{row['pcs_score']:.2f} "
              f"P(C):{row['pc_weight']:.2f})")

    print(f"\n  Pool: {len(state.candidate_pool)} | "
          f"Top: {result_df.iloc[0]['condition_name'] if len(result_df) > 0 else 'N/A'}")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = test_sneezing_scenario()
    sys.exit(0 if success else 1)
