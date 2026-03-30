import streamlit as st
from seu_arquivo_de_funcoes import extrair_dados_questoes

st.title("Conversor de Questões: Word ➔ CSV")

arquivo = st.file_uploader("Suba o arquivo .docx do Tec Concursos", type=["docx"])

if arquivo:
    df = extrair_dados_questoes(arquivo)
    st.write(f"Encontradas {len(df)} questões.")
    st.dataframe(df.head())
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("Baixar CSV", csv, "questoes_auditadas.csv", "text/csv")
