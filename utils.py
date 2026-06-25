"""
utils.py
Funções auxiliares do Delta-Negociação — GATE/PMESP.
Extraído do app.py — Fase 2 da reestruturação.
"""

import re
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


def tempo_para_exibicao_hhmm(val):
    """Converte segundos do Airtable (ou texto) para HH:MM nos formulários."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    if isinstance(val, list) and len(val) > 0:
        val = val[0]
    s = str(val).strip()
    if s in ("", "N/D"):
        return ""
    if re.match(r"^\d+:\d{1,2}$", s):
        partes = s.split(":")
        return f"{int(partes[0]):02d}:{int(partes[1]):02d}"
    m = re.match(r"^(\d+)\s*h\s*(\d+)\s*m", s, re.I)
    if m:
        return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    try:
        total = int(float(s))
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    except (ValueError, TypeError):
        return s


def tempo_para_airtable_segundos(val):
    """Converte h:mm (ou segundos numéricos) para inteiro em segundos — formato do Airtable."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        seg = int(val)
        return seg if seg > 0 else None
    if isinstance(val, list) and len(val) > 0:
        val = val[0]
    s = str(val).strip()
    if s in ("", "N/D", "None", "nan", "00:00", "0:00"):
        return None
    s = s.replace("：", ":")
    m = re.match(r"^(\d+)\s*h\s*(\d+)\s*m", s, re.I)
    if m:
        seg = int(m.group(1)) * 3600 + int(m.group(2)) * 60
        return seg if seg > 0 else None
    if ":" in s:
        partes = [p.strip() for p in s.split(":")]
        try:
            h = int(partes[0])
            mins = int(partes[1]) if len(partes) > 1 else 0
            seg = (h * 3600) + (mins * 60)
            return seg if seg > 0 else None
        except (ValueError, TypeError):
            return None
    try:
        seg = int(float(s.replace(",", ".")))
        return seg if seg > 0 else None
    except (ValueError, TypeError):
        return None


def validar_tempos_payload_airtable(payload):
    """
    Converte campos de duração para segundos (int) antes do Airtable.
    Levanta ValueError se o usuário informou texto inválido (ex.: '01:30' sem converter).
    """
    erros = []
    for campo in ("Tempo de Negociação Real", "Tempo de Negociação Tática"):
        if campo not in payload:
            continue
        bruto = payload[campo]
        if bruto is None or (isinstance(bruto, float) and pd.isna(bruto)):
            payload.pop(campo, None)
            continue
        if isinstance(bruto, str) and bruto.strip() in ("", "N/D"):
            payload.pop(campo, None)
            continue

        segundos = tempo_para_airtable_segundos(bruto)
        if segundos is None:
            erros.append(
                f'"{campo}": valor inválido ({bruto!r}). Use h:mm — ex.: 1:30 (1h30min).'
            )
            payload.pop(campo, None)
        else:
            payload[campo] = int(segundos)
            if not isinstance(payload[campo], int):
                erros.append(
                    f'"{campo}": conversão interna falhou ({bruto!r} → {payload[campo]!r}).'
                )
                payload.pop(campo, None)

    if erros:
        raise ValueError(" ".join(erros))
    return payload


def descrever_tempos_payload(payload):
    """Resumo legível dos campos de duração (para diagnóstico de erro)."""
    partes = []
    for campo in ("Tempo de Negociação Real", "Tempo de Negociação Tática"):
        if campo not in payload:
            continue
        valor = payload[campo]
        partes.append(f"{campo}={valor!r} (tipo {type(valor).__name__})")
    return "; ".join(partes) if partes else "(sem campos de tempo)"


def aplicar_tempos_payload_airtable(payload):
    """Alias retrocompatível — valida e converte tempos no payload."""
    return validar_tempos_payload_airtable(payload)


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

def render_card(label, valor, cor_classe):
    """Renderiza um card HTML com label, valor e classe de cor."""
    return (
        f"<div class='info-card {cor_classe}' style='padding: 12px; margin-top: 5px; margin-bottom: 5px;'>"
        f"<strong style='color: #bbb;'>{label}:</strong>"
        f"<br><span style='font-size: 1.1rem; font-weight: bold;'>{valor}</span>"
        f"</div>"
    )
