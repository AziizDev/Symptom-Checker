LIKELIHOOD_SCORES = {
    'very_high': 0.8,
    'high':      0.65,
    'medium':    0.5,
    'low':       0.35,
    'rare':      0.2,
    'zero':      0.0,
}

LIKELIHOOD_SCORES_COMPRESSED = {
    'very_high': 0.8,
    'high':      0.65,
    'medium':    0.5,
    'low':       0.35,
    'rare':      0.2,
    'zero':      0.0,
}

ELIM_CONFIG = {
    'yes_eliminate_unconnected': True,
    'no_eliminate_psc_levels': ['very_high', 'high'],
    'protection_enabled': True,
    'protection_pcs_levels': ['very_high', 'high'],
    'protection_increment': 0.2,
    'protection_threshold': 0.6,
    'triage_protection': False,
    'triage_always_protect': ['emergency'],
    'triage_protection_increment': 0.2,
}

RANKING_CONFIG = {
    'yes_point': 1.0,
    'no_point': -0.2,
    'demographic_method': 'addition',
}

QUESTION_BUDGET = {
    'mode': 'full',            # 'full' | 'no_adaptive' | 'base_only'
    'global_max': 13,          # hard ceiling across ALL question phases
    'adaptive_max': 2,         # max adaptive extra Qs (used in 'full' mode)
    'screening_max': 2,        # max red-flag screening Qs total (used in 'full' and 'no_adaptive')
}

QUESTIONING_CONFIG = {
    'max_questions': 9,
    'top_n_discovered': 20,
    'min_pool_size': 3,
    'min_question_score': 0.0,
    'score_threshold': 10,
    'question_scoring_method': 'normalized_symptom_score',
    'variant_followup_enabled': True,
    'max_variant_followups': 3,
    'prerequisite_mode': 'pre_screen',
    'max_prerequisite_prescreens': 3,
    'prerequisite_elim_strengths': ['very_high', 'high'],
    'prerequisite_after_n_discovered': 0,
    'prerequisite_cf_mode': 'dynamic',
}

RELATION_QUESTIONS = {
    'duration_since':    'How long have you had this symptom?',
    'location':          'Where is it located?',
    'severity':          'How severe is it?',
    'onset':             'How did it start?',
    'pain_type':         'What type of pain is it?',
    'characteristic':    'What are the characteristics?',
    'aggravated':        'What makes it worse?',
    'relieved':          'What makes it better?',
    'radiating':         'Does it radiate anywhere?',
    'temporal_pattern':  'What is the pattern over time?',
    'duration_lasts':    'How long does each episode last?',
    'laterality':        'Which side is it on?',
}

RED_FLAG_CONFIG = {
    'enabled': True,
    'bonus': 1.0,
    'screening_top_n': 5,
}

RED_FLAG_MAP = {
    82272006: {
        'name': 'Common Cold / Acute Rhinitis',
        'triggers': [
            {'flag': 'High fever (>39C)',            'match_roots': [], 'match_variants': ['Fever <severity> severe (104 < x)']},
            {'flag': 'Shortness of breath',          'match_roots': ['Breathlessness']},
            {'flag': 'Chest pain',                   'match_roots': ['Chest pain']},
            {'flag': 'Severe ear pain or headache',  'match_roots': [], 'match_variants': ['Headache <severity> severe', 'Ear pain <severity> severe']},
        ],
        'screening_questions': [],
        'referral_rules': None,
    },
    235595009: {
        'name': 'Gastroesophageal reflux disease',
        'triggers': [
            {'flag': 'Dysphagia',              'match_roots': ['Dysphagia']},
            {'flag': 'Chest pain',             'match_roots': ['Chest pain']},
            {'flag': 'Vomiting',               'match_roots': ['Vomit']},
            {'flag': 'Blood in vomit',         'match_roots': [], 'match_variants': ['Vomit <char> bloody in vomit']},
            {'flag': 'Abdominal pain (severe)', 'match_roots': [], 'match_variants': ['Abdominal pain <severity> severe']},
        ],
        'screening_questions': [
            {'flag': 'Odynophagia (pain on swallowing)',  'question': 'Do you experience pain when swallowing (odynophagia)?'},
            {'flag': 'Unexplained weight loss',           'question': 'Have you had unexplained weight loss recently?'},
            {'flag': 'Melena (black tarry stools)',       'question': 'Have you noticed black, tarry stools?'},
            {'flag': 'Anemia symptoms',                   'question': 'Have you been told you have anemia, or do you feel unusually tired and pale?'},
            {'flag': 'Pain radiating to arm or jaw',      'question': 'Does the pain radiate to your arm or jaw?'},
        ],
        'referral_rules': {
            'emergency': {
                'any_flags': ['Blood in vomit', 'Melena (black tarry stools)'],
                'combo': {'flags': ['Chest pain', 'Pain radiating to arm or jaw'], 'require_all': True},
            },
            'urgent_clinic': {
                'any_flags': ['Dysphagia', 'Odynophagia (pain on swallowing)',
                              'Unexplained weight loss', 'Anemia symptoms'],
            },
        },
    },
    398057008: {
        'name': 'Tension-type headache',
        'triggers': [
            {'flag': 'Thunderclap headache',  'match_roots': [], 'match_variants': ['Headache <char> thunderclap']},
        ],
        'screening_questions': [
            {'flag': 'Headache with neurological signs',
             'question': 'Do you have any neurological symptoms such as vision changes, numbness, weakness, or difficulty speaking?'},
            {'flag': 'Triggered by cough/sneeze/straining/position change',
             'question': 'Is your headache triggered or worsened by coughing, sneezing, straining, or changing position?'},
            {'flag': 'New headache onset after age 50',
             'question': 'Is this a new type of headache that started after age 50?'},
        ],
        'referral_rules': None,
    },
}

PREREQUISITE_QUESTIONS = {
    'Pregnant':                            'Are you currently pregnant?',
    'Alcoholic (current consumer)':        'Do you consume alcohol regularly?',
    'Diabetes Type 2':                     'Have you been diagnosed with Type 2 Diabetes?',
    'Diabetes mellitus type 1':            'Have you been diagnosed with Type 1 Diabetes?',
    'Hypertension':                        'Do you have high blood pressure (hypertension)?',
    'H/O Trauma':                          'Have you had any recent physical trauma or injury?',
    'Unprotected sexual intercourse':      'Have you had unprotected sexual intercourse recently?',
    'Uncircumcised':                       'Are you uncircumcised?',
    'H/O: chickenpox':                     'Have you had chickenpox before?',
    'H/O COVID-19':                        'Have you had COVID-19?',
    'Missed period':                       'Have you missed your period recently?',
    'recent childbirth':                   'Have you given birth recently?',
    'Exposure to cold':                    'Have you been exposed to extreme cold recently?',
    'High altitude':                       'Are you at or recently been at high altitude?',
    'Bite of domestic animal':             'Have you been bitten by an animal recently?',
    'Seizure':                             'Have you had a seizure recently?',
    'Taken a vaccine':                     'Have you recently received a vaccine?',
    'Intake of drug':                      'Have you recently started any new medication?',
    'Frequent use of nasal decongestants': 'Do you frequently use nasal decongestant sprays?',
    'H/O fracture':                        'Have you had a bone fracture before?',
    'Injury of head':                      'Have you had a recent head injury?',
    'Injury of shoulder region':           'Have you had a recent shoulder injury?',
    'Injury to elbow':                     'Have you had a recent elbow injury?',
    'Injury of hip':                       'Have you had a recent hip injury?',
    'Injury of ear':                       'Have you had a recent ear injury?',
}
