import streamlit as st
import pandas as pd
from docx import Document
import re
import io

def extrair_dados_questoes(docx_file):
    try:
        doc = Document(docx_file)
        paragrafos = [p.text for p in doc.paragraphs]
        conteudo = "\n".join(paragrafos)
        
        # Divisão por link do TecConcursos
        blocos = re.split(r'(?:https?://)?www\.tecconcursos\.com\.br/questoes/\d+', conteudo)
        
        questoes = []
        for bloco in blocos[1:]:
            linhas = [l.strip() for l in bloco.strip().split('\n') if l.strip()]
            if len(linhas) < 5: continue

            # --- METADADOS (M1 a M6) ---
            # FGV - Esp Leg (ALERJ)/ALERJ/Nível IV/Administração Geral/2026
            meta_topo = linhas[0].split('/')
            banca_cargo = meta_topo[0].split(' - ')
            banca = banca_cargo[0] if len(banca_cargo) > 0 else ""
            cargo = banca_cargo[1] if len(banca_cargo) > 1 else ""
            orgao = meta_topo[1] if len(meta_topo) > 1 else ""
            ano = meta_topo[-1] if len(meta_topo) > 1 else ""

            # Direito Constitucional - Mandado de Injunção
            meta_assunto = linhas[1].split(' - ')
            disciplina = meta_assunto[0] if len(meta_assunto) > 0 else ""
            assunto = meta_assunto[1] if len(meta_assunto) > 1 else ""

            # --- BUSCA DE ÍNDICES ---
            idx_alternativas = []
            idx_gabarito = -1
            
            for i, linha in enumerate(linhas):
                l_strip = linha.strip()
                # Detecta a), b) ou Certo/Errado isolados
                if re.match(r'^[a-h]\)\s+', l_strip.lower()) or l_strip in ["Certo", "Errado"]:
                    idx_alternativas.append(i)
                if "Gabarito:" in linha:
                    idx_gabarito = i

            if not idx_alternativas or idx_gabarito == -1: continue

            # --- ENUNCIADO ---
            # Pega tudo entre as linhas de metadados e a primeira alternativa
            # Mantemos as quebras de linha reais
            enunciado = "\n".join(linhas[2:idx_alternativas[0]]).strip()

            # --- GABARITO ---
            match_gab = re.search(r'Gabarito:\s*([A-E]|Certo|Errado|C|E)', linhas[idx_gabarito], re.IGNORECASE)
            letra_correta = match_gab.group(1).upper() if match_gab else ""

            # --- ALTERNATIVAS ---
            alts_extraidas = []
            for i in range(len(idx_alternativas)):
                inicio = idx_alternativas[i]
                fim = idx_alternativas[i+1] if i+1 < len(idx_alternativas) else idx_gabarito
                alts_extraidas.append("\n".join(linhas[inicio:fim]).strip())

            # --- MONTAGEM DA LINHA ---
            row = {"Enunciado": enunciado}
            
            for i in range(1, 6):
                texto_alt = alts_extraidas[i-1] if i <= len(alts_extraidas) else ""
                check = ""
                if texto_alt:
                    # Identifica se a alternativa é a correta
                    letra_alt = texto_alt[0].upper() if ")" in texto_alt[:3] else texto_alt
                    if letra_alt == letra_correta or \
                       (texto_alt == "Certo" and letra_correta in ["C", "CERTO"]) or \
                       (texto_alt == "Errado" and letra_correta in ["E", "ERRADO"]):
                        check = "CORRETA"
                
                row[f"Alternativa {i}"] = texto_alt
                row[f"Alt {i} Corr."] = check

            row.update({
                "M1 (Banca)": banca, "M2 (Órgão)": orgao, "M3 (Cargo)": cargo,
                "M4 (Ano)": ano, "M5 (Disc.)": disciplina, "M6 (Assunto)": assunto
            })
            questoes.append(row)
            
        return pd.DataFrame(questoes)
    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame()

# --- Interface ---
st.title("🏗️ Extrator CSV - Correção de Colunas")

arquivo = st.file_uploader("Suba o .docx", type=["docx"])

if arquivo:
    df = extrair_dados_questoes(arquivo)
    if not df.empty:
        colunas_ordem = [
            "Enunciado", "Alternativa 1", "Alt 1 Corr.", "Alternativa 2", "Alt 2 Corr.",
            "Alternativa 3", "Alt 3 Corr.", "Alternativa 4", "Alt 4 Corr.", "Alternativa 5", "Alt 5 Corr.",
            "M1 (Banca)", "M2 (Órgão)", "M3 (Cargo)", "M4 (Ano)", "M5 (Disc.)", "M6 (Assunto)"
        ]
        df = df[colunas_ordem]
        
        st.dataframe(df)
        
        # --- SOLUÇÃO PARA O EXCEL ---
        # Usamos sep=";" e encoding="utf-8-sig" para o Excel reconhecer as colunas e os acentos
        csv = df.to_csv(index=False, sep=";", encoding='utf-8-sig', quoting=1) # quoting=1 coloca aspas em tudo
        
        st.download_button("📥 Baixar CSV para Excel", csv, "questoes_corretas.csv", "text/csv")
