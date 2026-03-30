import pandas as pd
from extrator import extrair_dados_questoes
import re
import io

def extrair_dados_questoes(docx_file):
    doc = Document(docx_file)
    questoes = []
    texto_completo = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    # Unir parágrafos para facilitar a busca por blocos
    conteudo = "\n".join(texto_completo)
    
    # Split baseado no link do Tec Concursos (divisor comum das questões)
    blocos = re.split(r'www\.tecconcursos\.com\.br/questoes/\d+', conteudo)
    
    for bloco in blocos[1:]:  # Ignora o que vem antes da primeira questão
        linhas = [l.strip() for l in bloco.strip().split('\n') if l.strip()]
        if len(linhas) < 4: continue

        # --- Extração de Metadados ---
        # Ex: FGV - ATTM (Pref Nova Iguaçu)/Pref Nova Iguaçu/2024
        header_info = linhas[0].split('/')
        banca_orgao = header_info[0].split(' - ')
        
        banca = banca_orgao[0] if len(banca_orgao) > 0 else ""
        orgao = banca_orgao[1] if len(banca_orgao) > 1 else header_info[1] if len(header_info) > 1 else ""
        cargo = header_info[1] if len(header_info) > 1 else ""
        ano = header_info[2] if len(header_info) > 2 else ""
        
        # Disciplina e Assunto (Ex: Direito Administrativo - Desconcentração...)
        desc_info = linhas[1].split(' - ')
        disciplina = desc_info[0]
        assunto = desc_info[1] if len(desc_info) > 1 else ""

        # --- Enunciado e Alternativas ---
        gabarito_match = re.search(r'Gabarito:\s*([A-Ea-e]|Certo|Errado|C|E)', bloco, re.IGNORECASE)
        gabarito_letra = gabarito_match.group(1).upper() if gabarito_match else ""

        # Isolar enunciado (do número da questão até a primeira alternativa)
        # Regex para encontrar a), b), c) ou Certo/Errado
        enunciado_fim_idx = 0
        alternativas_lista = []
        
        for i, linha in enumerate(linhas):
            if re.match(r'^[a-h]\)', linha) or linha in ["Certo", "Errado"]:
                if enunciado_fim_idx == 0: enunciado_fim_idx = i
                alternativas_lista.append(linha)

        enunciado = " ".join(linhas[2:enunciado_fim_idx])

        # --- Montagem do Dicionário (Formato CSV) ---
        row = {
            "Enunciado": enunciado,
            "Categoria": "Múltipla Escolha" if len(alternativas_lista) > 2 else "Certo/Errado",
            "Metadado 1": banca, "Valor 1": banca,
            "Metadado 2": orgao, "Valor 2": orgao,
            "Metadado 3": cargo, "Valor 3": cargo,
            "Metadado 4": ano, "Valor 4": ano,
            "Metadado 5": disciplina, "Valor 5": disciplina,
            "Metadado 6": assunto
        }

        # Preencher Alternativas (até 8 colunas conforme solicitado)
        for i in range(1, 9):
            alt_text = ""
            correta = "Não"
            if i <= len(alternativas_lista):
                alt_text = alternativas_lista[i-1]
                # Verifica se a alternativa atual é a correta
                letra_atual = alt_text[0].upper()
                if letra_atual == gabarito_letra or (alt_text == "Certo" and gabarito_letra == "C") or (alt_text == "Errado" and gabarito_letra == "E"):
                    correta = "Sim"
            
            row[f"Alternativa {i}"] = alt_text
            row[f"Alternativa {i} Correta"] = correta

        questoes.append(row)
    
    return pd.DataFrame(questoes)
