import streamlit as st

_client = None


def get_supabase():
    global _client
    if _client is not None:
        return _client
    try:
        from supabase import create_client
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
        _client = create_client(url, key)
        return _client
    except Exception:
        return None
