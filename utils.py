"""
utils.py
Funções auxiliares do Delta-Negociação — GATE/PMESP.
Extraído do app.py — Fase 2 da reestruturação.
"""

import pandas as pd
import streamlit as st


# ============================================================
# TRATAMENTO DE VALORES (AIRTABLE)
# ============================================================

def limpar_valor(val):
    """Normaliza valores vindos do Airtable (listas, NaN, etc)."""
    if isinstance(val, list):
        return val[0] if len(val) > 0 else "N/D"
    return str(val) if pd.notna(val) else "N/D"


def limpar_id(v):
    """Remove sufixo .0 e normaliza IDs."""
    if isinstance(v, list) and len(v) > 0:
        v = v[0]
    v_str = str(v).strip()
    if v_str.endswith('.0'):
        v_str = v_str[:-2]
    return v_str


def formatar_tempo_airtable(val):
    """Converte segundos (int/float) para string HH:MM."""
    try:
        if isinstance(val, list):
            val = val[0]
        if pd.isna(val) or val == "N/D" or val == "":
            return "N/D"
        s = int(float(val))
        h = s // 3600
        m = (s % 3600) // 60
        return f"{h:02d}h {m:02d}m"
    except:
        return str(val)


def somar_tempos_segundos(serie):
    """Soma uma série de valores em segundos e retorna HH:MM."""
    total_s = 0
    for val in serie:
        try:
            if isinstance(val, list):
                val = val[0]
            if pd.notna(val) and val != "N/D" and val != "":
                total_s += int(float(val))
        except:
            pass
    h = total_s // 3600
    m = (total_s % 3600) // 60
    return f"{h:02d}h {m:02d}m"


# ============================================================
# ESCALA LIKERT — MAPA EMOCIONAL
# ============================================================

escala_likert = {
    "❓ inaudível / não observado": 0,
    "inaudível": 0,
    "não observado": 0,
    "n/d": 0,
    "nao observado": 0,

    # Nível 1
    "não agressivo": 1, "nao agressivo": 1,
    "não agresssivo": 1, "nao agresssivo": 1,
    "não receptivo": 1, "nao receptivo": 1,

    # Nível 2
    "neutro": 2,

    # Nível 3
    "parcialmente agressivo": 3,
    "parcialmente receptivo": 3,

    # Nível 4
    "agressivo": 4,
    "receptivo": 4,

    # Nível 5
    "muito agressivo": 5,
    "muito receptivo": 5,

    "🔴 reação negativa": 1,
    "⚪ reação neutra": 2,
    "🟢 reação positiva": 5,
}


def converter_escala(val):
    """Converte texto da escala Likert para valor numérico."""
    if not val:
        return 0
    v = str(val).lower().strip()
    return escala_likert.get(v, 0)


# ============================================================
# COMPONENTES DE UI
# ============================================================

def render_toggle_button(
    label: str,
    session_key: str,
    button_key: str,
    width_ratio: float = 0.6
) -> bool:
    """
    Renderiza um botão toggle padronizado com glassmorphism.
    Retorna True se o painel estiver aberto, False se fechado.
    """
    if session_key not in st.session_state:
        st.session_state[session_key] = False

    col_btn, col_spacer = st.columns([width_ratio, 1 - width_ratio])
    with col_btn:
        if st.button(label, key=button_key, use_container_width=True):
            st.session_state[session_key] = not st.session_state[session_key]

    return st.session_state[session_key]
