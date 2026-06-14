import streamlit as st
from engine.data_loader import load_all_data
from engine.expansion import symptom_expansion
from engine.questioning import QuestioningEngine
from engine.presets import get_merged_config


def render():
    data = load_all_data()

    doctor = st.session_state.get('doctor', {})
    doctor_name = doctor.get('name', '')
    greeting = f", {doctor_name}" if doctor_name and doctor_name != 'Local User' else ""

    st.markdown(
        f"""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="margin-bottom: 0; color: #0f172a;">
                Symptom Checker Engine
            </h1>
            <p style="color: #64748b; font-size: 1.1em; margin-top: 4px;">
                Welcome{greeting}! Describe your symptoms below.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    symptom = st.selectbox(
        "What symptom are you experiencing?",
        options=[''] + data.symptom_names,
        index=0,
        placeholder="Type to search...",
        key='symptom_input',
    )

    col1, col2 = st.columns(2)
    with col1:
        gender = st.radio(
            "Gender", ["Male", "Female"], horizontal=True, key='gender_input',
        )
    with col2:
        age = st.number_input(
            "Age", min_value=1, max_value=120, value=25, key='age_input',
        )

    st.markdown("")

    if st.button(
        "Start Assessment", type="primary", use_container_width=True,
        disabled=(not symptom),
    ):
        with st.spinner("Analyzing symptom and building question pool..."):
            expansion = symptom_expansion(symptom, data)
            if expansion is None:
                st.error(
                    f"Symptom '{symptom}' not found in the knowledge base."
                )
                return

            preset = st.session_state.get('preset', 'Standard')
            overrides = st.session_state.get('config_overrides', None)
            config = get_merged_config(preset, overrides)

            gender_code = 'M' if gender == 'Male' else 'F'
            engine = QuestioningEngine(data, config)
            state = engine.initialize(expansion, gender_code, age)

        from db.models import create_session
        doctor_id = st.session_state.get('doctor', {}).get('id')
        session_id = create_session(
            doctor_id, symptom, gender_code, age, preset,
        )
        st.session_state.db_session_id = session_id

        st.session_state.engine = engine
        st.session_state.state = state
        st.session_state.expansion = expansion
        st.session_state.gender = gender_code
        st.session_state.age = age
        st.session_state.page = 'questioning'
        st.rerun()
