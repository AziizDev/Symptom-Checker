import copy
from engine.config import ELIM_CONFIG, RANKING_CONFIG, QUESTIONING_CONFIG, QUESTION_BUDGET


PRESETS = {
    'Standard': {
        'max_questions': 10,
        'protection_enabled': True,
        'triage_protection': False,
        'min_pool_size': 3,
        'score_threshold': 10,
        'variant_followup_enabled': True,
        'max_variant_followups': 3,
        'prerequisite_mode': 'pre_screen',
        'max_prerequisite_prescreens': 3,
        'budget_mode': 'full',
        'budget_global_max': 14,
        'budget_adaptive_max': 2,
        'budget_screening_max': 2,
    },
    'Safety-first': {
        'max_questions': 15,
        'protection_enabled': True,
        'triage_protection': True,
        'min_pool_size': 2,
        'score_threshold': 15,
        'variant_followup_enabled': True,
        'max_variant_followups': 3,
        'prerequisite_mode': 'pre_screen',
        'max_prerequisite_prescreens': 4,
        'budget_mode': 'full',
        'budget_global_max': 18,
        'budget_adaptive_max': 2,
        'budget_screening_max': 2,
    },
    'Quick screen': {
        'max_questions': 6,
        'protection_enabled': True,
        'triage_protection': False,
        'min_pool_size': 5,
        'score_threshold': 7,
        'variant_followup_enabled': True,
        'max_variant_followups': 2,
        'prerequisite_mode': 'off',
        'max_prerequisite_prescreens': 0,
        'budget_mode': 'base_only',
        'budget_global_max': 6,
        'budget_adaptive_max': 0,
        'budget_screening_max': 0,
    },
}


def get_merged_config(preset_name, overrides=None):
    preset = PRESETS.get(preset_name, PRESETS['Standard'])

    elim = copy.deepcopy(ELIM_CONFIG)
    elim['protection_enabled'] = preset['protection_enabled']
    elim['triage_protection'] = preset['triage_protection']

    ranking = copy.deepcopy(RANKING_CONFIG)

    questioning = copy.deepcopy(QUESTIONING_CONFIG)
    questioning['max_questions'] = preset['max_questions']
    questioning['min_pool_size'] = preset['min_pool_size']
    questioning['score_threshold'] = preset['score_threshold']
    questioning['variant_followup_enabled'] = preset['variant_followup_enabled']
    questioning['max_variant_followups'] = preset['max_variant_followups']
    questioning['prerequisite_mode'] = preset['prerequisite_mode']
    questioning['max_prerequisite_prescreens'] = preset['max_prerequisite_prescreens']

    budget = copy.deepcopy(QUESTION_BUDGET)
    budget['mode'] = preset.get('budget_mode', budget['mode'])
    budget['global_max'] = preset.get('budget_global_max', budget['global_max'])
    budget['adaptive_max'] = preset.get('budget_adaptive_max', budget['adaptive_max'])
    budget['screening_max'] = preset.get('budget_screening_max', budget['screening_max'])

    if overrides:
        for key, val in overrides.items():
            if key in questioning:
                questioning[key] = val
            elif key in elim:
                elim[key] = val
            elif key in ranking:
                ranking[key] = val
            elif key.startswith('budget_'):
                budget_key = key.replace('budget_', '')
                if budget_key in budget:
                    budget[budget_key] = val

    return {
        'elim': elim,
        'ranking': ranking,
        'questioning': questioning,
        'budget': budget,
    }
