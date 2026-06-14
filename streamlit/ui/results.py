import os
import tempfile
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import networkx as nx
from pyvis.network import Network

from engine.data_loader import load_all_data
from engine.ranking import rank_conditions
from engine.config import LIKELIHOOD_SCORES
from ui.components import (
    render_condition_card, triage_badge_html, triage_color,
    TRIAGE_COLORS, TRIAGE_LABELS, TRIAGE_BG_LIGHT,
    render_metric_card, render_section_header,
)


def render():
    data = load_all_data()
    state = st.session_state.state
    engine = st.session_state.engine

    result_df, detail_df = rank_conditions(
        state.confirmed_uuids, state.denied_uuids, state.candidate_pool,
        state.condition_points, state.age, state.gender, data,
        engine.ranking_config,
    )

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
        f"Top 5 of {len(result_df)} conditions scored and ranked"
    )

    if len(result_df) > 0:
        max_score = result_df.iloc[0]['final_score']
        for i, row in result_df.head(5).iterrows():
            render_condition_card(row, i + 1, max_score=max_score)

        if len(result_df) > 5:
            with st.expander(
                f"All Ranked Conditions ({len(result_df)} total)"
            ):
                for i, row in result_df.iterrows():
                    render_condition_card(row, i + 1, max_score=max_score)
    else:
        st.warning("No conditions survived the elimination process.")

    render_section_header(
        "Symptom-Condition Network",
        "Blue diamonds = confirmed symptoms. "
        "Circles = conditions colored by triage level."
    )
    if len(result_df) > 0:
        _render_graph(result_df, state, data)

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
            log_df = pd.DataFrame(state.question_log)
            st.dataframe(log_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No questions were asked.")

    # --- Evaluation Section ---
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    render_section_header(
        "Evaluation",
        "Please evaluate this assessment before starting a new one"
    )

    evaluation_submitted = st.session_state.get('evaluation_submitted', False)

    if not evaluation_submitted:
        with st.form("evaluation_form"):
            rank = st.selectbox(
                "Does your intended diagnosis/condition come in which rank?",
                options=[1, 2, 3, 4, 5],
                index=0,
            )
            review = st.text_area(
                "Your review on the overall examination "
                "and what should improve",
                placeholder="Please share your detailed feedback...",
                height=150,
            )
            submitted = st.form_submit_button(
                "Submit Evaluation", type="primary",
                use_container_width=True,
            )

        if submitted:
            if not review or not review.strip():
                st.error("Please provide your review comment — it's required.")
            else:
                from db.models import log_evaluation
                session_id = st.session_state.get('db_session_id')
                log_evaluation(session_id, rank, review.strip())
                st.session_state.evaluation_submitted = True
                st.rerun()
    else:
        st.success("Thank you for your evaluation!")

        st.markdown(
            "<div style='height:20px'></div>", unsafe_allow_html=True,
        )

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


def _render_graph(result_df, state, data, max_nodes=30):
    net = Network(
        height="500px", width="100%",
        bgcolor="#f8fafc", font_color="#1e293b",
        directed=False,
    )
    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -4000,
                "springLength": 160,
                "springConstant": 0.04,
                "damping": 0.09
            },
            "stabilization": {"iterations": 150}
        },
        "nodes": {
            "font": {"size": 12, "face": "Inter, sans-serif", "color": "#1e293b"},
            "borderWidth": 2,
            "borderWidthSelected": 3
        },
        "edges": {
            "color": {"color": "#94a3b8", "highlight": "#2563eb"},
            "width": 1.5,
            "smooth": {"type": "continuous"}
        },
        "interaction": {
            "hover": true,
            "zoomView": true,
            "dragView": true,
            "tooltipDelay": 100
        }
    }
    """)

    node_count = 0
    top_n = min(10, len(result_df))
    top_conditions = result_df.head(top_n)

    for _, row in top_conditions.iterrows():
        if node_count >= max_nodes:
            break
        cid = row['condition_snomed_id']
        color = TRIAGE_COLORS.get(row['triage_level'], '#6b7280')
        triage_label = TRIAGE_LABELS.get(
            row['triage_level'], row['triage_level']
        )
        net.add_node(
            f"cond_{cid}",
            label=row['condition_name'][:28],
            title=(
                f"<b>{row['condition_name']}</b><br>"
                f"Score: {row['final_score']:.1f}<br>"
                f"Triage: {triage_label}<br>"
                f"Matches: {row['num_symptom_matches']}"
            ),
            color={
                'background': color, 'border': color,
                'highlight': {'background': color, 'border': '#0f172a'},
            },
            size=22 + row['final_score'] * 2,
            shape='dot',
            font={'color': '#1e293b', 'size': 12},
        )
        node_count += 1

    confirmed_symptoms = data.nodes_symptom[
        data.nodes_symptom['uuid'].isin(state.confirmed_uuids)
    ][['uuid', 'root_snomed_name', 'name']].drop_duplicates('uuid')

    for _, sym in confirmed_symptoms.iterrows():
        if node_count >= max_nodes:
            break
        sym_id = f"sym_{sym['uuid']}"
        display_name = (
            sym['name'] if len(sym['name']) <= 22
            else sym['root_snomed_name']
        )
        net.add_node(
            sym_id,
            label=display_name[:22],
            title=(
                f"<b>Symptom</b><br>"
                f"{sym['name']}<br>"
                f"Root: {sym['root_snomed_name']}"
            ),
            color={
                'background': '#3b82f6', 'border': '#1d4ed8',
                'highlight': {
                    'background': '#60a5fa', 'border': '#1d4ed8',
                },
            },
            size=16,
            shape='diamond',
            font={'color': '#1e293b', 'size': 11},
        )
        node_count += 1

    top_cids = set(top_conditions['condition_snomed_id'].values)
    for _, sym in confirmed_symptoms.iterrows():
        sym_id = f"sym_{sym['uuid']}"
        edges = data.edges_present_in[
            (data.edges_present_in['symptom_uuid'] == sym['uuid']) &
            (data.edges_present_in['condition_snomed_id'].isin(top_cids))
        ]
        for _, e in edges.iterrows():
            cond_id = f"cond_{e['condition_snomed_id']}"
            pcs = e['likelihood_condition_given_symptom']
            score = LIKELIHOOD_SCORES.get(pcs, 0.2)
            net.add_edge(
                sym_id, cond_id,
                title=f"P(C|S): {pcs}",
                width=score * 3,
                color={'color': '#cbd5e1', 'highlight': '#2563eb'},
            )

    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix='.html', mode='w', encoding='utf-8',
    )
    net.save_graph(tmp.name)
    tmp.close()

    with open(tmp.name, 'r', encoding='utf-8') as f:
        html_content = f.read()

    components.html(html_content, height=520, scrolling=False)

    try:
        os.unlink(tmp.name)
    except OSError:
        pass
