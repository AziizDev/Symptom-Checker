import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Symptom Checker Engine",
    page_icon="⚕",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .stApp p, .stApp span, .stApp label, .stApp div {
        color: #1e293b;
    }
    .stApp h1, .stApp h2, .stApp h3 {
        color: #0f172a !important;
    }
    .stApp .stCaption, .stApp .stCaption p {
        color: #64748b !important;
    }

    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px;
        padding: 0.6em 1.2em;
        font-weight: 600;
    }
    .stButton>button[kind="primary"]:hover {
        box-shadow: 0 4px 12px rgba(37,99,235,0.3);
    }
    .stButton>button[kind="secondary"],
    .stButton>button:not([kind="primary"]) {
        border-radius: 8px;
        padding: 0.6em 1.2em;
        font-weight: 500;
        background: #f1f5f9 !important;
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important;
    }

    .stProgress > div > div {
        background: linear-gradient(90deg, #2563eb, #3b82f6) !important;
        border-radius: 10px;
    }

    div[data-testid="stExpander"] {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
    }

    .stRadio label, .stCheckbox label {
        color: #334155 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Auth check first (populates doctor in session_state) ---
from engine.presets import PRESETS
from ui.auth import check_auth

is_authenticated = check_auth()

# --- Sidebar ---
with st.sidebar:
    if 'doctor' in st.session_state:
        doctor = st.session_state.doctor
        if doctor.get('id') != 'local':
            st.markdown(f"**{doctor['name']}**")
            st.caption(doctor.get('email', ''))
            if st.button("Not you? Switch", key="switch_doctor"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.query_params.clear()
                st.session_state.page = 'auth'
                st.rerun()
            st.divider()

    show_admin = False
    try:
        admin_pin = st.secrets["admin"]["pin"]
    except (KeyError, FileNotFoundError):
        admin_pin = None
        show_admin = True

    if admin_pin is not None and not show_admin:
        with st.expander("Admin"):
            pin_input = st.text_input(
                "PIN", type="password", key="admin_pin_input",
            )
            if pin_input == admin_pin:
                show_admin = True

    if show_admin:
        st.header("Configuration")

        preset = st.selectbox(
            "Assessment Mode",
            options=list(PRESETS.keys()),
            index=0,
            key='preset_select',
        )

        if 'preset' not in st.session_state:
            st.session_state.preset = preset

        if st.session_state.preset != preset:
            page_was = st.session_state.get('page', 'intake')
            if page_was not in ('intake', 'auth'):
                for key in list(st.session_state.keys()):
                    if key not in (
                        'preset', 'preset_select', 'doctor',
                        'admin_pin_input',
                    ):
                        del st.session_state[key]
                st.session_state.page = 'intake'
            st.session_state.preset = preset

        preset_desc = {
            'Standard': 'Balanced assessment with 10 questions.',
            'Safety-first': 'More thorough. 15 questions, triage protection.',
            'Quick screen': 'Fast triage with 6 questions.',
        }
        st.caption(preset_desc.get(preset, ''))

        with st.expander("Advanced Settings"):
            overrides = {}
            p = PRESETS[preset]

            max_q = st.slider(
                "Max questions", 5, 20, p['max_questions'],
                key='adv_max_q',
            )
            if max_q != p['max_questions']:
                overrides['max_questions'] = max_q

            min_pool = st.slider(
                "Min pool size", 2, 10, p['min_pool_size'],
                key='adv_min_pool',
            )
            if min_pool != p['min_pool_size']:
                overrides['min_pool_size'] = min_pool

            score_thresh = st.slider(
                "Score threshold", 5, 20, p['score_threshold'],
                key='adv_score_thresh',
            )
            if score_thresh != p['score_threshold']:
                overrides['score_threshold'] = score_thresh

            protection = st.checkbox(
                "Protection enabled", value=p['protection_enabled'],
                key='adv_protection',
            )
            if protection != p['protection_enabled']:
                overrides['protection_enabled'] = protection

            triage_prot = st.checkbox(
                "Triage protection", value=p['triage_protection'],
                key='adv_triage',
            )
            if triage_prot != p['triage_protection']:
                overrides['triage_protection'] = triage_prot

            variant_fup = st.checkbox(
                "Variant follow-up", value=p['variant_followup_enabled'],
                key='adv_variant',
            )
            if variant_fup != p['variant_followup_enabled']:
                overrides['variant_followup_enabled'] = variant_fup

            prereq_mode = st.selectbox(
                "Prerequisite mode",
                ['off', 'pre_screen', 'integrated', 'both'],
                index=['off', 'pre_screen', 'integrated', 'both'].index(
                    p['prerequisite_mode']
                ),
                key='adv_prereq',
            )
            if prereq_mode != p['prerequisite_mode']:
                overrides['prerequisite_mode'] = prereq_mode

            if overrides:
                st.session_state.config_overrides = overrides
            elif 'config_overrides' in st.session_state:
                del st.session_state['config_overrides']
    else:
        if 'preset' not in st.session_state:
            st.session_state.preset = 'Standard'

    st.divider()
    st.caption("Symptom Checker Engine v6")

# --- Page routing ---
from ui import intake, questioning, results, auth

page = st.session_state.get('page', 'intake')

if not is_authenticated:
    auth.render()
elif page == 'questioning':
    questioning.render()
elif page == 'results':
    results.render()
else:
    intake.render()
