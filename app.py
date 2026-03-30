import streamlit as st
import pandas as pd
from docx import Document
import re
import io

# --- FUNÇÃO DE EXTRAÇÃO (O MOTOR) ---
def extrair_dados_questoes(docx_file):
    doc = Document(docx_file)
    questoes = []
    texto_completo = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    conteudo = "\n".join(texto_completo)
    
    # Divide o texto pelos links das questões
    blocos = re.split(r'www\.tecconcursos\.com\.br/questoes/\d+', conteudo)
    
    for bloco in blocos[1:]:
        linhas = [l.strip() for l in bloco.strip().split('\n') if l.strip()]
        if len(linhas) < 4: continue

        # Extração básica de Metadados
        header_info = linhas[0].split('/')
        banca = header_info[0].split(' - ')[0] if header_info else "N/A"
        ano = header_info[2] if len(header_info) > 2 else "N/A"
        
        # Gabarito
        gabarito_match = re.search(r'Gabarito:\s*([A-H]|Certo|Errado|C|E)', bloco, re.IGNORECASE)
        gabarito_letra = gabarito_match.group(1).upper() if gabarito_match else ""

        # Identifica o que é enunciado e o que é alternativa
        enunciado_fim_idx = 0
        alternativas_lista = []
        for i, linha in enumerate(linhas):
            if re.match(r'^[a-h]\)', linha) or linha in ["Certo", "Errado"]:
                if enunciado_fim_idx == 0: enunciado_fim_idx = i
                alternativas_lista.append(linha)

        enunciado = " ".join(linhas[2:enunciado_fim_idx])

        # Monta a linha do CSV
        row = {
            "Enunciado": enunciado,
            "Categoria": "Múltipla Escolha" if len(alternativas_lista) > 2 else "Certo/Errado",
            "Metadado 1": "Banca", "Valor 1": banca,
            "Metadado 4": "Ano", "Valor 4": ano,
        }

        # Preenche as 8 colunas de alternativas solicitadas
        for i in range(1, 9):
            alt_text = alternativas_lista[i-1] if i <= len(alternativas_lista) else ""
            correta = "Não"
            if alt_text:
                letra_atual = alt_text[0].upper()
                if letra_atual == gabarito_letra or (alt_text == "Certo" and gabarito_letra == "C"):
                    correta = "Sim"
            
            row[f"Alternativa {i}"] = alt_text
            row[f"Alternativa {i} Correta"] = correta

        questoes.append(row)
    
    return pd.DataFrame(questoes)

# --- INTERFACE (O SITE) ---
st.set_page_config(page_title="Auditor de Obras - Extrator", layout="wide")
st.title("🏗️ Extrator de Questões Rodoviárias")
st.markdown("Suba seu arquivo Word do Tec Concursos para gerar o CSV.")

arquivo = st.file_uploader("Escolha o arquivo .docx", type=["docx"])

if arquivo:
    with st.spinner('Processando...'):
        df = extrair_dados_questoes(arquivo)
        
        if not df.empty:
            st.success(f"Sucesso! {len(df)} questões extraídas.")
            st.subheader("Prévia dos Dados")
            st.dataframe(df.head())
            
            # Botão de Download
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Baixar arquivo CSV para Excel",
                data=csv,
                file_name="questoes_extraidas.csv",
                mime="text/csv"
            )
        else:
            st.error("Não consegui encontrar questões no padrão esperado. Verifique o arquivo.")
