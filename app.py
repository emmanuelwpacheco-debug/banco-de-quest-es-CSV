import streamlit as st
import pandas as pd
from docx import Document
import re

def extrair_dados_questoes(docx_file):
    try:
        doc = Document(docx_file)
        # Lemos todos os parágrafos ignorando os vazios
        paragrafos = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        conteudo = "\n".join(paragrafos)
        
        # --- DIVISÃO DAS QUESTÕES ---
        # Tenta dividir pelo link do Tec (com ou sem http) OU por números seguidos de parênteses no início da linha
        # Ex: 13), 22), etc.
        blocos = re.split(r'(?:https?://)?www\.tecconcursos\.com\.br/questoes/\d+|(?:\n|^)\d+\)\s', conteudo)
        
        # Se a divisão não funcionou, tenta dividir apenas pelo "Gabarito:" como última alternativa
        if len(blocos) <= 1:
            blocos = re.split(r'(?<=Gabarito: [A-E])\n', conteudo)

        questoes = []
        for bloco in blocos:
            linhas = [l.strip() for l in bloco.strip().split('\n') if l.strip()]
            if len(linhas) < 4: continue

            # --- BUSCA DE GABARITO E ALTERNATIVAS (O CORAÇÃO DO PROBLEMA) ---
            idx_alternativas = []
            idx_gabarito = -1
            
            for i, linha in enumerate(linhas):
                l_lower = linha.lower()
                # Padrão: a) ou Certo/Errado no início da linha
                if re.match(r'^[a-h]\)\s+', l_lower) or l_lower in ["certo", "errado"]:
                    idx_alternativas.append(i)
                if "gabarito:" in l_lower:
                    idx_gabarito = i

            # Só processa se achar o gabarito
            if idx_gabarito == -1: continue

            # Se não achou alternativas (ex: questão mal formatada), tenta extrair o que der
            primeira_alt = idx_alternativas[0] if idx_alternativas else idx_gabarito

            # --- METADADOS ---
            # Tentamos pegar banca e ano das duas primeiras linhas
            meta_linha = linhas[0] if len(linhas) > 0 else ""
            ano_match = re.search(r'20\d{2}', meta_linha)
            ano = ano_match.group(0) if ano_match else ""
            
            banca = meta_linha.split('-')[0].strip() if '-' in meta_linha else meta_linha[:15]

            # --- ENUNCIADO ---
            # O enunciado agora é tudo antes da primeira alternativa ou do Gabarito
            enunciado = "\n".join(linhas[:primeira_alt])
            # Remove as linhas de metadados do topo do enunciado (se sobrarem)
            enunciado_limpo = "\n".join(enunciado.split('\n')[2:]).strip()

            # --- GABARITO ---
            match_gab = re.search(r'Gabarito:\s*([A-E]|Certo|Errado|C|E)', linhas[idx_gabarito], re.IGNORECASE)
            letra_correta = match_gab.group(1).upper() if match_gab else ""

            # --- ALTERNATIVAS ---
            alts_extraidas = []
            if idx_alternativas:
                for i in range(len(idx_alternativas)):
                    inicio = idx_alternativas[i]
                    fim = idx_alternativas[i+1] if i+1 < len(idx_alternativas) else idx_gabarito
                    alts_extraidas.append("\n".join(linhas[inicio:fim]).strip())

            # --- MONTAGEM NA ORDEM SOLICITADA ---
            row = {"Enunciado": enunciado_limpo if enunciado_limpo else enunciado}
            
            for i in range(1, 6):
                texto_alt = alts_extraidas[i-1] if i <= len(alts_extraidas) else ""
                corr = ""
                if texto_alt:
                    letra_alt = texto_alt[0].upper() if ")" in texto_alt[:3] else texto_alt
                    if letra_alt == letra_correta or \
                       (texto_alt == "Certo" and letra_correta in ["C", "CERTO"]) or \
                       (texto_alt == "Errado" and letra_correta in ["E", "ERRADO"]):
                        corr = "CORRETA"
                row[f"Alternativa {i}"] = texto_alt
                row[f"Alt {i} Corr."] = corr

            row.update({
                "M1 (Banca)": banca, "M2 (Órgão)": "", "M3 (Cargo)": "",
                "M4 (Ano)": ano, "M5 (Disc.)": "", "M6 (Assunto)": ""
            })
            questoes.append(row)
            
        return pd.DataFrame(questoes)

    except Exception as e:
        st.error(f"Erro: {e}")
        return pd.DataFrame()

# Interface simplificada
st.title("🏗️ Extrator Flexível de Questões")
arquivo = st.file_uploader("Suba o .docx", type=["docx"])

if arquivo:
    df = extrair_dados_questoes(arquivo)
    if not df.empty:
        # Garante a ordem exata das colunas
        ordem = ["Enunciado", "Alternativa 1", "Alt 1 Corr.", "Alternativa 2", "Alt 2 Corr.", 
                 "Alternativa 3", "Alt 3 Corr.", "Alternativa 4", "Alt 4 Corr.", "Alternativa 5", "Alt 5 Corr.",
                 "M1 (Banca)", "M2 (Órgão)", "M3 (Cargo)", "M4 (Ano)", "M5 (Disc.)", "M6 (Assunto)"]
        df = df.reindex(columns=ordem)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Baixar CSV", csv, "questoes.csv", "text/csv")
    else:
        st.warning("Nenhuma questão processada. O Gabarito está escrito como 'Gabarito: X'?")
        
