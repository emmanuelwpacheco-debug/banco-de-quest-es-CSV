import streamlit as st
import pandas as pd
from docx import Document
import re
import io

def extrair_dados_questoes(docx_file):
    doc = Document(docx_file)
    questoes = []
    
    # Pegamos todos os parágrafos, mantendo o texto bruto
    paragrafos = [p.text for p in doc.paragraphs]
    conteudo = "\n".join(paragrafos)
    
    # Divisão por link do Tec (divisor de questões)
    blocos = re.split(r'www\.tecconcursos\.com\.br/questoes/\d+', conteudo)
    
    for bloco in blocos[1:]:
        linhas = [l.rstrip() for l in bloco.strip().split('\n')]
        if len(linhas) < 4: continue

        # --- Metadados ---
        header = linhas[0].split('/')
        banca = header[0].split(' - ')[0] if len(header) > 0 else ""
        orgao = header[1] if len(header) > 1 else ""
        cargo = header[1] if len(header) > 1 else "" # Ajuste conforme sua necessidade
        ano = header[2] if len(header) > 2 else ""
        
        desc_line = linhas[1].split(' - ')
        disciplina = desc_line[0] if len(desc_line) > 0 else ""
        assunto = desc_line[1] if len(desc_line) > 1 else ""

        # --- Localização de Gabarito e Alternativas ---
        # Encontramos onde começam as alternativas e onde está o gabarito
        idx_alternativas = []
        idx_gabarito = -1
        
        for i, linha in enumerate(linhas):
            # Procura a), b), Certo, Errado no início da linha
            if re.match(r'^[a-h]\)\s+', linha.strip().lower()) or linha.strip() in ["Certo", "Errado"]:
                idx_alternativas.append(i)
            if "Gabarito:" in linha:
                idx_gabarito = i

        if not idx_alternativas: continue

        # --- Enunciado ---
        # O enunciado começa na linha 2 (após o cabeçalho) e vai até a primeira alternativa
        enunciado_raw = linhas[2:idx_alternativas[0]]
        enunciado = "\n".join(enunciado_raw).strip()

        # --- Gabarito ---
        txt_gabarito = linhas[idx_gabarito] if idx_gabarito != -1 else ""
        letra_correta = re.search(r'Gabarito:\s*([A-H]|Certo|Errado|C|E)', txt_gabarito, re.IGNORECASE)
        letra_correta = letra_correta.group(1).upper() if letra_correta else ""

        # --- Alternativas ---
        alts_extraidas = []
        for i in range(len(idx_alternativas)):
            inicio = idx_alternativas[i]
            # O fim de uma alternativa é o início da próxima ou o gabarito
            fim = idx_alternativas[i+1] if i+1 < len(idx_alternativas) else idx_gabarito
            
            texto_alt = "\n".join(linhas[inicio:fim]).strip()
            alts_extraidas.append(texto_alt)

        # --- Montagem da Linha ---
        row = {
            "Enunciado": enunciado,
            "Categoria": "Múltipla Escolha" if len(alts_extraidas) > 2 else "Certo/Errado",
            "Metadado 1": "Banca", "Valor 1": banca,
            "Metadado 2": "Órgão", "Valor 2": orgao,
            "Metadado 3": "Cargo", "Valor 3": cargo,
            "Metadado 4": "Ano", "Valor 4": ano,
            "Metadado 5": "Disciplina", "Valor 5": disciplina,
            "Metadado 6": "Assunto", "Valor 6": assunto
        }

        # Preenche até 8 colunas de alternativas
        for i in range(1, 9):
            alt_completa = alts_extraidas[i-1] if i <= len(alts_extraidas) else ""
            correta = "Não"
            
            if alt_completa:
                # Lógica para marcar correta (se a letra bater ou se for C/E)
                letra_da_alt = alt_completa[0].upper() if ")" in alt_completa[:3] else alt_completa[0]
                if letra_da_alt == letra_correta or \
                   (alt_completa == "Certo" and letra_correta == "C") or \
                   (alt_completa == "Errado" and letra_correta == "E"):
                    correta = "Sim"
            
            row[f"Alternativa {i}"] = alt_completa
            row[f"Alternativa {i} Correta"] = correta

        questoes.append(row)
    
    return pd.DataFrame(questoes)

# --- Streamlit UI (Igual ao anterior) ---
st.set_page_config(page_title="Extrator Auditoria", layout="wide")
st.title("🏗️ Extrator de Questões (Versão Completa)")

arquivo = st.file_uploader("Suba o .docx", type=["docx"])

if arquivo:
    df = extrair_dados_questoes(arquivo)
    if not df.empty:
        st.success(f"Processadas {len(df)} questões!")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Baixar CSV", csv, "questoes.csv", "text/csv")
