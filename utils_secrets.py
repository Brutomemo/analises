import os
import streamlit as st

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        return os.getenv(key)