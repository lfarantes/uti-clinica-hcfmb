import pandas as pd
import logging
import numpy as np

# Configurar o logging
logging.basicConfig(level=logging.INFO)

def aplicar_filtro_coorte_desfecho(df, selected_month, selected_year, coluna_desfecho_obrigatorio):
    """
    Filtra os pacientes com base na data de admissão na UTI, mas exige 
    que a coluna_desfecho_obrigatorio não esteja vazia (ciclo encerrado).
    """
    df_limpo = df.copy()
    col_adm = 'data_e_hora_admissao_uti'
    
    if col_adm not in df_limpo.columns or coluna_desfecho_obrigatorio not in df_limpo.columns:
        return pd.DataFrame()
        
    # Conversão segura para data
    df_limpo[col_adm] = pd.to_datetime(df_limpo[col_adm], errors='coerce')
    
    # Remove registros onde a admissão ou o desfecho especificado são nulos/em branco
    df_limpo = df_limpo.dropna(subset=[col_adm, coluna_desfecho_obrigatorio])
    df_limpo = df_limpo[~df_limpo[coluna_desfecho_obrigatorio].astype(str).str.strip().str.lower().isin(['nan', 'none', 'nat', ''])]
    
    # Filtra os pacientes admitidos na competência do mês/ano selecionados
    df_mes = df_limpo[
        (df_limpo[col_adm].dt.month == selected_month) &
        (df_limpo[col_adm].dt.year == selected_year)
    ]
    return df_mes

# --- FUNÇÃO 1: TAXA DE MORTALIDADE ---
def calculate_taxa_mortalidade_uti(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]
        
    coluna_desfecho = 'desfecho_uti'
    df_mes_corrente = aplicar_filtro_coorte_desfecho(df, selected_month, selected_year, 'data_do_desfecho_uti')
    
    if df_mes_corrente.empty or coluna_desfecho not in df_mes_corrente.columns:
        return 0.0, 0, 0

    df_mes_corrente[coluna_desfecho] = df_mes_corrente[coluna_desfecho].astype(str)
    denominador = len(df_mes_corrente)
    
    is_obito_raw_1 = df_mes_corrente[coluna_desfecho].eq('2')
    is_obito_raw_2 = df_mes_corrente[coluna_desfecho].eq('2.0')
    numerador = (is_obito_raw_1 | is_obito_raw_2).sum()

    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0
    return taxa, numerador, denominador

# --- FUNÇÃO 2: TAXA DE DESNUTRIÇÃO ---
def calculate_taxa_desnutricao(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]
        
    coluna_data_admissao = 'data_e_hora_admissao_uti'
    coluna_desnutricao = 'diagnostico_desnutricao'

    if coluna_data_admissao not in df.columns or coluna_desnutricao not in df.columns:
        return 0.0, 0, 0 

    df[coluna_data_admissao] = pd.to_datetime(df[coluna_data_admissao], errors='coerce')
    df_com_admissao = df.dropna(subset=[coluna_data_admissao])
    
    df_admitidos_no_mes = df_com_admissao[
        (df_com_admissao[coluna_data_admissao].dt.month == selected_month) &
        (df_com_admissao[coluna_data_admissao].dt.year == selected_year)
    ]

    denominador = len(df_admitidos_no_mes)
    df_admitidos_no_mes[coluna_desnutricao] = df_admitidos_no_mes[coluna_desnutricao].astype(str)
    is_desnutrido_raw_1 = df_admitidos_no_mes[coluna_desnutricao].eq('1')
    is_desnutrido_raw_2 = df_admitidos_no_mes[coluna_desnutricao].eq('1.0')
    numerador = (is_desnutrido_raw_1 | is_desnutrido_raw_2).sum()

    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0
    return taxa, numerador, denominador

# --- FUNÇÃO 3: RELAÇÃO DIETA ---
def calculate_relacao_dieta(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0

    coluna_data_diario = 'data_diario'
    coluna_prescrito = 'volume_prescrito'
    coluna_infundido = 'volume_infundido_ml'

    if any(col not in df_diario.columns for col in [coluna_data_diario, coluna_prescrito, coluna_infundido]):
        return 0.0, 0, 0

    df_diario[coluna_data_diario] = pd.to_datetime(df_diario[coluna_data_diario], errors='coerce')
    df_diario[coluna_prescrito] = pd.to_numeric(df_diario[coluna_prescrito], errors='coerce')
    df_diario[coluna_infundido] = pd.to_numeric(df_diario[coluna_infundido], errors='coerce')

    df_diario_mes = df_diario[
        (df_diario[coluna_data_diario].dt.month == selected_month) &
        (df_diario[coluna_data_diario].dt.year == selected_year)
    ]

    denominador = df_diario_mes[coluna_prescrito].sum()
    numerador = df_diario_mes[coluna_infundido].sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 4: TEMPO ATÉ A META ---
def calculate_tempo_ate_meta(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_geral = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]
    else:
        df_geral = df
    
    col_adm = 'data_e_hora_admissao_uti'
    if col_adm not in df_geral.columns:
        return 0.0, 0, 0

    df_geral[col_adm] = pd.to_datetime(df_geral[col_adm], errors='coerce')
    df_admitidos_no_mes = df_geral[
        (df_geral[col_adm].dt.month == selected_month) &
        (df_geral[col_adm].dt.year == selected_year)
    ].dropna(subset=[col_adm])
    
    denominador = len(df_admitidos_no_mes)
    if denominador == 0:
        return 0.0, 0, 0 

    df_cohort = df_admitidos_no_mes[['record_id', col_adm]].copy()
    df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente'].copy()
    
    if 'data_diario' not in df_diario.columns or 'esta_na_meta' not in df_diario.columns:
        return 0.0, 0, denominador 

    df_diario['data_diario'] = pd.to_datetime(df_diario['data_diario'], errors='coerce')
    df_diario['esta_na_meta'] = df_diario['esta_na_meta'].astype(str).str.replace(r'\.0$', '', regex=True) 
    df_dias_meta_sim = df_diario[df_diario['esta_na_meta'] == '1'].dropna(subset=['data_diario'])
    
    df_primeira_meta = df_dias_meta_sim.groupby('record_id')['data_diario'].min().reset_index()
    df_primeira_meta.rename(columns={'data_diario': 'data_primeira_meta'}, inplace=True)

    df_merged = pd.merge(df_cohort, df_primeira_meta, on='record_id', how='left')
    df_merged['dias_ate_meta'] = (df_merged['data_primeira_meta'] - df_merged[col_adm]).dt.days
    df_merged.loc[df_merged['dias_ate_meta'] < 0, 'dias_ate_meta'] = 0
    
    numerador = df_merged['dias_ate_meta'].fillna(0).sum()
    media_dias = numerador / denominador if denominador > 0 else 0.0
    return media_dias, numerador, denominador

# --- FUNÇÃO 5: TEMPO MÉDIO DE VM ---
def calculate_tempo_medio_vm(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0

    coluna_data_diario = 'data_diario'
    coluna_vm = 'suporte_vm_ultimas_24h'
    coluna_paciente = 'record_id' 

    if any(col not in df_diario.columns for col in [coluna_data_diario, coluna_vm, coluna_paciente]):
        return 0.0, 0, 0

    df_diario[coluna_data_diario] = pd.to_datetime(df_diario[coluna_data_diario], errors='coerce')
    df_diario[coluna_vm] = df_diario[coluna_vm].astype(str).str.replace(r'\.0$', '', regex=True)

    df_diario_mes = df_diario[
        (df_diario[coluna_data_diario].dt.month == selected_month) &
        (df_diario[coluna_data_diario].dt.year == selected_year)
    ]

    df_dias_em_vm = df_diario_mes[df_diario_mes[coluna_vm] == '1']
    numerador = len(df_dias_em_vm)
    denominador = df_dias_em_vm[coluna_paciente].nunique()
    media_dias = numerador / denominador if denominador > 0 else 0.0 
    return media_dias, numerador, denominador

# --- FUNÇÃO 6: TAXA UTILIZAÇÃO VM ---
def calculate_taxa_utilizacao_vm(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0

    coluna_data_diario = 'data_diario'
    coluna_vm = 'suporte_vm_ultimas_24h'
    coluna_leito = 'paciente_ocupando_leito'

    if any(col not in df_diario.columns for col in [coluna_data_diario, coluna_vm, coluna_leito]):
        return 0.0, 0, 0

    df_diario[coluna_data_diario] = pd.to_datetime(df_diario[coluna_data_diario], errors='coerce')
    df_diario[coluna_vm] = df_diario[coluna_vm].astype(str).str.replace(r'\.0$', '', regex=True)
    df_diario[coluna_leito] = df_diario[coluna_leito].astype(str).str.replace(r'\.0$', '', regex=True)

    df_diario_mes = df_diario[
        (df_diario[coluna_data_diario].dt.month == selected_month) &
        (df_diario[coluna_data_diario].dt.year == selected_year)
    ]
    
    numerador = (df_diario_mes[coluna_vm] == '1').sum()
    denominador = (df_diario_mes[coluna_leito] == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 7: PROPORÇÃO EOT PALIATIVA ---
def calculate_taxa_eot_paliativa(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]

    coluna_data_eot = 'eot' 
    coluna_eot_sim_nao = 'eot_sim_nao' 
    coluna_eot_paliativa = 'eot_paliativa' 

    if any(col not in df.columns for col in [coluna_data_eot, coluna_eot_sim_nao, coluna_eot_paliativa]):
        return 0.0, 0, 0

    df[coluna_data_eot] = pd.to_datetime(df[coluna_data_eot], errors='coerce')
    df_eventos_mes = df[
        (df[coluna_data_eot].dt.month == selected_month) &
        (df[coluna_data_eot].dt.year == selected_year)
    ]

    df_eventos_mes[coluna_eot_sim_nao] = df_eventos_mes[coluna_eot_sim_nao].astype(str).str.replace(r'\.0$', '', regex=True)
    df_eventos_mes[coluna_eot_paliativa] = df_eventos_mes[coluna_eot_paliativa].astype(str).str.replace(r'\.0$', '', regex=True)

    denominador = (df_eventos_mes[coluna_eot_sim_nao] == '1').sum()
    numerador = (df_eventos_mes[coluna_eot_paliativa] == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 8: TAXA EOT ACIDENTAL ---
def calculate_taxa_eot_acidental(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]

    coluna_data_eot = 'eot' 
    coluna_eot_sim_nao = 'eot_sim_nao' 
    coluna_eot_acidental = 'eot_acidental' 

    if any(col not in df.columns for col in [coluna_data_eot, coluna_eot_sim_nao, coluna_eot_acidental]):
        return 0.0, 0, 0

    df[coluna_data_eot] = pd.to_datetime(df[coluna_data_eot], errors='coerce')
    df_eventos_mes = df[
        (df[coluna_data_eot].dt.month == selected_month) &
        (df[coluna_data_eot].dt.year == selected_year)
    ]

    df_eventos_mes[coluna_eot_sim_nao] = df_eventos_mes[coluna_eot_sim_nao].astype(str).str.replace(r'\.0$', '', regex=True)
    df_eventos_mes[coluna_eot_acidental] = df_eventos_mes[coluna_eot_acidental].astype(str).str.replace(r'\.0$', '', regex=True)

    denominador = (df_eventos_mes[coluna_eot_sim_nao] == '1').sum()
    numerador = (df_eventos_mes[coluna_eot_acidental] == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 9: TAXA RE-IOT 48H ---
def calculate_taxa_re_iot(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]

    coluna_data_eot = 'eot' 
    coluna_eot_sim_nao = 'eot_sim_nao' 
    coluna_eot_acidental = 'eot_acidental' 
    coluna_re_iot = 're_iot_sim_nao' 

    if any(col not in df.columns for col in [coluna_data_eot, coluna_eot_sim_nao, coluna_eot_acidental, coluna_re_iot]):
        return 0.0, 0, 0

    df[coluna_data_eot] = pd.to_datetime(df[coluna_data_eot], errors='coerce')
    df_eventos_mes = df[
        (df[coluna_data_eot].dt.month == selected_month) &
        (df[coluna_data_eot].dt.year == selected_year)
    ]

    df_eventos_mes[coluna_eot_sim_nao] = df_eventos_mes[coluna_eot_sim_nao].astype(str).str.replace(r'\.0$', '', regex=True)
    df_eventos_mes[coluna_eot_acidental] = df_eventos_mes[coluna_eot_acidental].astype(str).str.replace(r'\.0$', '', regex=True)
    df_eventos_mes[coluna_re_iot] = df_eventos_mes[coluna_re_iot].astype(str).str.replace(r'\.0$', '', regex=True)

    numerador = (df_eventos_mes[coluna_re_iot] == '1').sum()
    total_eots = (df_eventos_mes[coluna_eot_sim_nao] == '1').sum()
    eots_acidentais = (df_eventos_mes[coluna_eot_acidental] == '1').sum()
    denominador = total_eots - eots_acidentais

    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 10: TAXA UTILIZAÇÃO CVC ---
def calculate_taxa_utilizacao_cvc(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0

    coluna_data_diario = 'data_diario'
    coluna_cvc = 'uso_cvc_nas_ultimas_24h' 
    coluna_leito = 'paciente_ocupando_leito' 

    if any(col not in df_diario.columns for col in [coluna_data_diario, coluna_cvc, coluna_leito]):
        return 0.0, 0, 0

    df_diario[coluna_data_diario] = pd.to_datetime(df_diario[coluna_data_diario], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario[coluna_data_diario].dt.month == selected_month) &
        (df_diario[coluna_data_diario].dt.year == selected_year)
    ]
    
    numerador = (df_diario_mes[coluna_cvc].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    denominador = (df_diario_mes[coluna_leito].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 11: TAXA UTILIZAÇÃO SVD ---
def calculate_taxa_utilizacao_svd(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0

    coluna_data_diario = 'data_diario'
    coluna_svd = 'uso_de_svd_nas_ultimas_24h' 
    coluna_leito = 'paciente_ocupando_leito' 

    if any(col not in df_diario.columns for col in [coluna_data_diario, coluna_svd, coluna_leito]):
        return 0.0, 0, 0

    df_diario[coluna_data_diario] = pd.to_datetime(df_diario[coluna_data_diario], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario[coluna_data_diario].dt.month == selected_month) &
        (df_diario[coluna_data_diario].dt.year == selected_year)
    ]
    
    numerador = (df_diario_mes[coluna_svd].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    denominador = (df_diario_mes[coluna_leito].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 12: TAXA UTILIZAÇÃO DIALISE ---
def calculate_taxa_utilizacao_dialise(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0

    coluna_data_diario = 'data_diario'
    coluna_dialise = 'di_lise_nas_ultimas_24h' 
    coluna_leito = 'paciente_ocupando_leito' 

    if any(col not in df_diario.columns for col in [coluna_data_diario, coluna_dialise, coluna_leito]):
        return 0.0, 0, 0

    df_diario[coluna_data_diario] = pd.to_datetime(df_diario[coluna_data_diario], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario[coluna_data_diario].dt.month == selected_month) &
        (df_diario[coluna_data_diario].dt.year == selected_year)
    ]
    
    numerador = (df_diario_mes[coluna_dialise].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    denominador = (df_diario_mes[coluna_leito].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 13: TAXA UTILIZAÇÃO DVA ---
def calculate_taxa_utilizacao_dva(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0

    coluna_data_diario = 'data_diario'
    coluna_dva = 'dva_nas_ultimas_24h' 
    coluna_leito = 'paciente_ocupando_leito' 

    if any(col not in df_diario.columns for col in [coluna_data_diario, coluna_dva, coluna_leito]):
        return 0.0, 0, 0

    df_diario[coluna_data_diario] = pd.to_datetime(df_diario[coluna_data_diario], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario[coluna_data_diario].dt.month == selected_month) &
        (df_diario[coluna_data_diario].dt.year == selected_year)
    ]
    
    numerador = (df_diario_mes[coluna_dva].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    denominador = (df_diario_mes[coluna_leito].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 14: TAXA INCIDÊNCIA LPP ---
def calculate_taxa_incidencia_lpp(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0
    df_diario['data_diario'] = pd.to_datetime(df_diario['data_diario'], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario['data_diario'].dt.month == selected_month) &
        (df_diario['data_diario'].dt.year == selected_year)
    ]
    denominador = (df_diario_mes['paciente_ocupando_leito'].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()

    df_g = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')] if 'redcap_repeat_instrument' in df.columns else df
    if 'lesao_pressao_data' not in df_g.columns:
        return 0.0, 0, denominador
        
    df_g['lesao_pressao_data'] = pd.to_datetime(df_g['lesao_pressao_data'], errors='coerce')
    df_lpp_mes = df_g[
        (df_g['lesao_pressao_data'].dt.month == selected_month) &
        (df_g['lesao_pressao_data'].dt.year == selected_year)
    ]
    numerador = (df_lpp_mes['teve_lesao_por_pressao'].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 15: TAXA INCIDÊNCIA FLEBITE ---
def calculate_taxa_incidencia_flebite(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0
    df_diario['data_diario'] = pd.to_datetime(df_diario['data_diario'], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario['data_diario'].dt.month == selected_month) &
        (df_diario['data_diario'].dt.year == selected_year)
    ]
    denominador = (df_diario_mes['paciente_ocupando_leito'].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()

    df_g = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')] if 'redcap_repeat_instrument' in df.columns else df
    if 'flebite_data' not in df_g.columns:
        return 0.0, 0, denominador

    df_g['flebite_data'] = pd.to_datetime(df_g['flebite_data'], errors='coerce')
    df_fleb_mes = df_g[
        (df_g['flebite_data'].dt.month == selected_month) &
        (df_g['flebite_data'].dt.year == selected_year)
    ]
    numerador = (df_fleb_mes['teve_flebite'].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 16: DENSIDADE INFECÇÃO CVC ---
def calculate_densidade_infeccao_cvc(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0
    df_diario['data_diario'] = pd.to_datetime(df_diario['data_diario'], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario['data_diario'].dt.month == selected_month) &
        (df_diario['data_diario'].dt.year == selected_year)
    ]
    denominador = (df_diario_mes['uso_cvc_nas_ultimas_24h'].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()

    df_g = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')] if 'redcap_repeat_instrument' in df.columns else df
    
    col_inf_data = 'infeccoes_durante_uti_data'
    if col_inf_data not in df_g.columns:
        return 0.0, 0, denominador

    df_g[col_inf_data] = pd.to_datetime(df_g[col_inf_data], errors='coerce')
    df_inf_mes = df_g[
        (df_g[col_inf_data].dt.month == selected_month) &
        (df_g[col_inf_data].dt.year == selected_year)
    ]
    numerador = pd.to_numeric(df_inf_mes['ics_numero'], errors='coerce').sum()
    taxa = (numerador / denominador) * 1000 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 17: DENSIDADE INFECÇÃO PAV ---
def calculate_densidade_infeccao_pav(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0
    df_diario['data_diario'] = pd.to_datetime(df_diario['data_diario'], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario['data_diario'].dt.month == selected_month) &
        (df_diario['data_diario'].dt.year == selected_year)
    ]
    denominador = (df_diario_mes['suporte_vm_ultimas_24h'].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()

    df_g = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')] if 'redcap_repeat_instrument' in df.columns else df
    
    col_inf_data = 'infeccoes_durante_uti_data'
    if col_inf_data not in df_g.columns:
        return 0.0, 0, denominador

    df_g[col_inf_data] = pd.to_datetime(df_g[col_inf_data], errors='coerce')
    df_inf_mes = df_g[
        (df_g[col_inf_data].dt.month == selected_month) &
        (df_g[col_inf_data].dt.year == selected_year)
    ]
    numerador = pd.to_numeric(df_inf_mes['pavm_numero'], errors='coerce').sum()
    taxa = (numerador / denominador) * 1000 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 18: DENSIDADE INFECÇÃO ITU ---
def calculate_densidade_infeccao_itu(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0
    df_diario['data_diario'] = pd.to_datetime(df_diario['data_diario'], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario['data_diario'].dt.month == selected_month) &
        (df_diario['data_diario'].dt.year == selected_year)
    ]
    denominador = (df_diario_mes['uso_de_svd_nas_ultimas_24h'].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()

    df_g = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')] if 'redcap_repeat_instrument' in df.columns else df
    
    col_inf_data = 'infeccoes_durante_uti_data'
    if col_inf_data not in df_g.columns:
        return 0.0, 0, denominador

    df_g[col_inf_data] = pd.to_datetime(df_g[col_inf_data], errors='coerce')
    df_inf_mes = df_g[
        (df_g[col_inf_data].dt.month == selected_month) &
        (df_g[col_inf_data].dt.year == selected_year)
    ]
    numerador = pd.to_numeric(df_inf_mes['itu_numero'], errors='coerce').sum()
    taxa = (numerador / denominador) * 1000 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 19: DIÁRIAS EVITÁVEIS ---
def calculate_diarias_evitaveis(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0
    df_diario['data_diario'] = pd.to_datetime(df_diario['data_diario'], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario['data_diario'].dt.month == selected_month) &
        (df_diario['data_diario'].dt.year == selected_year)
    ]
    denominador = (df_diario_mes['paciente_ocupando_leito'].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()

    df_g = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')] if 'redcap_repeat_instrument' in df.columns else df
    
    col_sol_alta = 'data_solicitacao_alta'
    if col_sol_alta not in df_g.columns:
        return 0.0, 0, denominador

    df_altas = aplicar_filtro_coorte_desfecho(df_g, selected_month, selected_year, 'data_do_desfecho_uti')
    if df_altas.empty:
        return 0.0, 0, denominador

    df_altas[col_sol_alta] = pd.to_datetime(df_altas[col_sol_alta], errors='coerce')
    df_altas['data_do_desfecho_uti'] = pd.to_datetime(df_altas['data_do_desfecho_uti'], errors='coerce')
    df_altas['desfecho_uti'] = df_altas['desfecho_uti'].astype(str).str.replace(r'\.0$', '', regex=True)

    df_validas = df_altas[df_altas['desfecho_uti'].isin(['1', '3'])].dropna(subset=[col_sol_alta, 'data_do_desfecho_uti'])
    df_validas['dias_evitados'] = (df_validas['data_do_desfecho_uti'] - df_validas[col_sol_alta]).dt.days
    df_validas.loc[df_validas['dias_evitados'] < 0, 'dias_evitados'] = 0
    
    numerador = df_validas['dias_evitados'].sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0 
    return taxa, numerador, denominador

# --- FUNÇÃO 20: SAPS-3 MÉDIA ---
def calculate_saps3_media(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]
        
    coluna_data_admissao = 'data_e_hora_admissao_uti'
    coluna_saps_pontos = 'saps_3_pontuacao'

    if coluna_data_admissao not in df.columns:
        return 0.0, 0.0, 0

    df[coluna_data_admissao] = pd.to_datetime(df[coluna_data_admissao], errors='coerce')
    df_admitidos_no_mes = df[
        (df['data_e_hora_admissao_uti'].dt.month == selected_month) &
        (df['data_e_hora_admissao_uti'].dt.year == selected_year)
    ].dropna(subset=[coluna_data_admissao])
    
    if df_admitidos_no_mes.empty:
        return 0.0, 0.0, 0

    df_admitidos_no_mes[coluna_saps_pontos] = pd.to_numeric(df_admitidos_no_mes[coluna_saps_pontos], errors='coerce')
    media_pontuacao = df_admitidos_no_mes[coluna_saps_pontos].mean()
    count_pacientes = len(df_admitidos_no_mes.dropna(subset=[coluna_saps_pontos]))

    # Equação Logística Padrão América Central e do Sul
    if not pd.isna(media_pontuacao) and media_pontuacao > 0:
        logit = -5.41775145 + (0.08106960 * media_pontuacao)
        media_percentual = (1 / (1 + np.exp(-logit))) * 100
    else:
        media_percentual = 0.0

    return (media_pontuacao if not pd.isna(media_pontuacao) else 0.0, 
            media_percentual, 
            count_pacientes)

# --- FUNÇÃO 21: TEMPO MÉDIO DE PERMANÊNCIA ---
def calculate_tempo_medio_permanencia(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    
    if 'redcap_repeat_instrument' in df.columns:
        df_diario = df[df['redcap_repeat_instrument'] == 'diario_paciente']
    else:
        return 0.0, 0, 0
    df_diario['data_diario'] = pd.to_datetime(df_diario['data_diario'], errors='coerce')
    df_diario_mes = df_diario[
        (df_diario['data_diario'].dt.month == selected_month) &
        (df_diario['data_diario'].dt.year == selected_year)
    ]
    numerador = (df_diario_mes['paciente_ocupando_leito'].astype(str).str.replace(r'\.0$', '', regex=True) == '1').sum()

    df_g = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')] if 'redcap_repeat_instrument' in df.columns else df
    df_saidas_coorte = aplicar_filtro_coorte_desfecho(df_g, selected_month, selected_year, 'data_do_desfecho_uti')
    denominador = len(df_saidas_coorte)

    media = (numerador / denominador) if denominador > 0 else 0.0
    return media, numerador, denominador

# --- FUNÇÃO 22: TAXA DE MORTALIDADE HOSPITALAR ---
def calculate_taxa_mortalidade_hospitalar(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]

    df_coorte_valida = aplicar_filtro_coorte_desfecho(df, selected_month, selected_year, 'desfecho_hospitalar')
    
    if df_coorte_valida.empty:
        return 0.0, 0, 0

    coluna_desfecho = 'desfecho_hospitalar'
    df_coorte_valida[coluna_desfecho] = df_coorte_valida[coluna_desfecho].astype(str)
    denominador = len(df_coorte_valida)
    
    is_obito_raw_1 = df_coorte_valida[coluna_desfecho].eq('2')
    is_obito_raw_2 = df_coorte_valida[coluna_desfecho].eq('2.0')
    numerador = (is_obito_raw_1 | is_obito_raw_2).sum()

    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0
    return taxa, numerador, denominador

# --- FUNÇÃO 23: TAXA DE REINTERNAÇÃO 48H ---
def calculate_taxa_reinternacao_48h(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]

    df_mes = aplicar_filtro_coorte_desfecho(df, selected_month, selected_year, 'data_do_desfecho_uti')
    if df_mes.empty:
        return 0.0, 0, 0

    df_mes['desfecho_uti'] = df_mes['desfecho_uti'].astype(str).str.replace(r'\.0$', '', regex=True)
    df_mes['reinternacao_na_uti_48h'] = df_mes['reinternacao_na_uti_48h'].astype(str).str.replace(r'\.0$', '', regex=True)

    denominador = (df_mes['desfecho_uti'] == '1').sum()
    numerador = (df_mes['reinternacao_na_uti_48h'] == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0
    return taxa, numerador, denominador

# --- FUNÇÃO 24: TAXA DE RE-SOLICITAÇÃO 48H ---
def calculate_taxa_resolicitacao_48h(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df = df[(df['redcap_repeat_instrument'].isnull()) | (df['redcap_repeat_instrument'] == '')]

    df_mes = aplicar_filtro_coorte_desfecho(df, selected_month, selected_year, 'data_do_desfecho_uti')
    if df_mes.empty:
        return 0.0, 0, 0

    df_mes['desfecho_uti'] = df_mes['desfecho_uti'].astype(str).str.replace(r'\.0$', '', regex=True)
    df_mes['re_solicitacao_do_leito'] = df_mes['re_solicitacao_do_leito'].astype(str).str.replace(r'\.0$', '', regex=True)

    denominador = (df_mes['desfecho_uti'] == '1').sum()
    numerador = (df_mes['re_solicitacao_do_leito'] == '1').sum()
    taxa = (numerador / denominador) * 100 if denominador > 0 else 0.0
    return taxa, numerador, denominador

# --- FUNÇÃO 25: SMR ---
def calculate_smr(df_raw, selected_month, selected_year):
    df = df_raw.copy()
    if 'redcap_repeat_instrument' in df.columns:
        df_geral = df[df['redcap_repeat_instrument'].isna() | (df['redcap_repeat_instrument'] == '')].copy()
    else:
        df_geral = df.copy()

    col_admissao = 'data_e_hora_admissao_uti'
    col_desfecho_hosp = 'desfecho_hospitalar'
    col_saps = 'saps_3_pontuacao'

    df_geral[col_admissao] = pd.to_datetime(df_geral[col_admissao], errors='coerce')
    df_geral[col_saps] = pd.to_numeric(df_geral[col_saps], errors='coerce')

    df_admitidos = df_geral[(df_geral[col_admissao].dt.month == selected_month) & (df_geral[col_admissao].dt.year == selected_year)].copy()
    df_admitidos = df_admitidos.drop_duplicates(subset=['record_id'])
    list_ids_denominador = df_admitidos['record_id'].tolist()
    denominador = len(df_admitidos)

    if denominador == 0:
        return 0.0, 0.0, 0.0, 0.0, 0, 0, [], [], 0.0, 0, []

    opcoes_validas = ['1', '2', '3', 1, 2, 3, 1.0, 2.0, 3.0]
    df_saidas = df_admitidos[df_admitidos[col_desfecho_hosp].isin(opcoes_validas)].copy()
    list_ids_numerador = df_saidas['record_id'].tolist()
    numerador_saidas = len(df_saidas)

    obitos = len(df_saidas[df_saidas[col_desfecho_hosp].astype(str).str.contains('2', na=False)])
    taxa_obs = (obitos / numerador_saidas * 100) if numerador_saidas > 0 else 0.0

    m_saps = df_saidas[col_saps].mean()
    if not pd.isna(m_saps) and m_saps > 0:
        logit = -5.41775145 + (0.08106960 * m_saps)
        taxa_esp = (1 / (1 + np.exp(-logit))) * 100
        smr = taxa_obs / taxa_esp if taxa_esp > 0 else 0
    else:
        taxa_esp, smr, m_saps = 0.0, 0.0, 0.0

    soma_saps = df_saidas[col_saps].sum() if not df_saidas.empty else 0.0
    count_saps = df_saidas[col_saps].count() if not df_saidas.empty else 0
    list_saps_vals = df_saidas[col_saps].dropna().tolist() if not df_saidas.empty else []

    return smr, taxa_obs, taxa_esp, m_saps, denominador, numerador_saidas, list_ids_denominador, list_ids_numerador, soma_saps, count_saps, list_saps_vals

# --- FUNÇÃO 26: SRU ---
def calculate_sru(df_clinico_raw, selected_month, selected_year):
    df = df_clinico_raw.copy()
    bins = [-float('inf'), 24, 34, 44, 54, 64, 74, 84, 94, float('inf')]
    labels = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    los_esperado_map = {1: 2.26, 2: 2.67, 3: 3.48, 4: 4.93, 5: 7.22, 6: 11.87, 7: 21.23, 8: 34.32, 9: 54.85}
    
    if 'redcap_repeat_instrument' in df.columns:
        df_g = df[df['redcap_repeat_instrument'].isna() | (df['redcap_repeat_instrument'] == '')].copy()
        df_g = df_g.drop_duplicates(subset=['record_id'], keep='last')
    else:
        df_g = df

    df_mes = aplicar_filtro_coorte_desfecho(df_g, selected_month, selected_year, 'data_do_desfecho_uti')
    if df_mes.empty or 'saps_3_pontuacao' not in df_mes.columns:
        return 0.0, 0.0, 0.0, 0

    df_mes['saps_3_pontuacao'] = pd.to_numeric(df_mes['saps_3_pontuacao'], errors='coerce')
    df_mes['desfecho_uti'] = df_mes['desfecho_uti'].astype(str).str.replace(r'\.0$', '', regex=True)
    df_mes = df_mes.dropna(subset=['saps_3_pontuacao', 'data_do_desfecho_uti', 'data_e_hora_admissao_uti'])

    df_sobreviventes = df_mes[df_mes['desfecho_uti'].isin(['1', '3'])].copy()
    if df_sobreviventes.empty:
        return 0.0, 0.0, 0.0, 0

    df_sobreviventes['data_do_desfecho_uti'] = pd.to_datetime(df_sobreviventes['data_do_desfecho_uti'])
    df_sobreviventes['data_e_hora_admissao_uti'] = pd.to_datetime(df_sobreviventes['data_e_hora_admissao_uti'])
    
    df_sobreviventes['los_observado'] = (df_sobreviventes['data_do_desfecho_uti'] - df_sobreviventes['data_e_hora_admissao_uti']).dt.days
    df_sobreviventes.loc[df_sobreviventes['los_observado'] < 0, 'los_observado'] = 0
    numerador_observado = df_sobreviventes['los_observado'].sum()

    df_sobreviventes['estrato_saps'] = pd.cut(df_sobreviventes['saps_3_pontuacao'], bins=bins, right=True, labels=labels)
    df_sobreviventes['los_esperado'] = pd.to_numeric(df_sobreviventes['estrato_saps'].map(los_esperado_map), errors='coerce')
    denominador_esperado = df_sobreviventes['los_esperado'].sum()

    sru = numerador_observado / denominador_esperado if denominador_esperado > 0 else 0.0
    return sru, numerador_observado, denominador_esperado, len(df_sobreviventes)