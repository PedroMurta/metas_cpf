import streamlit as st
from tabs import crescimento, fracionamento, base_clientes, diagnostico, proposta, introducao



st.set_page_config(page_title="Proposta de meta de clientes 2027", layout="wide")
st.title("Proposta de meta de clientes atendidos (CPF) — ciclo 2027")
st.caption("Pessoas atendidas por ano (cada CPF conta uma vez por unidade). SEST e SENAT são contados separadamente. "
           "Fonte: SIGOP, 2019 a 2025 e janeiro a setembro de 2026.")

with st.expander("Glossário: o que significa cada termo"):
    st.markdown("""
- **Pessoa atendida (CPF):** cada pessoa conta uma vez por ano em cada unidade, não importa quantas vezes foi atendida.
  Quem foi atendido em duas unidades conta nas duas.
- **Atendimento:** cada registro de serviço (consulta, sessão, aula). Uma pessoa pode ter vários no ano.
- **Atendimentos por pessoa:** atendimentos ÷ pessoas atendidas. Quanto maior, mais vezes, em média, cada pessoa foi atendida.
- **Agenda SEST:** consultas de odontologia, fisioterapia, nutrição e psicologia. São as quatro áreas usadas na meta.
- **Núcleo:** consultas da Agenda SEST e cursos do SENAT, isto é, atendimentos com acompanhamento.
- **Campanha e Turma SEST:** ações pontuais ou em grupo (eventos, atividades coletivas). Ampliam o alcance, mas poucas
  dessas pessoas voltam depois.
- **Novo, retido e reativado:** novo = atendido pela primeira vez; retido = também foi atendido no ano anterior;
  reativado = voltou depois de pelo menos um ano sem vir.
- **Retenção:** % de quem foi atendido em um ano e voltou no ano seguinte.
- **Registro repetido no mesmo dia:** 2º, 3º... atendimento da mesma pessoa, no mesmo dia, unidade e especialidade.
- **Ponto percentual (p.p.):** diferença entre dois percentuais. Passar de 10% para 15% é uma alta de 5 p.p.
- **Meta de atendimentos (pactuada):** a meta de produção já combinada com cada unidade.
- **RAIS:** cadastro oficial dos empregos com carteira assinada. Serve para estimar quantos trabalhadores do transporte
  existem na região de cada unidade (autônomos não entram).
""")



ABAS = {"Introdução": introducao, "Diagnóstico e plano": diagnostico, "Crescimento de clientes": crescimento,
        "Base de clientes": base_clientes, "Proposta": proposta,
        "Registros repetidos (detalhe)": fracionamento}
for aba, modulo in zip(st.tabs(list(ABAS)), ABAS.values()):
    with aba:
        modulo.render()
