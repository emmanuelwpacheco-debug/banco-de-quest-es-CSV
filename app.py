import streamlit as st
import pandas as pd
from docx import Document
import re

def extrair_dados_questoes(docx_file):
    doc = Document(docx_file)
    questoes = []
    paragrafos = [p.text for p in doc.paragraphs]
    conteudo = "\n".join(paragrafos)
    
    # Divisão pelo link (marcador de início de questão)
    blocos = re.split(r'www\.tecconcursos\.com\.br/questoes/\d+', conteudo)
    
    for bloco in blocos[1:]:
        linhas = [l.strip() for l in bloco.strip().split('\n') if l.strip()]
        if len(linhas) < 5: continue

        # --- LINHA 1: Banca - Cargo / Órgão / Nível / Disciplina Original / Ano ---
        # Ex: FGV - Esp Leg (ALERJ)/ALERJ/Nível IV/Administração Geral/2026
        meta_topo = linhas[0].split('/')
        banca_cargo = meta_topo[0].split(' - ')
        
        banca = banca_cargo[0] if len(banca_cargo) > 0 else ""
        cargo = banca_cargo[1] if len(banca_cargo) > 1 else ""
        orgao = meta_topo[1] if len(meta_topo) > 1 else ""
        # O ano costuma ser o último elemento da primeira linha
        ano = meta_topo[-1] if len(meta_topo) > 1 else ""

        # --- LINHA 2: Disciplina (Doutrina) - Assunto ---
        # Ex: Direito Constitucional (CF/1988 e Doutrina) - Mandado de Injunção
        meta_assunto = linhas[1].split(' - ')
        disciplina = meta_assunto[0] if len(meta_assunto) > 0 else ""
        assunto = meta_assunto[1] if len(meta_assunto) > 1 else ""

        # --- IDENTIFICAÇÃO DE GABARITO E ALTERNATIVAS ---
        idx_alternativas = []
        idx_gabarito = -1
        
        for i, linha in enumerate(linhas):
            # Procura a), b) ou Certo/Errado isolados
            if re.match(r'^[a-h]\)\s+', linha.lower()) or linha in ["Certo", "Errado"]:
                idx_alternativas.append(i)
            if "Gabarito:" in linha:
                idx_gabarito = i

        if not idx_alternativas or idx_gabarito == -1: continue

        # --- ENUNCIADO (Tudo entre a linha 2 e a primeira alternativa) ---
        # Preservamos as quebras de linha para listas I, II, III
        enunciado = "\n".join(linhas[2:idx_alternativas[0]])

        # --- GABARITO ---
        linha_gab = linhas[idx_gabarito]
        letra_correta = re.search(r'Gabarito:\s*([A-E]|Certo|Errado|C|E)', linha_gab, re.IGNORECASE)
        letra_correta = letra_correta.group(1).upper() if letra_correta else ""

        # --- ALTERNATIVAS ---
        alts_extraidas = []
        for i in range(len(idx_alternativas)):
            inicio = idx_alternativas[i]
            fim = idx_alternativas[i+1] if i+1 < len(idx_alternativas) else idx_gabarito
            texto_alt = "\n".join(linhas[inicio:fim]).strip()
            alts_extraidas.append(texto_alt)

        # --- MONTAGEM DO DICIONÁRIO NA ORDEM EXATA PEDIDA ---
        row = {"Enunciado": enunciado}
        
        # Preencher 5 Alternativas e 5 Colunas de Correção
        for i in range(1, 6):
            texto_da_alt = alts_extraidas[i-1] if i <= len(alts_extraidas) else ""
            check_correta = ""
            
            if texto_da_alt:
                # Se for múltipla escolha, checa a letra. Se for C/E, checa a palavra.
                letra_da_alt = texto_da_alt[0].upper() if ")" in texto_da_alt[:3] else ""
                
                is_correta = False
                if letra_da_alt == letra_correta: is_correta = True
                if texto_da_alt == "Certo" and letra_correta in ["C", "CERTO"]: is_correta = True
                if texto_da_alt == "Errado" and letra_correta in ["E", "ERRADO"]: is_correta = True
                
                if is_correta:
                    check_correta = "CORRETA" # Ou "Sim", conforme preferir

            row[f"Alternativa {i}"] = texto_da_alt
            row[f"Alt {i} Corr."] = check_correta

        # Metadados finais (M1 a M6)
        row["M1 (Banca)"] = banca
        row["M2 (Órgão)"] = orgao
        row["M3 (Cargo)"] = cargo
        row["M4 (Ano)"] = ano
        row["M5 (Disc.)"] = disciplina
        row["M6 (Assunto)"] = assunto

        questoes.append(row)
    
    return pd.DataFrame(questoes)

# --- Interface Streamlit ---
st.set_page_config(page_title="Extrator Auditoria", layout="wide")
st.title("🏗️ Extrator de Questões Rodoviárias")

arquivo = st.file_uploader("Arraste o arquivo .docx aqui", type=["docx"])

if arquivo:
    df = extrair_dados_questoes(arquivo)
    if not df.empty:
        st.success(f"{len(df)} questões processadas!")
        
        # Reordenar colunas explicitamente para garantir a ordem do usuário
        colunas_ordem = [
            "Enunciado", "Alternativa 1", "Alt 1 Corr.", "Alternativa 2", "Alt 2 Corr.",
            "Alternativa 3", "Alt 3 Corr.", "Alternativa 4", "Alt 4 Corr.", "Alternativa 5", "Alt 5 Corr.",
            "M1 (Banca)", "M2 (Órgão)", "M3 (Cargo)", "M4 (Ano)", "M5 (Disc.)", "M6 (Assunto)"
        ]
        df = df[colunas_ordem]
        
        st.dataframe(df)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Baixar CSV para Excel", csv, "questoes_corrigidas.csv", "text/csv")
