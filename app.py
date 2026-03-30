import streamlit as st
import pandas as pd
from docx import Document
import re
import io

def extrair_dados_questoes(docx_file):
    try:
        doc = Document(docx_file)
        questoes = []
        paragrafos = [p.text for p in doc.paragraphs]
        conteudo = "\n".join(paragrafos)
        
        # Divisão pelo link (marcador de início de questão)
        # O padrão do Tec às vezes tem espaços ou variações, por isso o \s*
        blocos = re.split(r'www\.tecconcursos\.com\.br/questoes/\d+', conteudo)
        
        if len(blocos) <= 1:
            st.error("Não encontrei links do 'tecconcursos' no documento. Verifique se o padrão mudou.")
            return pd.DataFrame()

        for bloco in blocos[1:]:
            linhas = [l.strip() for l in bloco.strip().split('\n') if l.strip()]
            if len(linhas) < 4: continue

            # --- METADADOS (LINHA 1 E 2) ---
            # Ex: FGV - Esp Leg (ALERJ)/ALERJ/Nível IV/Administração Geral/2026
            meta_topo = linhas[0].split('/')
            banca_cargo = meta_topo[0].split(' - ')
            
            banca = banca_cargo[0] if len(banca_cargo) > 0 else ""
            cargo = banca_cargo[1] if len(banca_cargo) > 1 else ""
            orgao = meta_topo[1] if len(meta_topo) > 1 else ""
            ano = meta_topo[-1] if len(meta_topo) > 1 else ""

            # Ex: Direito Constitucional - Mandado de Injunção
            meta_assunto = linhas[1].split(' - ')
            disciplina = meta_assunto[0] if len(meta_assunto) > 0 else ""
            assunto = meta_assunto[1] if len(meta_assunto) > 1 else ""

            # --- BUSCA DE ÍNDICES (ALTERNATIVAS E GABARITO) ---
            idx_alternativas = []
            idx_gabarito = -1
            
            for i, linha in enumerate(linhas):
                l_strip = linha.strip()
                # Verifica a), b), c), d), e) ou Certo/Errado
                if re.match(r'^[a-h]\)\s*', l_strip.lower()) or l_strip in ["Certo", "Errado"]:
                    idx_alternativas.append(i)
                if "Gabarito:" in linha:
                    idx_gabarito = i

            # Se não achou gabarito ou alternativas, pula essa questão para não travar
            if not idx_alternativas or idx_gabarito == -1:
                continue

            # --- ENUNCIADO ---
            # Pega da linha 2 até a primeira alternativa encontrada
            enunciado = "\n".join(linhas[2:idx_alternativas[0]])

            # --- GABARITO ---
            letra_correta = ""
            match = re.search(r'Gabarito:\s*([A-E]|Certo|Errado|C|E)', linhas[idx_gabarito], re.IGNORECASE)
            if match:
                letra_correta = match.group(1).upper()

            # --- ALTERNATIVAS ---
            alts_extraidas = []
            for i in range(len(idx_alternativas)):
                inicio = idx_alternativas[i]
                fim = idx_alternativas[i+1] if i+1 < len(idx_alternativas) else idx_gabarito
                texto_alt = "\n".join(linhas[inicio:fim]).strip()
                alts_extraidas.append(texto_alt)

            # --- MONTAGEM DA LINHA ---
            row = {"Enunciado": enunciado}
            
            for i in range(1, 6): # Mapeia as 5 alternativas
                texto_da_alt = alts_extraidas[i-1] if i <= len(alts_extraidas) else ""
                check_correta = ""
                
                if texto_da_alt:
                    # Lógica de correção
                    letra_da_alt = texto_da_alt[0].upper() if ")" in texto_da_alt[:3] else ""
                    
                    is_correta = False
                    if letra_da_alt and letra_da_alt == letra_correta: is_correta = True
                    if texto_da_alt == "Certo" and letra_correta in ["C", "CERTO"]: is_correta = True
                    if texto_da_alt == "Errado" and letra_correta in ["E", "ERRADO"]: is_correta = True
                    
                    if is_correta:
                        check_correta = "CORRETA"

                row[f"Alternativa {i}"] = texto_da_alt
                row[f"Alt {i} Corr."] = check_correta

            row.update({
                "M1 (Banca)": banca, "M2 (Órgão)": orgao, "M3 (Cargo)": cargo,
                "M4 (Ano)": ano, "M5 (Disc.)": disciplina, "M6 (Assunto)": assunto
            })
            questoes.append(row)
            
        return pd.DataFrame(questoes)

    except Exception as e:
        st.error(f"Erro técnico no processamento: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.set_page_config(page_title="Extrator de Obras", layout="wide")
st.title("🏗️ Extrator de Questões (Versão Debug)")

arquivo = st.file_uploader("Suba o arquivo .docx", type=["docx"])

if arquivo:
    with st.spinner('Lendo arquivo...'):
        df = extrair_dados_questoes(arquivo)
        
        if not df.empty:
            # Reordenação de colunas
            colunas = [
                "Enunciado", "Alternativa 1", "Alt 1 Corr.", "Alternativa 2", "Alt 2 Corr.",
                "Alternativa 3", "Alt 3 Corr.", "Alternativa 4", "Alt 4 Corr.", "Alternativa 5", "Alt 5 Corr.",
                "M1 (Banca)", "M2 (Órgão)", "M3 (Cargo)", "M4 (Ano)", "M5 (Disc.)", "M6 (Assunto)"
            ]
            # Filtra apenas colunas que realmente existem no DF para evitar erro
            colunas_existentes = [c for c in colunas if c in df.columns]
            df = df[colunas_existentes]
            
            st.success(f"Concluído! {len(df)} questões prontas.")
            st.dataframe(df)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Baixar CSV", csv, "questoes.csv", "text/csv")
        else:
            st.warning("O arquivo foi lido, mas nenhuma questão foi identificada. Verifique se o padrão do texto no Word é o mesmo dos exemplos.")
