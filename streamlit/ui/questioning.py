import streamlit as st
import pandas as pd
from ui.components import triage_badge_html, TRIAGE_COLORS


def render():
    state = st.session_state.state
    engine = st.session_state.engine

    if state.finished:
        st.session_state.page = 'results'
        st.rerun()
        return

    q = state.current_question
    if q is None:
        st.session_state.page = 'results'
        st.rerun()
        return

    total = state.total_expected
    progress = min(state.questions_asked / total, 1.0)
    st.progress(progress, text=f"Question {state.questions_asked + 1} of {total}")

    phase_labels = {
        'phase1_variant': 'Symptom Details',
        'phase2_prereq': 'Medical History',
        'phase3_main': 'Assessment',
        'phase4_adaptive': 'Refining',
    }

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
            <span style="font-size:0.82em; color:#64748b; font-weight:500;">
                Phase: {phase_labels.get(state.phase, state.phase)}
            </span>
            <span style="font-size:0.82em; color:#64748b; font-weight:500;">
                Pool: {len(state.candidate_pool)} conditions
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    if q['type'] == 'variant':
        _render_variant(q, state)
    elif q['type'] == 'discovered':
        _render_discovered(q, state)
    elif q['type'] == 'prerequisite':
        _render_prerequisite(q, state)
    elif q['type'] == 'screening':
        _render_screening(q, state)

    st.divider()
    _render_live_dashboard(engine, state)


def _render_variant(q, state):
    st.subheader(q['question'])
    st.markdown(
        f'<p style="font-size:1.05em; color:#334155; font-weight:500; '
        f'margin-top:-8px; margin-bottom:16px;">'
        f'Regarding: {q["root_name"]}</p>',
        unsafe_allow_html=True,
    )

    options = q['options']
    qkey = f"q_{state.questions_asked}"
    comment_key = f"comment_{qkey}"

    if q['selection_type'] == 's':
        labels = [o['label'] for o in options]
        choice = st.radio(
            "Select one:",
            options=range(len(labels) + 1),
            format_func=lambda i: (
                labels[i] if i < len(labels) else "None of these apply"
            ),
            key=qkey,
            index=len(labels),
        )

        comment = st.text_input(
            "Comment (optional)",
            placeholder="Any notes about this question?",
            key=comment_key,
        )

        if st.button(
            "Confirm", type="primary", use_container_width=True,
            key=f"btn_{qkey}",
        ):
            if choice >= len(labels):
                _submit([], comment)
            else:
                _submit([choice], comment)
    else:
        st.markdown("*Select all that apply:*")
        selected = []
        for i, o in enumerate(options):
            if st.checkbox(o['label'], key=f"opt_{qkey}_{i}"):
                selected.append(i)

        comment = st.text_input(
            "Comment (optional)",
            placeholder="Any notes about this question?",
            key=comment_key,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Confirm Selection", type="primary",
                use_container_width=True, key=f"btn_yes_{qkey}",
            ):
                _submit(selected, comment)
        with col2:
            if st.button(
                "None of these", use_container_width=True,
                key=f"btn_no_{qkey}",
            ):
                _submit([], comment)


def _render_discovered(q, state):
    st.subheader(q['question'])

    qkey = f"q_{state.questions_asked}"
    comment_key = f"comment_{qkey}"

    comment = st.text_input(
        "Comment (optional)",
        placeholder="Any notes about this question?",
        key=comment_key,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Yes", type="primary", use_container_width=True,
            key=f"btn_yes_{qkey}",
        ):
            _submit(True, comment)
    with col2:
        if st.button(
            "No", use_container_width=True, key=f"btn_no_{qkey}",
        ):
            _submit(False, comment)


def _render_prerequisite(q, state):
    st.subheader(q['question'])
    st.caption("Medical History")

    qkey = f"q_{state.questions_asked}"
    comment_key = f"comment_{qkey}"

    comment = st.text_input(
        "Comment (optional)",
        placeholder="Any notes about this question?",
        key=comment_key,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Yes", type="primary", use_container_width=True,
            key=f"btn_yes_{qkey}",
        ):
            _submit(True, comment)
    with col2:
        if st.button(
            "No", use_container_width=True, key=f"btn_no_{qkey}",
        ):
            _submit(False, comment)


def _render_screening(q, state):
    st.markdown(
        f'<div style="background:#fef3c7;border-left:4px solid #f59e0b;'
        f'padding:10px 14px;border-radius:6px;margin-bottom:12px;'
        f'font-size:0.88em;color:#92400e;font-weight:500;">'
        f'Red Flag Screening — {q["condition_name"]}</div>',
        unsafe_allow_html=True,
    )
    st.subheader(q['question'])

    qkey = f"q_{state.questions_asked}"
    comment_key = f"comment_{qkey}"

    comment = st.text_input(
        "Comment (optional)",
        placeholder="Any notes about this question?",
        key=comment_key,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Yes", type="primary", use_container_width=True,
            key=f"btn_yes_{qkey}",
        ):
            _submit(True, comment)
    with col2:
        if st.button(
            "No", use_container_width=True,
            key=f"btn_no_{qkey}",
        ):
            _submit(False, comment)


def _submit(answer, comment=''):
    state = st.session_state.state
    engine = st.session_state.engine

    q = state.current_question
    pool_before = len(state.candidate_pool)

    new_state = engine.process_answer(state, answer)

    from db.models import log_question
    session_id = st.session_state.get('db_session_id')
    if q and session_id:
        pool_after = len(new_state.candidate_pool)
        eliminated = pool_before - pool_after
        log_question(
            session_id=session_id,
            order=new_state.questions_asked,
            q_type=q['type'],
            question_text=q.get('question', ''),
            answer=str(answer),
            comment=comment,
            pool_after=pool_after,
            eliminated=eliminated,
        )

    st.session_state.state = new_state
    st.rerun()


def _render_live_dashboard(engine, state):
    top5 = engine.get_live_top_n(state, n=5)

    if not top5:
        st.markdown(
            '<div style="color:#64748b;font-size:0.9em;padding:12px;'
            'text-align:center;">No conditions scored yet.</div>',
            unsafe_allow_html=True,
        )
        return

    rows_html = ""
    for i, row in enumerate(top5):
        bg = "#ffffff" if i % 2 == 0 else "#f8fafc"
        accent = TRIAGE_COLORS.get(row['triage_level'], '#6b7280')
        rows_html += f"""
        <tr style="background:{bg};">
            <td style="padding:8px 10px;color:#0f172a;font-weight:500;
                       font-size:0.88em;">
                {row['condition_name'][:30]}
            </td>
            <td style="padding:8px 6px;">
                {triage_badge_html(row['triage_level'])}
            </td>
            <td style="padding:8px 6px;text-align:center;color:#334155;
                       font-size:0.85em;">
                {row['yn_points']:+.1f}
            </td>
            <td style="padding:8px 6px;text-align:center;color:#334155;
                       font-size:0.85em;">
                {row['pcs_score']:.1f}
            </td>
            <td style="padding:8px 6px;text-align:center;color:#334155;
                       font-size:0.85em;">
                {row['pc_weight']:.2f}
            </td>
            <td style="padding:8px 6px;text-align:center;font-weight:700;
                       color:{accent};font-size:0.92em;">
                {row['final_score']:.1f}
            </td>
            <td style="padding:8px 6px;text-align:center;color:#64748b;
                       font-size:0.85em;">
                {row['num_matches']}
            </td>
        </tr>
        """

    th_style = (
        "padding:8px 6px;text-align:center;font-size:0.72em;"
        "color:#64748b;font-weight:600;text-transform:uppercase;"
        "letter-spacing:0.4px;"
    )

    st.markdown(
        f"""
        <div style="margin-top:4px;">
            <div style="font-size:0.85em;font-weight:700;color:#334155;
                        margin-bottom:8px;text-transform:uppercase;
                        letter-spacing:0.4px;">
                Live Top 5
            </div>
            <div style="border:1px solid #e2e8f0;border-radius:8px;
                        overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <table style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr style="background:#f1f5f9;">
                            <th style="{th_style}text-align:left;
                                       padding-left:10px;">Condition</th>
                            <th style="{th_style}text-align:left;">Triage</th>
                            <th style="{th_style}">Y/N</th>
                            <th style="{th_style}">P(C|S)</th>
                            <th style="{th_style}">P(C)</th>
                            <th style="{th_style}">Score</th>
                            <th style="{th_style}">#</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
