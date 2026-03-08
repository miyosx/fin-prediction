"""Streamlit session state helpers."""
import streamlit as st
import pandas as pd


def init_session_state():
    """Initialize all session state keys with defaults."""
    defaults = {
        "feature_matrix": None,
        "indices": {},
        "breadth": {},
        "mm_data": {},
        "last_refresh": None,
        "loading": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def set_loading(loading: bool):
    st.session_state["loading"] = loading


def get_feature_matrix() -> pd.DataFrame | None:
    return st.session_state.get("feature_matrix")


def set_feature_matrix(df: pd.DataFrame):
    st.session_state["feature_matrix"] = df


def get_indices() -> dict:
    return st.session_state.get("indices", {})


def set_indices(data: dict):
    st.session_state["indices"] = data


def get_breadth() -> dict:
    return st.session_state.get("breadth", {})


def set_breadth(data: dict):
    st.session_state["breadth"] = data


def get_mm_data() -> dict:
    return st.session_state.get("mm_data", {})


def set_mm_data(data: dict):
    st.session_state["mm_data"] = data
