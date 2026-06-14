import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

from engine.config import LIKELIHOOD_SCORES, RANKING_CONFIG
from engine.elimination import (
    compute_yes_eliminations, compute_no_eliminations,
    compute_question_value, build_variant_questions,
    build_prerequisite_questions,
)
from engine.expansion import get_root_uuid


@dataclass
class QuestioningState:
    candidate_pool: set
    confirmed_uuids: list
    denied_uuids: list
    condition_points: dict
    protection_counters: dict
    question_log: list
    questions_asked: int
    asked_uuids: set
    phase: str
    current_question: Optional[dict]
    variant_followup_queue: list
    phase1_remaining: list
    phase2_remaining: list
    phase2_count: int
    finished: bool
    stop_reason: str
    gender: str
    age: int
    discovered_q_count: int = 0
    prereqs_done: bool = False


class QuestioningEngine:

    def __init__(self, data, config):
        self.data = data
        self.config = config
        self.elim_config = config['elim']
        self.ranking_config = config['ranking']
        self.q_config = config['questioning']

    def initialize(self, expansion_result, gender, age):
        starting_variants = expansion_result.starting_variants_df
        root_name = expansion_result.starting_root['root_snomed_name']
        candidate_pool = set(expansion_result.condition_ids)

        condition_points = {cid: 0.0 for cid in candidate_pool}
        confirmed_uuids = []
        denied_uuids = []
        protection_counters = {}

        root_row = starting_variants[
            starting_variants['name'] == starting_variants['root_snomed_name']
        ]
        if len(root_row) > 0:
            root_uuid = root_row.iloc[0]['uuid']
            confirmed_uuids.append(root_uuid)
            root_edges = self.data.edges_present_in[
                (self.data.edges_present_in['symptom_uuid'] == root_uuid) &
                (self.data.edges_present_in['condition_snomed_id'].isin(candidate_pool))
            ]
            for _, edge in root_edges.iterrows():
                pcs_w = LIKELIHOOD_SCORES.get(edge['likelihood_condition_given_symptom'], 0)
                condition_points[edge['condition_snomed_id']] += (
                    self.ranking_config['yes_point'] * pcs_w
                )

        phase1_remaining = []
        if self.q_config.get('variant_followup_enabled', False):
            starting_variant_qs = build_variant_questions(root_name, self.data)
            scored = []
            for svq in starting_variant_qs:
                sv_score = compute_question_value(
                    svq['score_uuid'], candidate_pool, confirmed_uuids,
                    protection_counters, self.elim_config, self.q_config, self.data
                )[0]
                scored.append((sv_score, svq))
            scored.sort(key=lambda x: x[0], reverse=True)
            max_fups = self.q_config.get('max_variant_followups', 3)
            phase1_remaining = [q for _, q in scored[:max_fups]]

        phase2_remaining = []
        prereq_mode = self.q_config.get('prerequisite_mode', 'off')
        prereq_delay = self.q_config.get('prerequisite_after_n_discovered', 0)
        prereqs_done = False

        if prereq_delay == 0 and prereq_mode in ('pre_screen', 'both'):
            cf_mode = self.q_config.get('prerequisite_cf_mode', 'static')
            phase2_remaining = build_prerequisite_questions(
                candidate_pool, gender, self.data, confirmed_uuids, cf_mode
            )
            prereqs_done = True

        self._askable_pool = self._build_askable_pool(
            expansion_result, root_name, phase2_remaining
        )

        state = QuestioningState(
            candidate_pool=candidate_pool,
            confirmed_uuids=confirmed_uuids,
            denied_uuids=denied_uuids,
            condition_points=condition_points,
            protection_counters=protection_counters,
            question_log=[],
            questions_asked=0,
            asked_uuids=set(),
            phase='phase1_variant',
            current_question=None,
            variant_followup_queue=[],
            phase1_remaining=phase1_remaining,
            phase2_remaining=phase2_remaining,
            phase2_count=0,
            finished=False,
            stop_reason='',
            gender=gender,
            age=age,
            discovered_q_count=0,
            prereqs_done=prereqs_done,
        )

        state = self._advance(state)
        return state

    def _build_askable_pool(self, expansion_result, root_name, prereq_qs):
        askable = []
        starting_variants = expansion_result.starting_variants_df

        variants = starting_variants[
            (starting_variants['relation1_type'].notna()) &
            (starting_variants['uuid'].isin(self.data.uuids_with_edges))
        ]
        for relation_type, group in variants.groupby('relation1_type'):
            from engine.config import RELATION_QUESTIONS
            question_text = RELATION_QUESTIONS.get(
                relation_type, f"About the {relation_type}?"
            )
            selection_type = group.iloc[0]['grouping1_selection_type']
            options = []
            for _, row in group.iterrows():
                if pd.notna(row.get('child2_name')):
                    label = f"{row['child1_name']} > {row['child2_name']}"
                elif pd.notna(row.get('child1_name')):
                    label = row['child1_name']
                else:
                    label = row['name']
                options.append({
                    'label': label, 'uuid': row['uuid'], 'name': row['name'],
                })
            askable.append({
                'type': 'variant', 'root_name': root_name,
                'relation_type': relation_type, 'question': question_text,
                'selection_type': selection_type, 'options': options,
                'score_uuid': group.iloc[0]['uuid'],
                'all_uuids': group['uuid'].tolist(),
            })

        discovered = expansion_result.discovered_roots_df.head(
            self.q_config['top_n_discovered']
        )
        for _, row in discovered.iterrows():
            disc_uuid = get_root_uuid(row['root_snomed_name'], self.data)
            if disc_uuid is None or disc_uuid not in self.data.uuids_with_edges:
                continue
            askable.append({
                'type': 'discovered', 'root_name': row['root_snomed_name'],
                'relation_type': None,
                'question': f"Do you have '{row['root_snomed_name']}'?",
                'selection_type': None, 'options': None,
                'score_uuid': disc_uuid, 'all_uuids': [disc_uuid],
            })

        prereq_mode = self.q_config.get('prerequisite_mode', 'off')
        if prereq_mode in ('integrated', 'both'):
            askable.extend(prereq_qs)

        return askable

    def process_answer(self, state, answer):
        q = state.current_question
        if q is None:
            return state

        if q['type'] == 'variant':
            self._process_variant_answer(state, q, answer)
        elif q['type'] == 'discovered':
            self._process_discovered_answer(state, q, answer)
        elif q['type'] == 'prerequisite':
            self._process_prerequisite_answer(state, q, answer)

        state.questions_asked += 1
        state.asked_uuids.add(q['score_uuid'])

        return self._advance(state)

    def _process_variant_answer(self, state, q, selected_indices):
        options = q['options']
        connected_edges = self.data.edges_present_in[
            (self.data.edges_present_in['symptom_uuid'] == q['score_uuid']) &
            (self.data.edges_present_in['condition_snomed_id'].isin(state.candidate_pool))
        ]
        connected_cids = set(connected_edges['condition_snomed_id'].unique())

        if not selected_indices:
            for o in options:
                state.denied_uuids.append(o['uuid'])
            for _, edge in connected_edges.iterrows():
                cid = edge['condition_snomed_id']
                if cid in state.condition_points:
                    psc_w = LIKELIHOOD_SCORES.get(
                        edge['likelihood_symptom_given_condition'], 0
                    )
                    state.condition_points[cid] += (
                        self.ranking_config['no_point'] * psc_w
                    )
            eliminated, state.protection_counters = compute_no_eliminations(
                q['score_uuid'], state.candidate_pool,
                state.protection_counters, self.elim_config, self.data
            )
            state.candidate_pool -= eliminated
            self._log_question(state, q, 'no', connected_cids, eliminated)
        else:
            selected_uuids = set()
            for idx in selected_indices:
                if 0 <= idx < len(options):
                    state.confirmed_uuids.append(options[idx]['uuid'])
                    selected_uuids.add(options[idx]['uuid'])
            for o in options:
                if o['uuid'] not in selected_uuids:
                    state.denied_uuids.append(o['uuid'])
            for _, edge in connected_edges.iterrows():
                cid = edge['condition_snomed_id']
                if cid in state.condition_points:
                    pcs_w = LIKELIHOOD_SCORES.get(
                        edge['likelihood_condition_given_symptom'], 0
                    )
                    state.condition_points[cid] += (
                        self.ranking_config['yes_point'] * pcs_w
                    )
            eliminated, state.protection_counters = compute_yes_eliminations(
                q['score_uuid'], state.candidate_pool, state.confirmed_uuids,
                state.protection_counters, self.elim_config, self.data
            )
            state.candidate_pool -= eliminated
            self._log_question(state, q, 'yes', connected_cids, eliminated)

    def _process_discovered_answer(self, state, q, answer_yes):
        connected_edges = self.data.edges_present_in[
            (self.data.edges_present_in['symptom_uuid'] == q['score_uuid']) &
            (self.data.edges_present_in['condition_snomed_id'].isin(state.candidate_pool))
        ]
        connected_cids = set(connected_edges['condition_snomed_id'].unique())

        if answer_yes:
            state.confirmed_uuids.append(q['score_uuid'])
            for _, edge in connected_edges.iterrows():
                cid = edge['condition_snomed_id']
                if cid in state.condition_points:
                    pcs_w = LIKELIHOOD_SCORES.get(
                        edge['likelihood_condition_given_symptom'], 0
                    )
                    state.condition_points[cid] += (
                        self.ranking_config['yes_point'] * pcs_w
                    )
            eliminated, state.protection_counters = compute_yes_eliminations(
                q['score_uuid'], state.candidate_pool, state.confirmed_uuids,
                state.protection_counters, self.elim_config, self.data
            )
            state.candidate_pool -= eliminated
            self._log_question(state, q, 'yes', connected_cids, eliminated)

            if self.q_config.get('variant_followup_enabled', False):
                followup_qs = build_variant_questions(q['root_name'], self.data)
                scored_fups = []
                for fq in followup_qs:
                    if fq['score_uuid'] in state.asked_uuids:
                        continue
                    fs = compute_question_value(
                        fq['score_uuid'], state.candidate_pool,
                        state.confirmed_uuids, state.protection_counters,
                        self.elim_config, self.q_config, self.data
                    )[0]
                    scored_fups.append((fs, fq))
                scored_fups.sort(key=lambda x: x[0], reverse=True)
                max_fups = self.q_config.get('max_variant_followups', 3)
                state.variant_followup_queue = [
                    fq for _, fq in scored_fups[:max_fups]
                ]
        else:
            state.denied_uuids.append(q['score_uuid'])
            for _, edge in connected_edges.iterrows():
                cid = edge['condition_snomed_id']
                if cid in state.condition_points:
                    psc_w = LIKELIHOOD_SCORES.get(
                        edge['likelihood_symptom_given_condition'], 0
                    )
                    state.condition_points[cid] += (
                        self.ranking_config['no_point'] * psc_w
                    )
            eliminated, state.protection_counters = compute_no_eliminations(
                q['score_uuid'], state.candidate_pool,
                state.protection_counters, self.elim_config, self.data
            )
            state.candidate_pool -= eliminated
            self._log_question(state, q, 'no', connected_cids, eliminated)

        state.discovered_q_count += 1

    def _process_prerequisite_answer(self, state, q, answer_yes):
        affected_in_pool = q['affected_condition_ids'] & state.candidate_pool

        if answer_yes:
            for cid in affected_in_pool:
                if cid in state.condition_points:
                    state.condition_points[cid] += self.ranking_config['yes_point']
            self._log_question(state, q, 'yes', affected_in_pool, set())
        else:
            elim_strengths = self.q_config.get(
                'prerequisite_elim_strengths', ['very_high', 'high']
            )
            to_eliminate = set()
            for _, row in self.data.edges_has_prerequisite[
                (self.data.edges_has_prerequisite['condition_snomed_id_dst']
                 == q['prereq_id']) &
                (self.data.edges_has_prerequisite['condition_snomed_id_src']
                 .isin(state.candidate_pool))
            ].iterrows():
                if row['relation_strength'] in elim_strengths:
                    to_eliminate.add(row['condition_snomed_id_src'])
            state.candidate_pool -= to_eliminate
            for cid in affected_in_pool:
                if cid in state.condition_points:
                    state.condition_points[cid] += self.ranking_config['no_point']
            self._log_question(state, q, 'no', affected_in_pool, to_eliminate)

    def _advance(self, state):
        if state.questions_asked >= self.q_config['max_questions']:
            state.finished = True
            state.stop_reason = 'Maximum questions reached'
            state.current_question = None
            return state

        if len(state.candidate_pool) <= self.q_config['min_pool_size']:
            state.finished = True
            state.stop_reason = (
                f'Pool narrowed to {len(state.candidate_pool)} conditions'
            )
            state.current_question = None
            return state

        if self.q_config['score_threshold'] is not None and state.candidate_pool:
            max_score = max(
                state.condition_points.get(c, 0) for c in state.candidate_pool
            )
            if max_score >= self.q_config['score_threshold']:
                state.finished = True
                state.stop_reason = f'Condition reached score {max_score:.1f}'
                state.current_question = None
                return state

        if state.variant_followup_queue:
            q = state.variant_followup_queue.pop(0)
            if q['score_uuid'] not in state.asked_uuids:
                state.current_question = q
                return state

        if state.phase == 'phase1_variant':
            if state.phase1_remaining:
                q = state.phase1_remaining.pop(0)
                state.current_question = q
                return state
            else:
                prereq_delay = self.q_config.get(
                    'prerequisite_after_n_discovered', 0
                )
                if prereq_delay > 0:
                    state.phase = 'phase3_main'
                else:
                    state.phase = 'phase2_prereq'

        if state.phase == 'phase2_prereq':
            max_prescreens = self.q_config.get('max_prerequisite_prescreens', 3)
            while state.phase2_remaining and state.phase2_count < max_prescreens:
                pq = state.phase2_remaining.pop(0)
                affected_now = pq['affected_condition_ids'] & state.candidate_pool
                if affected_now:
                    pq['affected_condition_ids'] = affected_now
                    state.current_question = pq
                    state.phase2_count += 1
                    return state
            state.phase = 'phase3_main'

        if state.phase == 'phase3_main':
            prereq_delay = self.q_config.get(
                'prerequisite_after_n_discovered', 0
            )
            prereq_mode = self.q_config.get('prerequisite_mode', 'off')
            if (prereq_delay > 0 and
                    not state.prereqs_done and
                    state.discovered_q_count >= prereq_delay and
                    prereq_mode in ('pre_screen', 'both')):
                cf_mode = self.q_config.get('prerequisite_cf_mode', 'static')
                state.phase2_remaining = build_prerequisite_questions(
                    state.candidate_pool, state.gender, self.data,
                    state.confirmed_uuids, cf_mode
                )
                state.phase2_count = 0
                state.prereqs_done = True
                if state.phase2_remaining:
                    max_prescreens = self.q_config.get(
                        'max_prerequisite_prescreens', 3
                    )
                    while (state.phase2_remaining and
                           state.phase2_count < max_prescreens):
                        pq = state.phase2_remaining.pop(0)
                        if pq['score_uuid'] in state.asked_uuids:
                            continue
                        affected_now = (
                            pq['affected_condition_ids'] & state.candidate_pool
                        )
                        if affected_now:
                            pq['affected_condition_ids'] = affected_now
                            state.current_question = pq
                            state.phase2_count += 1
                            return state

            best = self._score_and_pick_best(state)
            if best is None:
                state.finished = True
                state.stop_reason = 'No more valuable questions'
                state.current_question = None
                return state
            state.current_question = best
            return state

        state.finished = True
        state.stop_reason = 'Unexpected state'
        state.current_question = None
        return state

    def _score_and_pick_best(self, state):
        scored = []
        for q in self._askable_pool:
            if q['score_uuid'] in state.asked_uuids:
                continue
            if q['type'] == 'prerequisite':
                affected_now = q['affected_condition_ids'] & state.candidate_pool
                if affected_now:
                    scored.append((len(affected_now), q))
                continue
            score, ye, ne, conn, p_yes = compute_question_value(
                q['score_uuid'], state.candidate_pool, state.confirmed_uuids,
                state.protection_counters, self.elim_config, self.q_config,
                self.data
            )
            if score > self.q_config['min_question_score'] or ye > 0 or ne > 0:
                scored.append((score, q))

        if not scored:
            return None

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def get_live_top_n(self, state, n=5):
        if not state.candidate_pool:
            return []

        from engine.ranking import get_age_bracket_column, get_gender_column
        gender_col = get_gender_column(state.gender)
        age_col = get_age_bracket_column(state.age)

        rows = []
        for cid in state.candidate_pool:
            yn = state.condition_points.get(cid, 0)

            confirmed_edges = self.data.edges_present_in[
                (self.data.edges_present_in['symptom_uuid']
                 .isin(state.confirmed_uuids)) &
                (self.data.edges_present_in['condition_snomed_id'] == cid)
            ]
            pcs = confirmed_edges[
                'likelihood_condition_given_symptom'
            ].map(LIKELIHOOD_SCORES).sum() if len(confirmed_edges) > 0 else 0
            matches = (
                confirmed_edges['symptom_uuid'].nunique()
                if len(confirmed_edges) > 0 else 0
            )

            cond = self.data.nodes_condition[
                self.data.nodes_condition['snomed_id'] == cid
            ]
            if len(cond) == 0:
                continue
            name = cond.iloc[0]['name']
            triage = cond.iloc[0]['triage_level']

            g_w = cond.iloc[0][gender_col]
            a_w = cond.iloc[0][age_col]
            g_w = g_w if pd.notna(g_w) else 1.0
            a_w = a_w if pd.notna(a_w) else 1.0

            pc = LIKELIHOOD_SCORES.get(cond.iloc[0]['overall_likelihood'], 0)

            final = (yn + pcs) * pc * float(g_w) * float(a_w)

            rows.append({
                'condition_name': name,
                'triage_level': triage,
                'yn_points': round(yn, 2),
                'pcs_score': round(pcs, 2),
                'pc_weight': round(pc, 4),
                'final_score': round(final, 2),
                'num_matches': matches,
            })

        rows.sort(key=lambda x: x['final_score'], reverse=True)
        return rows[:n]

    def _log_question(self, state, q, answer_type, connected_cids, eliminated):
        def _get_name(cid):
            row = self.data.nodes_condition[
                self.data.nodes_condition['snomed_id'] == cid
            ]
            return row.iloc[0]['name'] if len(row) > 0 else 'Unknown'

        state.question_log.append({
            'order': state.questions_asked + 1,
            'type': q['type'],
            'question': q.get('question', ''),
            'answer': answer_type,
            'eliminated': len(eliminated),
            'pool_after': len(state.candidate_pool),
            'connected': ', '.join(
                _get_name(c) for c in list(connected_cids)[:5]
            ),
        })
