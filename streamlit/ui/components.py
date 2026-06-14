import streamlit as st

TRIAGE_COLORS = {
    'emergency': '#dc2626',
    'worrisome': '#d97706',
    'opd_managed': '#16a34a',
}

TRIAGE_BG_LIGHT = {
    'emergency': '#fef2f2',
    'worrisome': '#fffbeb',
    'opd_managed': '#f0fdf4',
}

TRIAGE_LABELS = {
    'emergency': 'EMERGENCY',
    'worrisome': 'WORRISOME',
    'opd_managed': 'OPD MANAGED',
}


def triage_badge_html(triage_level):
    color = TRIAGE_COLORS.get(triage_level, '#6b7280')
    bg = TRIAGE_BG_LIGHT.get(triage_level, '#f3f4f6')
    label = TRIAGE_LABELS.get(triage_level, triage_level.upper())
    return (
        f'<span style="'
        f'background-color:{bg};'
        f'color:{color};'
        f'padding:3px 10px;'
        f'border-radius:4px;'
        f'font-size:0.72em;'
        f'font-weight:700;'
        f'letter-spacing:0.4px;'
        f'border:1px solid {color}33;'
        f'display:inline-block;'
        f'">{label}</span>'
    )


def triage_color(triage_level):
    return TRIAGE_COLORS.get(triage_level, '#6b7280')


def render_condition_card(row, rank, max_score=None):
    triage = row['triage_level']
    accent = TRIAGE_COLORS.get(triage, '#6b7280')
    score = row['final_score']

    if max_score and max_score > 0:
        bar_pct = min((score / max_score) * 100, 100)
    else:
        bar_pct = 50

    pc_weight = row.get('pc_weight', '')
    pc_badge = ''
    if pc_weight != '':
        pc_badge = (
            f'<span style="background:#fef3c7;color:#92400e;padding:3px 9px;'
            f'border-radius:5px;font-size:0.75em;font-weight:600;">'
            f'P(C) {pc_weight:.2f}</span>'
        )

    st.markdown(
        f"""
        <div style="
            border: 1px solid #e2e8f0;
            border-left: 5px solid {accent};
            border-radius: 10px;
            margin-bottom: 12px;
            background: #ffffff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            overflow: hidden;
        ">
            <div style="padding:16px 20px 10px 20px;">
                <div style="display:flex;justify-content:space-between;
                            align-items:flex-start;">
                    <div style="flex:1;">
                        <div style="display:flex;align-items:center;gap:10px;">
                            <span style="background:{accent};color:#ffffff;
                                         width:26px;height:26px;border-radius:50%;
                                         display:inline-flex;align-items:center;
                                         justify-content:center;font-weight:700;
                                         font-size:0.75em;flex-shrink:0;">
                                {rank}
                            </span>
                            <span style="font-weight:700;font-size:1.05em;
                                         color:#0f172a;">
                                {row['condition_name']}
                            </span>
                        </div>
                        <div style="margin-top:6px;margin-left:36px;">
                            {triage_badge_html(triage)}
                            <span style="font-size:0.78em;color:#64748b;
                                         margin-left:8px;">
                                {row.get('type_condition', '')}
                            </span>
                        </div>
                    </div>
                    <div style="text-align:right;flex-shrink:0;margin-left:12px;">
                        <div style="font-size:1.6em;font-weight:800;
                                    color:{accent};line-height:1;">
                            {score:.1f}
                        </div>
                        <div style="font-size:0.65em;color:#94a3b8;
                                    text-transform:uppercase;letter-spacing:0.5px;
                                    margin-top:2px;">
                            score
                        </div>
                    </div>
                </div>
            </div>
            <div style="padding:0 20px 6px 20px;">
                <div style="background:#f1f5f9;border-radius:3px;height:5px;
                            overflow:hidden;">
                    <div style="background:{accent};height:100%;
                                width:{bar_pct}%;border-radius:3px;"></div>
                </div>
            </div>
            <div style="padding:10px 20px 12px 20px;background:#f8fafc;
                        border-top:1px solid #f1f5f9;display:flex;gap:8px;
                        flex-wrap:wrap;">
                <span style="background:#e0e7ff;color:#3730a3;padding:3px 9px;
                             border-radius:5px;font-size:0.75em;font-weight:600;">
                    Y/N {row['yn_points']:+.1f}
                </span>
                <span style="background:#dbeafe;color:#1e40af;padding:3px 9px;
                             border-radius:5px;font-size:0.75em;font-weight:600;">
                    P(C|S) {row['pcs_score']:.1f}
                </span>
                {pc_badge}
                <span style="background:#e0f2fe;color:#0369a1;padding:3px 9px;
                             border-radius:5px;font-size:0.75em;font-weight:600;">
                    Age {row['age_weight']:.1f}
                </span>
                <span style="background:#f0f9ff;color:#0c4a6e;padding:3px 9px;
                             border-radius:5px;font-size:0.75em;font-weight:600;">
                    Gender {row['gender_weight']:.1f}
                </span>
                <span style="background:#f5f3ff;color:#5b21b6;padding:3px 9px;
                             border-radius:5px;font-size:0.75em;font-weight:600;">
                    Matches {row['num_symptom_matches']}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label, value, color="#2563eb"):
    st.markdown(
        f"""
        <div style="
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 18px 14px;
            text-align: center;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            border-top: 3px solid {color};
        ">
            <div style="font-size: 0.72em; color: #64748b;
                        text-transform: uppercase; letter-spacing: 0.6px;
                        font-weight: 600; margin-bottom: 6px;">
                {label}
            </div>
            <div style="font-size: 1.7em; font-weight: 800; color: {color};">
                {value}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title, subtitle=None):
    sub_html = ""
    if subtitle:
        sub_html = (
            f'<div style="font-size:0.85em;color:#64748b;margin-top:3px;">'
            f'{subtitle}</div>'
        )
    st.markdown(
        f"""
        <div style="margin: 28px 0 14px 0; padding-bottom: 8px;
                    border-bottom: 2px solid #e2e8f0;">
            <div style="font-size: 1.2em; font-weight: 700; color: #0f172a;">
                {title}
            </div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
