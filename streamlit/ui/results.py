import streamlit as st
import pandas as pd

from engine.data_loader import load_all_data
from engine.ranking import rank_conditions
from engine.config import RED_FLAG_MAP, RED_FLAG_CONFIG
from ui.components import (
    render_condition_card, triage_badge_html, triage_color,
    TRIAGE_COLORS, TRIAGE_LABELS, TRIAGE_BG_LIGHT,
    render_metric_card, render_section_header,
    render_condition_network, render_speciality_breakdown,
)

# Columns hidden from the Question Log view. They stay in state.question_log
# (audit trail / DB), we just don't show them.
QUESTION_LOG_HIDDEN = ['connected', 'pool_after', 'answer']

TOP_N = 5


def render():
    data = load_all_data()
    state = st.session_state.state
    engine = st.session_state.engine

    result_df, detail_df = rank_conditions(
        state.confirmed_uuids, state.denied_uuids, state.candidate_pool,
        state.condition_points, state.age, state.gender, data,
        engine.ranking_config,
    )

    rf = state.red_flag_results
    bonus = RED_FLAG_CONFIG.get('bonus', 1.0)
    for cid, flags in rf.get('triggered', {}).items():
        n_flags = len(flags)
        pc = result_df.loc[result_df['condition_snomed_id'] == cid, 'pc_weight']
        if len(pc) > 0:
            total_bonus = n_flags * bonus * pc.values[0]
            idx = result_df.index[result_df['condition_snomed_id'] == cid]
            result_df.loc[idx, 'final_score'] += total_bonus
    if rf.get('triggered'):
        result_df.sort_values('final_score', ascending=False, inplace=True)
        result_df.reset_index(drop=True, inplace=True)

    if not st.session_state.get('results_logged'):
        from db.models import log_results
        session_id = st.session_state.get('db_session_id')
        if session_id and len(result_df) > 0:
            rows = []
            for rank_pos, row in result_df.iterrows():
                rows.append({
                    'session_id': session_id,
                    'rank_position': rank_pos + 1,
                    'condition_snomed_id': int(row['condition_snomed_id']),
                    'condition_name': row['condition_name'],
                    'final_score': round(float(row['final_score']), 4),
                    'yn_points': round(float(row['yn_points']), 4),
                    'pcs_score': round(float(row['pcs_score']), 4),
                    'triage_level': row['triage_level'],
                    'num_symptom_matches': int(row['num_symptom_matches']),
                })
            log_results(session_id, rows)
            st.session_state.results_logged = True

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1e3a5f 0%, #1d4ed8 100%);
            border-radius: 12px;
            padding: 30px 24px;
            margin-bottom: 24px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(30,58,95,0.2);
        ">
            <div style="font-size:1.5em;font-weight:700;color:#ffffff;
                        margin-bottom:6px;">
                Assessment Complete
            </div>
            <div style="font-size:0.9em;color:#bfdbfe;font-weight:400;">
                {state.stop_reason}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_summary, tab_engine = st.tabs(["Clinical Summary", "Engine Detail"])

    with tab_summary:
        _render_clinical_summary(state, result_df)

    with tab_engine:
        _render_engine_detail(state, result_df, detail_df, data)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    if st.button(
        "Start New Assessment", type="primary",
        use_container_width=True,
    ):
        doctor = st.session_state.get('doctor')
        preset = st.session_state.get('preset', 'Standard')
        for key in list(st.session_state.keys()):
            if key not in (
                'doctor', 'preset', 'preset_select', 'admin_pin_input',
            ):
                del st.session_state[key]
        if doctor:
            st.session_state.doctor = doctor
        st.session_state.preset = preset
        st.session_state.page = 'intake'
        st.rerun()


# --------------------------------------------------------------------------
# Clinical Summary — the doctor-facing note. No engine internals here:
# no scores, no pool sizes, no network graph. See Engine Detail for those.
# --------------------------------------------------------------------------

def _render_clinical_summary(state, result_df):
    gender = 'Male' if str(state.gender).upper().startswith('M') else 'Female'
    chief = getattr(state, 'chief_complaint', '') or '-'

    st.markdown(
        f"""
        <div style="border:1px solid #e2e8f0;border-radius:10px;
                    background:#ffffff;padding:18px 22px;margin-bottom:18px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <div style="display:flex;gap:32px;flex-wrap:wrap;">
                <div>
                    <div style="{_LABEL}">Age</div>
                    <div style="{_VALUE}">{state.age}</div>
                </div>
                <div>
                    <div style="{_LABEL}">Gender</div>
                    <div style="{_VALUE}">{gender}</div>
                </div>
                <div style="flex:1;min-width:200px;">
                    <div style="{_LABEL}">Chief Complaint</div>
                    <div style="{_VALUE}">{chief}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top = result_df.head(TOP_N)

    # --- Specialities ------------------------------------------------------
    # Sits directly under the patient header, before History (manager's call).
    if len(top) > 0:
        render_section_header(
            "Suggested Specialities",
            f"Specialities covering the top {len(top)} conditions. "
            "Click one to see its conditions",
        )
        render_speciality_breakdown(top.to_dict('records'))

    # --- History -----------------------------------------------------------
    # NOTE: chronological transcript for now. Planned change (after manager
    # review): regroup into positive findings then pertinent negatives.
    render_section_header(
        "History",
        "Questions asked and the answers given, in order",
    )

    if state.question_log:
        rows_html = ""
        for entry in state.question_log:
            root = entry.get('root_symptom', '-')
            root_html = (
                f'<div style="font-size:0.78em;color:#94a3b8;margin-top:2px;">'
                f're: {root}</div>' if root and root != '-' else ''
            )
            answer = entry.get('answer_detail') or entry.get('answer', '')
            is_no = str(answer).lower() in ('no', 'none of these')
            a_color = '#64748b' if is_no else '#0f172a'
            a_weight = '500' if is_no else '700'
            rows_html += f"""
            <tr>
                <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;
                           color:#94a3b8;font-size:0.85em;width:28px;
                           vertical-align:top;">
                    {entry.get('order', '')}
                </td>
                <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;
                           color:#334155;font-size:0.9em;">
                    {entry.get('question', '')}
                    {root_html}
                </td>
                <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;
                           color:{a_color};font-size:0.9em;font-weight:{a_weight};
                           text-align:right;white-space:nowrap;">
                    {answer}
                </td>
            </tr>
            """
        st.markdown(
            f"""
            <div style="border:1px solid #e2e8f0;border-radius:10px;
                        overflow:hidden;background:#ffffff;
                        box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <table style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr style="background:#f1f5f9;">
                            <th style="{_TH}">#</th>
                            <th style="{_TH}">Question</th>
                            <th style="{_TH}text-align:right;">Answer</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption("No questions were asked.")

    # --- Differential ------------------------------------------------------
    # Deliberately NOT called "Assessment": that word means the clinician's own
    # judgement. This is an engine-suggested list, and it is labelled as such.
    render_section_header(
        "Suggested Differential",
        "Decision support only, not a diagnosis",
    )

    if len(top) > 0:
        rows_html = ""
        for i, row in top.iterrows():
            spec = row.get('speciality') or '-'
            rows_html += f"""
            <tr>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;
                           width:30px;">
                    <span style="background:#f1f5f9;color:#475569;width:24px;
                                 height:24px;border-radius:50%;display:inline-flex;
                                 align-items:center;justify-content:center;
                                 font-weight:700;font-size:0.75em;">
                        {i + 1}
                    </span>
                </td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;
                           color:#0f172a;font-weight:600;font-size:0.95em;">
                    {row['condition_name']}
                </td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;
                           color:#475569;font-size:0.85em;">
                    {spec}
                </td>
                <td style="padding:12px;border-bottom:1px solid #f1f5f9;
                           text-align:right;">
                    {triage_badge_html(row['triage_level'])}
                </td>
            </tr>
            """
        st.markdown(
            f"""
            <div style="border:1px solid #e2e8f0;border-radius:10px;
                        overflow:hidden;background:#ffffff;
                        box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <table style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr style="background:#f1f5f9;">
                            <th style="{_TH}">#</th>
                            <th style="{_TH}">Diagnosis</th>
                            <th style="{_TH}">Speciality</th>
                            <th style="{_TH}text-align:right;">Triage</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.warning("No conditions survived the elimination process.")

    st.markdown(
        """
        <div style="margin-top:22px;padding:12px 16px;background:#f8fafc;
                    border:1px solid #e2e8f0;border-radius:8px;
                    font-size:0.82em;color:#64748b;line-height:1.5;">
            This summary is generated by an automated symptom checker and is
            intended as clinical decision support. It is not a diagnosis and
            does not replace clinical judgement.
        </div>
        """,
        unsafe_allow_html=True,
    )


_LABEL = (
    "font-size:0.7em;color:#94a3b8;font-weight:700;text-transform:uppercase;"
    "letter-spacing:0.5px;margin-bottom:3px;"
)
_VALUE = "font-size:1em;color:#0f172a;font-weight:600;"

_TH = (
    "padding:10px 12px;text-align:left;font-size:0.72em;color:#64748b;"
    "font-weight:700;text-transform:uppercase;letter-spacing:0.5px;"
)


# --------------------------------------------------------------------------
# Engine Detail — everything the engine did. This is the debug view.
# --------------------------------------------------------------------------

def _render_engine_detail(state, result_df, detail_df, data):
    total = len(st.session_state.expansion.condition_ids)
    eliminated = total - len(state.candidate_pool)

    cols = st.columns(4)
    with cols[0]:
        render_metric_card("Questions", state.questions_asked, color="#2563eb")
    with cols[1]:
        render_metric_card("Survived", len(state.candidate_pool), color="#16a34a")
    with cols[2]:
        render_metric_card("Confirmed", len(state.confirmed_uuids), color="#7c3aed")
    with cols[3]:
        render_metric_card("Eliminated", eliminated, color="#dc2626")

    render_section_header(
        "Top Conditions",
        f"Top {TOP_N} of {len(result_df)} conditions scored and ranked"
    )

    if len(result_df) > 0:
        max_score = result_df.iloc[0]['final_score']
        for i, row in result_df.head(TOP_N).iterrows():
            render_condition_card(row, i + 1, max_score=max_score)

        if len(result_df) > TOP_N:
            with st.expander(
                f"All Ranked Conditions ({len(result_df)} total)"
            ):
                for i, row in result_df.iterrows():
                    render_condition_card(row, i + 1, max_score=max_score)

        render_section_header(
            "Specialities",
            f"Specialities of the top {TOP_N} conditions. "
            "Click one to see its conditions",
        )
        render_speciality_breakdown(result_df.head(TOP_N).to_dict('records'))
    else:
        st.warning("No conditions survived the elimination process.")

    rf = state.red_flag_results
    if rf.get('triggered'):
        render_section_header(
            "Red Flag Alerts",
            "Clinical red flags detected during screening"
        )
        for cid, flags in rf['triggered'].items():
            cname = RED_FLAG_MAP.get(cid, {}).get('name', f'Condition {cid}')
            flags_html = ''.join(
                f'<li style="margin:4px 0;color:#991b1b;">{f}</li>'
                for f in flags
            )
            st.markdown(
                f"""
                <div style="background:#fef2f2;border:1px solid #fecaca;
                            border-left:4px solid #dc2626;border-radius:8px;
                            padding:14px 18px;margin-bottom:12px;">
                    <div style="font-weight:700;color:#991b1b;font-size:1em;
                                margin-bottom:6px;">
                        {cname}
                    </div>
                    <ul style="margin:0;padding-left:20px;font-size:0.9em;">
                        {flags_html}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

    render_section_header(
        "Symptom-Condition Network",
        "Blue diamonds = confirmed symptoms. "
        "Circles = conditions colored by triage level."
    )
    if len(result_df) > 0:
        render_condition_network(
            result_df.head(10).to_dict('records'),
            state.confirmed_uuids, data,
        )

    render_section_header("Confirmed Symptoms")
    confirmed_df = data.nodes_symptom[
        data.nodes_symptom['uuid'].isin(state.confirmed_uuids)
    ][['root_snomed_name', 'name', 'triage_level']].reset_index(drop=True)

    rows_html = ""
    for _, r in confirmed_df.iterrows():
        rows_html += f"""
        <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;
                       color:#0f172a;font-weight:500;font-size:0.9em;">
                {r['root_snomed_name']}
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;
                       color:#475569;font-size:0.88em;">
                {r['name']}
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #f1f5f9;">
                {triage_badge_html(r['triage_level'])}
            </td>
        </tr>
        """
    st.markdown(
        f"""
        <div style="border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;
                    margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
            <table style="width:100%;border-collapse:collapse;background:#ffffff;">
                <thead>
                    <tr style="background:#f1f5f9;">
                        <th style="padding:10px 12px;text-align:left;font-size:0.72em;
                                   color:#64748b;font-weight:700;text-transform:uppercase;
                                   letter-spacing:0.5px;">Root Symptom</th>
                        <th style="padding:10px 12px;text-align:left;font-size:0.72em;
                                   color:#64748b;font-weight:700;text-transform:uppercase;
                                   letter-spacing:0.5px;">Variant</th>
                        <th style="padding:10px 12px;text-align:left;font-size:0.72em;
                                   color:#64748b;font-weight:700;text-transform:uppercase;
                                   letter-spacing:0.5px;">Triage</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Scoring Detail"):
        if len(detail_df) > 0:
            st.dataframe(detail_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No scoring details available.")

    with st.expander("Question Log"):
        if state.question_log:
            chief = getattr(state, 'chief_complaint', '') or '-'
            st.markdown(
                f"""
                <div style="padding:8px 12px;margin-bottom:10px;
                            background:#f1f5f9;border-radius:6px;
                            font-size:0.88em;color:#334155;">
                    <span style="color:#64748b;font-weight:600;">
                        Chief Complaint (CC):
                    </span>
                    <span style="font-weight:700;color:#0f172a;">{chief}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            log_df = pd.DataFrame(state.question_log)
            # Display copy only — the hidden columns remain in question_log.
            view_df = log_df.drop(
                columns=[c for c in QUESTION_LOG_HIDDEN if c in log_df.columns]
            ).rename(columns={'answer_detail': 'answer'})
            st.dataframe(view_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No questions were asked.")

    # --- Evaluation Section ---
    # TEMPORARILY DISABLED (testing): doctor evaluation form.
    # To re-enable, uncomment the block below. The "Start New Assessment"
    # button lives in render(), below the tabs.
    #
    # st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    # render_section_header(
    #     "Evaluation",
    #     "Please evaluate this assessment before starting a new one"
    # )
    #
    # evaluation_submitted = st.session_state.get('evaluation_submitted', False)
    #
    # if not evaluation_submitted:
    #     with st.form("evaluation_form"):
    #         rank = st.selectbox(
    #             "Does your intended diagnosis/condition come in which rank?",
    #             options=[1, 2, 3, 4, 5, "None of these (please specify in the comment)"],
    #             index=0,
    #         )
    #         review = st.text_area(
    #             "Your review on the overall examination "
    #             "and what should improve",
    #             placeholder="Please share your detailed feedback...",
    #             height=150,
    #         )
    #         submitted = st.form_submit_button(
    #             "Submit Evaluation", type="primary",
    #             use_container_width=True,
    #         )
    #
    #     if submitted:
    #         if not review or not review.strip():
    #             st.error("Please provide your review comment — it's required.")
    #         else:
    #             from db.models import log_evaluation
    #             session_id = st.session_state.get('db_session_id')
    #             rank_val = 0 if isinstance(rank, str) else rank
    #             log_evaluation(session_id, rank_val, review.strip())
    #             st.session_state.evaluation_submitted = True
    #             st.rerun()
    # else:
    #     st.success("Thank you for your evaluation!")
