import os
import pandas as pd
import streamlit as st
from dataclasses import dataclass
from engine.config import LIKELIHOOD_SCORES


@dataclass
class DataBundle:
    nodes_symptom: pd.DataFrame
    nodes_condition: pd.DataFrame
    edges_present_in: pd.DataFrame
    edges_has_prerequisite: pd.DataFrame
    uuids_with_edges: set
    total_condition_weight: float
    symptom_names: list


@st.cache_data
def load_all_data():
    csv_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'csv')
    csv_dir = os.path.abspath(csv_dir)

    nodes_symptom = pd.read_csv(os.path.join(csv_dir, 'nodes_symptom.csv'))
    edges_present_in = pd.read_csv(os.path.join(csv_dir, 'edges_present_in.csv'))
    nodes_condition = pd.read_csv(os.path.join(csv_dir, 'nodes_condition.csv'))
    edges_has_prerequisite = pd.read_csv(os.path.join(csv_dir, 'edges_has_prerequisite.csv'))

    edges_present_in['likelihood_condition_given_symptom'] = (
        edges_present_in['likelihood_condition_given_symptom'].str.lower()
    )
    edges_present_in['likelihood_symptom_given_condition'] = (
        edges_present_in['likelihood_symptom_given_condition'].str.lower()
    )
    nodes_condition['overall_likelihood'] = nodes_condition['overall_likelihood'].str.lower()
    edges_has_prerequisite['relation_strength'] = edges_has_prerequisite['relation_strength'].str.lower()
    edges_has_prerequisite['relation_polarity'] = edges_has_prerequisite['relation_polarity'].str.lower()

    uuids_with_edges = set(edges_present_in['symptom_uuid'].unique())
    total_condition_weight = nodes_condition['overall_likelihood'].map(LIKELIHOOD_SCORES).sum()

    symptom_names = sorted(
        nodes_symptom[nodes_symptom['name'] == nodes_symptom['root_snomed_name']]
        ['root_snomed_name'].unique().tolist()
    )

    return DataBundle(
        nodes_symptom=nodes_symptom,
        nodes_condition=nodes_condition,
        edges_present_in=edges_present_in,
        edges_has_prerequisite=edges_has_prerequisite,
        uuids_with_edges=uuids_with_edges,
        total_condition_weight=total_condition_weight,
        symptom_names=symptom_names,
    )
