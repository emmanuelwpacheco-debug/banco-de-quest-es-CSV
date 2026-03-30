import streamlit as st
import pandas as pd
from docx import Document
import re

def extrair_dados_questoes(docx_file):
    try:
        doc = Document(docx_file)
        paragrafos = [p.text for p in doc.paragraphs]
        conteudo = "\n".join(paragrafos)
        
        blocos = re.split(r'(?:https?://)?www\.tecconcursos\.com\.br/questoes/\d+', conteudo)
        
        questoes = []
        for bloco in blocos[1:]:
            linhas = [l.strip() for l in bloco.strip().split('\n') if l.strip()]
            if len(linhas) < 5: continue

            # --- METADADOS ---
            meta_topo = linhas[0].split('/')
            banca_cargo = meta_topo[0].split(' - ')
            banca = banca_cargo[0] if len(banca_cargo) > 0 else ""
            cargo = banca_cargo[1] if len(banca_cargo) > 1 else ""
            orgao = meta_topo[1] if len(meta_topo) > 1 else ""
            ano = meta_topo[-1] if len(meta_topo) > 1 else ""
            meta_assunto = linhas[1].split(' - ')
            disciplina = meta_assunto[0] if len(meta_assunto) > 0 else ""
            assunto = meta_assunto[1] if len(meta_assunto) > 1 else ""

            # --- BUSCA DE ÍNDICES ---
            idx_alternativas = []
            idx_gabarito = -1
            categoria = "Múltipla Escolha"
            
            for i, linha in enumerate(linhas):
                l_strip = linha.strip()
                if re.match(r'^[a-h]\)\s+', l_strip.lower()):
                    idx_alternativas.append(i)
                elif l_strip in ["Certo", "Errado"]:
                    idx_alternativas.append(i)
                    categoria = "Certo/Errado"
                if "Gabarito:" in linha:
                    idx_gabarito = i

            if not idx_alternativas or idx_gabarito == -1: continue

            # --- ENUNCIADO E GABARITO ---
            enunciado = "\n".join(linhas[2:idx_alternativas[0]]).strip()
            match_gab = re.search(r'Gabarito:\s*([A-H]|Certo|Errado|C|E)', linhas[idx_gabarito], re.IGNORECASE)
            letra_correta = match_gab.group(1).upper() if match_gab else ""

            # --- ALTERNATIVAS ---
            alts_extraidas = []
            for i in range(len(idx_alternativas)):
                inicio = idx_alternativas[i]
                fim = idx_alternativas[i+1] if i+1 < len(idx_alternativas) else idx_gabarito
                alts_extraidas.append("\n".join(linhas[inicio:fim]).strip())

            # --- MONTAGEM DO DICIONÁRIO (ORDEM RÍGIDA) ---
            row = {
                "Enunciado": enunciado,
                "Categoria": categoria
            }
            
            # Gerar colunas de Alternativa 1 até 8 e suas respectivas correções
            for i in range(1, 9):
                texto_alt = alts_extraidas[i-1] if i <= len(alts_extraidas) else ""
                check = ""
                if texto_alt:
                    letra_alt = texto_alt[0].upper() if ")" in texto_alt[:3] else texto_alt
                    if letra_alt == letra_correta or \
                       (texto_alt == "Certo" and letra_correta in ["C", "CERTO"]) or \
                       (texto_alt == "Errado" and letra_correta in ["E", "ERRADO"]):
                        check = "Sim"
                
                row[f"Alternativa {i}"] = texto_alt
                row[f"Alternativa {i} Correta"] = check

            # Metadados solicitados
            row.update({
                "Metadado 1": "Banca", "Valor 1": banca,
                "Metadado 2": "Órgão", "Valor 2": orgao,
                "Metadado 3": "Cargo", "Valor 3": ano,
                "Metadado 4": "Ano", "Valor 4": disciplina,
                "Metadado 5": "Disciplina", "Valor 5": assunto
            })
            questoes.append(row)
            
        return pd.DataFrame(questoes)
    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame()

# --- Interface ---
st.set_page_config(page_title="Extrator Auditoria", layout="wide")
st.title("🏗️ Extrator de Questões - Formato CSV Padrão")

arquivo = st.file_uploader("Suba o arquivo .docx", type=["docx"])

if arquivo:
    df = extrair_dados_questoes(arquivo)
    if not df.empty:
        # LISTA RÍGIDA DE COLUNAS CONFORME SOLICITADO
        colunas_finais = [
            "Enunciado", "Categoria",
            "Alternativa 1", "Alternativa 1 Correta", "Alternativa 2", "Alternativa 2 Correta",
            "Alternativa 3", "Alternativa 3 Correta", "Alternativa 4", "Alternativa 4 Correta",
            "Alternativa 5", "Alternativa 5 Correta", "Alternativa 6", "Alternativa 6 Correta",
            "Alternativa 7", "Alternativa 7 Correta", "Alternativa 8", "Alternativa 8 Correta",
            "Metadado 1", "Valor 1", "Metadado 2", "Valor 2", "Metadado 3", "Valor 3", 
            "Metadado 4", "Valor 4", "Metadado 5", "Valor 5"
        ]
        
        # Garante que o DataFrame tenha todas as colunas, mesmo que vazias
        for col in colunas_finais:
            if col not in df.columns:
                df[col] = ""
        
        df = df[colunas_finais]
        
        st.success(f"{len(df)} questões processadas!")
        st.dataframe(df)
        
        # Exportação configurada para Excel Brasileiro (sep=";")
        csv = df.to_csv(index=False, sep=";", encoding='utf-8-sig', quoting=1)
        st.download_button("📥 Baixar CSV para Excel", csv, "questoes_auditoria.csv", "text/csv")
