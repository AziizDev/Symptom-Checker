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

QUESTIONING_CONFIG = {
    'max_questions': 10,
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
    'prerequisite_after_n_discovered': 3,
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
