import streamlit as st
import streamlit_authenticator as stauth
import yaml
import pandas as pd
import datetime
import indicadores_clinicos 
from data_loader import load_redcap_data 
import admin_report

# --- Configuração da Página ---
st.set_page_config(page_title="Sistema de Gestão - UTI Clínica HCFMB", page_icon="🏥", layout="wide")

# --- Autenticação via Secrets ---
# Lemos a string salva no secrets e transformamos em dicionário
auth_config = yaml.safe_load(st.secrets["auth"]["config"])

authenticator = stauth.Authenticate(
    auth_config['credentials'],
    auth_config['cookie']['name'],
    auth_config['cookie']['key'],
    auth_config['cookie']['expiry_days']
)

# Apenas chama o login, sem tentar desempacotar o retorno
authenticator.login(location='main')

# Acessa os dados através das propriedades do objeto autenticator
name = st.session_state.get('name')
authentication_status = st.session_state.get('authentication_status')
username = st.session_state.get('username')

# --- Fluxo de Autenticação ---
if authentication_status == False:
    st.error('Usuário ou senha incorretos')
elif authentication_status == None:
    st.warning('Por favor, digite seu usuário e senha')

# --- DASHBOARD (SÓ RODA SE LOGADO) ---
if authentication_status:
    # ... resto do seu código ...
    authenticator.logout('Sair', 'sidebar')
    st.sidebar.write(f'Bem-vindo, **{name}**')

    # --- Filtros ---

    # Módulos do projeto
    import indicadores_clinicos 
    from data_loader import load_redcap_data 
    import admin_report

    # --- Configuração da Página ---
    st.set_page_config(
        page_title="Sistema de Gestão - UTI Clínica",
        page_icon="🏥",
        layout="wide"
    )

    # --- Sidebar de Filtros ---
    with st.sidebar:
        st.title("Filtros de Análise")
        today = datetime.date.today()
        default_year = today.year
        default_month = today.month
        year_options = list(range(default_year - 5, default_year + 1))
        selected_year = st.selectbox("Ano", options=year_options, index=len(year_options) - 1)
        
        months = {
            "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, 
            "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8, 
            "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
        }
        month_name = st.selectbox("Mês", options=months.keys(), index=default_month - 1)
        selected_month = months[month_name]

        st.markdown("---") 
        if st.button("Recarregar Dados (Limpar Cache)", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # --- Carregamento dos Dados ---
    @st.cache_data
    def get_data(api_key_geral, api_key_enfermagem):
        try:
            df_admin, df_clinico = load_redcap_data(api_key_geral, api_key_enfermagem)
            return df_admin, df_clinico
        except Exception as e:
            st.error(f"Erro na conexão com REDCap: {e}")
            st.stop()

    try:
        df_admin_data, df_clinical_data = get_data(
            st.secrets["api_key_geral"], 
            st.secrets["api_key_enfermagem"]
        )
    except Exception as e:
        st.error("Verifique as chaves de API nos Secrets do Streamlit ou nas configurações locais.")
        st.stop()

    # --- Título Principal ---
    st.title("Sistema de Gestão – UTI Clínica HCFMB")
    st.markdown(f"### Análise de **{month_name} de {selected_year}**")

    # --- Criação das Abas ---
    tab_medica, tab_enfermagem, tab_fisioterapia, tab_nutricao = st.tabs(
        ["🩺 Médica", "💉 Enfermagem", "🫁 Fisioterapia", "🥗 Nutrição"]
    )

    # ==============================================================================
    # ABA 1: MÉDICA
    # ==============================================================================
    with tab_medica:
        st.subheader("Indicadores Médicos e de Desempenho")
        if not df_clinical_data.empty:
            # Cálculos[cite: 2, 4]
            media_saps_pontos, media_saps_perc, num_pac_saps = indicadores_clinicos.calculate_saps3_media(df_clinical_data, selected_month, selected_year)
            taxa_mortalidade, num_obitos, num_desfechos = indicadores_clinicos.calculate_taxa_mortalidade_uti(df_clinical_data, selected_month, selected_year)
            taxa_mort_hosp, num_obitos_hosp, num_desfechos_hosp = indicadores_clinicos.calculate_taxa_mortalidade_hospitalar(df_clinical_data, selected_month, selected_year)
            media_permanencia, num_pac_dias, num_desfechos_perm = indicadores_clinicos.calculate_tempo_medio_permanencia(df_clinical_data, selected_month, selected_year)
            taxa_reint_48h, num_reint, num_altas_reint = indicadores_clinicos.calculate_taxa_reinternacao_48h(df_clinical_data, selected_month, selected_year)
            taxa_resol_48h, num_resol, num_altas_resol = indicadores_clinicos.calculate_taxa_resolicitacao_48h(df_clinical_data, selected_month, selected_year)
            
            taxa_inf_cvc, num_inf_cvc, num_cvc_dias_inf = indicadores_clinicos.calculate_densidade_infeccao_cvc(df_clinical_data, selected_month, selected_year)
            taxa_inf_pav, num_inf_pav, num_vm_dias_inf = indicadores_clinicos.calculate_densidade_infeccao_pav(df_clinical_data, selected_month, selected_year)
            taxa_inf_itu, num_inf_itu, num_svd_dias_inf = indicadores_clinicos.calculate_densidade_infeccao_itu(df_clinical_data, selected_month, selected_year)
            taxa_diarias_evit, num_dias_evit, num_pac_dias_evit = indicadores_clinicos.calculate_diarias_evitaveis(df_clinical_data, selected_month, selected_year)

            smr_val, tx_obs, tx_esp, m_saps_val, den_val, num_val, ids_den, ids_num, soma_saps, count_saps, list_saps_vals = indicadores_clinicos.calculate_smr(df_clinical_data, selected_month, selected_year)
            sru_val, dias_obs, dias_esp, count_sru = indicadores_clinicos.calculate_sru(df_clinical_data, selected_month, selected_year)

            # Exibição: Resultados e Gravidade[cite: 2]
            st.write("#### 📌 Indicadores de Resultado e Gravidade")
            colR1, colR2, colR3, colR4 = st.columns(4)
            colR1.metric("Mortalidade UTI", f"{taxa_mortalidade:.1f} %", help=f"Óbitos: {num_obitos} / Saídas UTI: {num_desfechos} no período")
            colR2.metric("Mortalidade Hospitalar", f"{taxa_mort_hosp:.1f} %", help="Óbitos hospitalares / Total de saídas hospitalares da coorte")
            colR3.metric("Permanência Média", f"{media_permanencia:.1f} dias", help="Total de pacientes-dia / Saídas da UTI")
            colR4.metric("Média SAPS 3", f"{media_saps_pontos:.1f} pts ({media_saps_perc:.1f}%)", help=f"Média de pontuação SAPS 3 (Predição de mortalidade: {media_saps_perc:.1f}%) para {num_pac_saps} pacientes avaliados")

            colR5, colR6, _, _ = st.columns(4)
            colR5.metric("Reinternação em 48h", f"{taxa_reint_48h:.1f} %", help=f"Reinternações: {num_reint} / Altas UTI: {num_altas_reint} no período")
            colR6.metric("Re-solicitação de Leito 48h", f"{taxa_resol_48h:.1f} %", help=f"Re-solicitações: {num_resol} / Altas UTI: {num_altas_resol} no período")

            # Exibição: Infecções e Processo[cite: 2]
            st.markdown("---")
            st.write("#### 🛡️ Densidade de Infecção (x 1.000 dias de dispositivo) e Processos")
            colI1, colI2, colI3, colI4 = st.columns(4)
            colI1.metric("Infecção de Corrente Sanguínea (CVC)", f"{taxa_inf_cvc:.1f}", help="Nº de ICS associadas a CVC / Total de dias de uso de CVC * 1000")
            colI2.metric("Pneumonia Associada à VM (PAV)", f"{taxa_inf_pav:.1f}", help="Nº de PAV / Total de dias de uso de VM * 1000")
            colI3.metric("Infecção do Trato Urinário (ITU)", f"{taxa_inf_itu:.1f}", help="Nº de ITU associadas a SVD / Total de dias de uso de SVD * 1000")
            colI4.metric("Taxa de Diárias Evitáveis", f"{taxa_diarias_evit:.1f} %", help="Total de dias aguardando vaga externa após alta / Total de pacientes-dia")

            # Exibição: Desempenho Clínico (SMR / SRU)[cite: 2]
            st.markdown("---")
            st.write("#### 📊 Desempenho Clínico e Eficiência (SMR / SRU)")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("SMR (Padronizado)", f"{smr_val:.6f}", delta=f"{smr_val - 1:.6f}", delta_color="inverse", help="Standardized Mortality Ratio (Mortalidade Observada / Esperada via SAPS 3)")
            c2.metric("SRU (Recursos)", f"{sru_val:.2f}", delta=f"{sru_val - 1:.2f}", delta_color="inverse", help="Standardized Resource Use (Permanência Observada / Esperada via SAPS 3)")
            c3.metric("Admitidos no Mês", f"{den_val}", help="Total de admissões registradas no período selecionado")
            c4.metric("Desfechos Hospitalares", f"{num_val}", help="Pacientes da coorte que já completaram o desfecho hospitalar")
            c5.metric("Média SAPS 3 (Grupo SMR)", f"{m_saps_val:.6f}", help="Média de pontuação SAPS 3 dos pacientes com desfecho hospitalar")

            with st.expander("🔍 Auditoria SMR: Lista de IDs Processados"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**IDs Admitidos no período ({len(ids_den)}):**")
                    st.code(", ".join(map(str, ids_den)))
                with col_b:
                    st.write(f"**IDs Admitidos que já possuem Desfecho Hospitalar ({len(ids_num)}):**")
                    st.code(", ".join(map(str, ids_num)))

            # --- EXIBIÇÃO: DADOS BASE PARA CÁLCULOS (COMPLETO) ---
            st.markdown("---")
            st.write("#### 📊 Auditoria Completa: Dados Base para Cálculos")
            
            # 1. Indicadores de Resultado e Mortalidade
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Óbitos UTI", f"{num_obitos}")
            b2.metric("Saídas UTI", f"{num_desfechos}")
            b3.metric("Óbitos Hosp.", f"{num_obitos_hosp}")
            b4.metric("Saídas Hosp. (Coorte)", f"{num_desfechos_hosp}")
            
            # 2. SMR, SRU e SAPS 3
            b5, b6, b7, b8 = st.columns(4)
            b5.metric("Mortalidade Obs.", f"{tx_obs:.2f}%")
            b6.metric("Mortalidade Esp.", f"{tx_esp:.2f}%")
            b7.metric("Perm. Observada", f"{dias_obs:.1f} dias")
            b8.metric("Média SAPS 3 (pts)", f"{media_saps_pontos:.2f}")
            
            b9, b10, b11, b12 = st.columns(4)
            b9.metric("Predição Mort. (%)", f"{media_saps_perc:.2f}%")
            b10.metric("Pacientes Avaliados", f"{num_pac_saps}")
            b11.metric("Perm. Esperada", f"{dias_esp:.1f} dias")
            b12.metric("Pacientes Desfecho (SRU)", f"{count_sru}")
            
            # 3. Processos e Dispositivos
            b13, b14, b15, b16 = st.columns(4)
            b13.metric("Dias Evitáveis", f"{num_dias_evit}")
            b14.metric("Pacientes-Dia Total", f"{num_pac_dias}")
            b15.metric("Nº ICS (CVC)", f"{num_inf_cvc}")
            b16.metric("Dias Uso CVC", f"{num_cvc_dias_inf}")
            
            b17, b18, b19, b20 = st.columns(4)
            b17.metric("Nº PAV (VM)", f"{num_inf_pav}")
            b18.metric("Dias Uso VM", f"{num_vm_dias_inf}")
            b19.metric("Nº ITU (SVD)", f"{num_inf_itu}")
            b20.metric("Dias Uso SVD", f"{num_svd_dias_inf}")
            
            # 4. Reinternações
            b21, b22, b23, b24 = st.columns(4)
            b21.metric("Reint. UTI 48h", f"{num_reint}")
            b22.metric("Altas UTI (Reint.)", f"{num_altas_reint}")
            b23.metric("Re-solic. UTI 48h", f"{num_resol}")
            b24.metric("Total Altas (Sol.)", f"{num_altas_resol}")

            # Exibição: Prova Real Médica[cite: 2]
            st.markdown("---")
            with st.expander("🛠️ Prova Real dos Cálculos - Médica (Auditoria Detalhada)"):
                prova_real_med = [
                    {"Indicador": "Mortalidade UTI (%)", "Numerador (N)": num_obitos, "Denominador (D)": num_desfechos, "Fórmula": "(N / D) * 100", "Resultado": f"{taxa_mortalidade:.2f} %"},
                    {"Indicador": "Mortalidade Hospitalar (%)", "Numerador (N)": num_obitos_hosp, "Denominador (D)": num_desfechos_hosp, "Fórmula": "(N / D) * 100", "Resultado": f"{taxa_mort_hosp:.2f} %"},
                    {"Indicador": "Permanência Média (dias)", "Numerador (N)": num_pac_dias, "Denominador (D)": num_desfechos_perm, "Fórmula": "N / D", "Resultado": f"{media_permanencia:.2f} dias"},
                    {"Indicador": "Média SAPS 3 (pontos)", "Numerador (N)": f"{media_saps_pontos * num_pac_saps:.1f}", "Denominador (D)": num_pac_saps, "Fórmula": "Soma Pontos / Avaliados", "Resultado": f"{media_saps_pontos:.2f} pts"},
                    {"Indicador": "Reinternação 48h (%)", "Numerador (N)": num_reint, "Denominador (D)": num_altas_reint, "Fórmula": "(N / D) * 100", "Resultado": f"{taxa_reint_48h:.2f} %"},
                    {"Indicador": "Re-solicitação 48h (%)", "Numerador (N)": num_resol, "Denominador (D)": num_altas_resol, "Fórmula": "(N / D) * 100", "Resultado": f"{taxa_resol_48h:.2f} %"},
                    {"Indicador": "Densidade de Infecção CVC", "Numerador (N)": num_inf_cvc, "Denominador (D)": num_cvc_dias_inf, "Fórmula": "(N / D) * 1000", "Resultado": f"{taxa_inf_cvc:.2f}"},
                    {"Indicador": "Densidade de Infecção PAV", "Numerador (N)": num_inf_pav, "Denominador (D)": num_vm_dias_inf, "Fórmula": "(N / D) * 1000", "Resultado": f"{taxa_inf_pav:.2f}"},
                    {"Indicador": "Densidade de Infecção ITU", "Numerador (N)": num_inf_itu, "Denominador (D)": num_svd_dias_inf, "Fórmula": "(N / D) * 1000", "Resultado": f"{taxa_inf_itu:.2f}"},
                    {"Indicador": "Taxa de Diárias Evitáveis (%)", "Numerador (N)": num_dias_evit, "Denominador (D)": num_pac_dias_evit, "Fórmula": "(N / D) * 100", "Resultado": f"{taxa_diarias_evit:.2f} %"},
                    {"Indicador": "SMR (Padronizado)", "Numerador (N)": f"{tx_obs:.2f}% (Obs)", "Denominador (D)": f"{tx_esp:.2f}% (Esp)", "Fórmula": "Mort. Obs / Mort. Esp", "Resultado": f"{smr_val:.6f}"},
                    {"Indicador": "Média SAPS 3 (Grupo SMR)", "Numerador (N)": f"{soma_saps:.1f} (Soma Pts)", "Denominador (D)": f"{count_saps} (Avaliados)", "Fórmula": "N / D", "Resultado": f"{m_saps_val:.6f}"},
                    {"Indicador": "SRU (Recursos)", "Numerador (N)": f"{dias_obs:.1f} dias", "Denominador (D)": f"{dias_esp:.1f} dias", "Fórmula": "Perm. Obs / Perm. Esp", "Resultado": f"{sru_val:.2f}"},
                ]
                st.dataframe(pd.DataFrame(prova_real_med), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum dado clínico disponível para este período.")

    # ==============================================================================
    # ABA 2: ENFERMAGEM
    # ==============================================================================
    with tab_enfermagem:
        st.subheader("Indicadores Administrativos e Assistenciais de Enfermagem")
        if not df_admin_data.empty:
            admin_report.display_admin_metrics(df_admin_data, selected_month, selected_year)
        
        st.markdown("---")
        if not df_clinical_data.empty:
            st.write("#### 🔌 Utilização de Dispositivos Invasivos (Diário)")
            t_cvc, n_cvc, d_cvc = indicadores_clinicos.calculate_taxa_utilizacao_cvc(df_clinical_data, selected_month, selected_year)
            t_svd, n_svd, d_svd = indicadores_clinicos.calculate_taxa_utilizacao_svd(df_clinical_data, selected_month, selected_year)
            t_dial, n_dial, d_dial = indicadores_clinicos.calculate_taxa_utilizacao_dialise(df_clinical_data, selected_month, selected_year)
            t_dva, n_dva, d_dva = indicadores_clinicos.calculate_taxa_utilizacao_dva(df_clinical_data, selected_month, selected_year)
            
            ce1, ce2, ce3, ce4 = st.columns(4)
            ce1.metric("Taxa Utilização CVC", f"{t_cvc:.1f} %", help="Dias de uso de Cateter Venoso Central / Total de pacientes-dia")
            ce2.metric("Taxa Utilização SVD", f"{t_svd:.1f} %", help="Dias de uso de Sonda Vesical de Demora / Total de pacientes-dia")
            ce3.metric("Taxa Utilização Diálise", f"{t_dial:.1f} %", help="Dias de terapia renal substitutiva (Diálise) / Total de pacientes-dia")
            ce4.metric("Taxa Utilização DVA", f"{t_dva:.1f} %", help="Dias de uso de Droga Vasoativa / Total de pacientes-dia")

            st.markdown("---")
            st.write("#### ⚠️ Indicadores de Incidência de Eventos Adversos")
            t_lpp, n_lpp, d_lpp = indicadores_clinicos.calculate_taxa_incidencia_lpp(df_clinical_data, selected_month, selected_year)
            t_fleb, n_fleb, d_fleb = indicadores_clinicos.calculate_taxa_incidencia_flebite(df_clinical_data, selected_month, selected_year)
            
            ce5, ce6, _, _ = st.columns(4)
            ce5.metric("Taxa Incidência LPP", f"{t_lpp:.1f} %", help="Pacientes que desenvolveram Lesão por Pressão na UTI / Total de pacientes-dia")
            ce6.metric("Taxa Incidência Flebite", f"{t_fleb:.1f} %", help="Pacientes que desenvolveram Flebite na UTI / Total de pacientes-dia")

            st.markdown("---")
            with st.expander("🛠️ Prova Real dos Cálculos - Enfermagem (Auditoria Detalhada)"):
                prova_real_enf = [
                    {"Indicador": "Utilização de CVC (%)", "Numerador (N)": n_cvc, "Denominador (D)": d_cvc, "Fórmula": "(N / D) * 100", "Resultado": f"{t_cvc:.2f} %"},
                    {"Indicador": "Utilização de SVD (%)", "Numerador (N)": n_svd, "Denominador (D)": d_svd, "Fórmula": "(N / D) * 100", "Resultado": f"{t_svd:.2f} %"},
                    {"Indicador": "Utilização de Diálise (%)", "Numerador (N)": n_dial, "Denominador (D)": d_dial, "Fórmula": "(N / D) * 100", "Resultado": f"{t_dial:.2f} %"},
                    {"Indicador": "Utilização de DVA (%)", "Numerador (N)": n_dva, "Denominador (D)": d_dva, "Fórmula": "(N / D) * 100", "Resultado": f"{t_dva:.2f} %"},
                    {"Indicador": "Incidência de LPP (%)", "Numerador (N)": n_lpp, "Denominador (D)": d_lpp, "Fórmula": "(N / D) * 100", "Resultado": f"{t_lpp:.2f} %"},
                    {"Indicador": "Incidência de Flebite (%)", "Numerador (N)": n_fleb, "Denominador (D)": d_fleb, "Fórmula": "(N / D) * 100", "Resultado": f"{t_fleb:.2f} %"},
                ]
                st.dataframe(pd.DataFrame(prova_real_enf), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum dado clínico disponível para este período.")

    # ==============================================================================
    # ABA 3: FISIOTERAPIA
    # ==============================================================================
    with tab_fisioterapia:
        st.subheader("Indicadores Fisioterapêuticos e de Ventilação Mecânica")
        if not df_clinical_data.empty:
            m_vm, n_vm, d_vm = indicadores_clinicos.calculate_tempo_medio_vm(df_clinical_data, selected_month, selected_year)
            t_util_vm, n_util_vm, d_util_vm = indicadores_clinicos.calculate_taxa_utilizacao_vm(df_clinical_data, selected_month, selected_year)
            
            st.write("#### 🫁 Suporte Ventilatório")
            cf1, cf2, _, _ = st.columns(4)
            cf1.metric("Tempo Médio de VM", f"{m_vm:.1f} dias", help="Total de dias de VM / Número de pacientes que utilizaram VM")
            cf2.metric("Taxa de Utilização de VM", f"{t_util_vm:.1f} %", help="Total de dias de suporte ventilatório / Total de pacientes-dia")

            st.markdown("---")
            st.write("#### 🎯 Extubação e Retirada de Suporte (EOT)")
            t_pal, n_pal, d_pal = indicadores_clinicos.calculate_taxa_eot_paliativa(df_clinical_data, selected_month, selected_year)
            t_acid, n_acid, d_acid = indicadores_clinicos.calculate_taxa_eot_acidental(df_clinical_data, selected_month, selected_year)
            t_iot, n_iot, d_iot = indicadores_clinicos.calculate_taxa_re_iot(df_clinical_data, selected_month, selected_year)
            
            cf3, cf4, cf5, _ = st.columns(4)
            cf3.metric("EOT Paliativa", f"{t_pal:.1f} %", help="Extubações oro-traqueais paliativas / Total de extubações no período")
            cf4.metric("EOT Acidental", f"{t_acid:.1f} %", help="Extubações oro-traqueais acidentais / Total de extubações no período")
            cf5.metric("Re-intubação (Re-IOT 48h)", f"{t_iot:.1f} %", help="Pacientes reintubados em até 48h / (Total de EOT - EOT Acidentais)")

            st.markdown("---")
            with st.expander("🛠️ Prova Real dos Cálculos - Fisioterapia (Auditoria Detalhada)"):
                prova_real_fisio = [
                    {"Indicador": "Tempo Médio de VM (dias)", "Numerador (N)": n_vm, "Denominador (D)": d_vm, "Fórmula": "N / D", "Resultado": f"{m_vm:.2f} dias"},
                    {"Indicador": "Taxa de Utilização de VM (%)", "Numerador (N)": n_util_vm, "Denominador (D)": d_util_vm, "Fórmula": "(N / D) * 100", "Resultado": f"{t_util_vm:.2f} %"},
                    {"Indicador": "EOT Paliativa (%)", "Numerador (N)": n_pal, "Denominador (D)": d_pal, "Fórmula": "(N / D) * 100", "Resultado": f"{t_pal:.2f} %"},
                    {"Indicador": "EOT Acidental (%)", "Numerador (N)": n_acid, "Denominador (D)": d_acid, "Fórmula": "(N / D) * 100", "Resultado": f"{t_acid:.2f} %"},
                    {"Indicador": "Re-intubação em 48h (%)", "Numerador (N)": n_iot, "Denominador (D)": d_iot, "Fórmula": "(N / D) * 100", "Resultado": f"{t_iot:.2f} %"},
                ]
                st.dataframe(pd.DataFrame(prova_real_fisio), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum dado clínico disponível para este período.")

    # ==============================================================================
    # ABA 4: NUTRIÇÃO
    # ==============================================================================
    with tab_nutricao:
        st.subheader("Indicadores de Terapia Nutricional")
        if not df_clinical_data.empty:
            t_desn, n_desn, d_desn = indicadores_clinicos.calculate_taxa_desnutricao(df_clinical_data, selected_month, selected_year)
            t_dieta, n_dieta, d_dieta = indicadores_clinicos.calculate_relacao_dieta(df_clinical_data, selected_month, selected_year)
            m_meta, n_meta, d_meta = indicadores_clinicos.calculate_tempo_ate_meta(df_clinical_data, selected_month, selected_year)
            
            cn1, cn2, cn3, _ = st.columns(4)
            cn1.metric("Taxa de Desnutrição na Admissão", f"{t_desn:.1f} %", help="Pacientes com diagnóstico de desnutrição na admissão / Total de admitidos no mês")
            cn2.metric("Volume Infundido vs. Prescrito", f"{t_dieta:.1f} %", help="Somatória do volume de dieta infundido (ml) / Somatória do volume prescrito (ml)")
            cn3.metric("Tempo Média até Meta Calórica", f"{m_meta:.1f} dias", help="Média de dias desde a admissão até atingir a meta nutricional pela primeira vez")

            st.markdown("---")
            with st.expander("🛠️ Prova Real dos Cálculos - Nutrição (Auditoria Detalhada)"):
                prova_real_nutri = [
                    {"Indicador": "Taxa de Desnutrição (%)", "Numerador (N)": n_desn, "Denominador (D)": d_desn, "Fórmula": "(N / D) * 100", "Resultado": f"{t_desn:.2f} %"},
                    {"Indicador": "Infundido vs. Prescrito (%)", "Numerador (N)": f"{n_dieta:.0f} ml", "Denominador (D)": f"{d_dieta:.0f} ml", "Fórmula": "(N / D) * 100", "Resultado": f"{t_dieta:.2f} %"},
                    {"Indicador": "Dias até Meta Calórica", "Numerador (N)": f"{n_meta:.0f} dias", "Denominador (D)": d_meta, "Fórmula": "N / D", "Resultado": f"{m_meta:.2f} dias"},
                ]
                st.dataframe(pd.DataFrame(prova_real_nutri), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum dado clínico disponível para este período.")