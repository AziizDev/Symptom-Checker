import copy
from engine.config import ELIM_CONFIG, RANKING_CONFIG, QUESTIONING_CONFIG


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

    if overrides:
        for key, val in overrides.items():
            if key in questioning:
                questioning[key] = val
            elif key in elim:
                elim[key] = val
            elif key in ranking:
                ranking[key] = val

    return {
        'elim': elim,
        'ranking': ranking,
        'questioning': questioning,
    }
