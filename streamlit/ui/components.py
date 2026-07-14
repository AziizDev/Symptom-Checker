import os
import tempfile

import streamlit as st
import streamlit.components.v1 as st_components
from pyvis.network import Network

from engine.config import LIKELIHOOD_SCORES

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

    speciality = row.get('speciality', '')
    spec_badge = ''
    if speciality:
        spec_badge = (
            f'<span style="border:1px solid #cbd5e1;color:#475569;'
            f'background:#ffffff;padding:5px 10px;border-radius:6px;'
            f'font-size:0.72em;font-weight:600;white-space:nowrap;'
            f'line-height:1;">{speciality}</span>'
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
                    <div style="display:flex;align-items:center;gap:12px;
                                flex-shrink:0;margin-left:12px;">
                        {spec_badge}
                        <div style="text-align:right;">
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


def render_condition_network(conditions, confirmed_uuids, data,
                             height=500, max_nodes=30):
    """Draw the symptom-condition network for the given ranked conditions.

    `conditions` is a list of dicts with at least: condition_snomed_id,
    condition_name, triage_level, final_score, and num_symptom_matches
    (or num_matches). Confirmed symptoms are drawn as blue diamonds.
    """
    net = Network(
        height=f"{height}px", width="100%",
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
    top_cids = set()

    for row in conditions:
        if node_count >= max_nodes:
            break
        cid = row['condition_snomed_id']
        top_cids.add(cid)
        color = TRIAGE_COLORS.get(row['triage_level'], '#6b7280')
        triage_label = TRIAGE_LABELS.get(
            row['triage_level'], row['triage_level']
        )
        matches = row.get('num_symptom_matches', row.get('num_matches', 0))
        net.add_node(
            f"cond_{cid}",
            label=row['condition_name'][:28],
            title=(
                f"{row['condition_name']}\n"
                f"Score: {row['final_score']:.1f}\n"
                f"Triage: {triage_label}\n"
                f"Matches: {matches}"
            ),
            color={
                'background': color, 'border': color,
                'highlight': {'background': color, 'border': '#0f172a'},
            },
            size=max(12, 22 + row['final_score'] * 2),
            shape='dot',
            font={'color': '#1e293b', 'size': 12},
        )
        node_count += 1

    confirmed_symptoms = data.nodes_symptom[
        data.nodes_symptom['uuid'].isin(confirmed_uuids)
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
                f"Symptom\n"
                f"{sym['name']}\n"
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

    added_syms = {n for n in net.get_nodes() if str(n).startswith('sym_')}
    for _, sym in confirmed_symptoms.iterrows():
        sym_id = f"sym_{sym['uuid']}"
        if sym_id not in added_syms:
            continue
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

    st_components.html(html_content, height=height + 20, scrolling=False)

    try:
        os.unlink(tmp.name)
    except OSError:
        pass


def group_by_speciality(rows):
    """Group ranked conditions by speciality.

    `rows` must already be in rank order. Specialities are ordered by their
    best-ranked condition, so the speciality of the #1 condition comes first.
    Returns [(speciality, [(rank, row), ...]), ...].
    """
    groups = {}
    for i, row in enumerate(rows):
        spec = row.get('speciality') or '-'
        groups.setdefault(spec, []).append((i + 1, row))
    return sorted(groups.items(), key=lambda kv: kv[1][0][0])


def render_speciality_breakdown(rows):
    """Speciality list for the top-N conditions; click one to see its conditions."""
    for spec, items in group_by_speciality(rows):
        n = len(items)
        with st.expander(f"{spec}  ({n} condition{'s' if n > 1 else ''})"):
            for rank, row in items:
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:10px;
                                padding:7px 2px;">
                        <span style="background:#f1f5f9;color:#475569;
                                     width:22px;height:22px;border-radius:50%;
                                     display:inline-flex;align-items:center;
                                     justify-content:center;font-weight:700;
                                     font-size:0.72em;flex-shrink:0;">
                            {rank}
                        </span>
                        <span style="font-weight:600;color:#0f172a;
                                     font-size:0.92em;">
                            {row['condition_name']}
                        </span>
                        {triage_badge_html(row['triage_level'])}
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
