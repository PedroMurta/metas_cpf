"""Diagnóstico e plano: por que pessoas não crescem no ritmo dos atendimentos, sem identificar unidades."""
import pandas as pd
import streamlit as st
from charts.plots import CINZA, CORES_NEGOCIO, fig_barras_anonimas, fig_empilhado_v, fig_linhas_destaque, titulo
from charts.theme import PLOTLY_CONFIG, fmt_number
from data import DADOS, carregar_agenda_ano, carregar_base, carregar_fu, salto_proprio, serie_base
from tabs.base_clientes import _balanco, _conversao

DESTAQUE = CORES_NEGOCIO["SEST"]
CFG = dict(width="stretch", config=PLOTLY_CONFIG)
pct = lambda v, c=1: f"{fmt_number(v, c)}%"
var = lambda v: f"{'+' if v >= 0 else '−'}{fmt_number(abs(v), 0)}%"

PLANO = """
| Frente | Proposta | Por quê |
|---|---|---|
| **Medir o que importa** | Meta de pessoas = **pessoas diferentes atendidas nas quatro áreas de saúde da Agenda SEST** (odontologia, fisioterapia, nutrição e psicologia), por unidade, comparando cada unidade com o próprio histórico (conta na aba **Proposta**). Campanha e Turma SEST passam a ter um indicador próprio, de **contatos** | São as áreas que já têm meta de atendimentos. Contatos rápidos aumentam o alcance no papel, mas poucas dessas pessoas voltam |
| | **Conversão da Campanha** (% de quem passou pela Campanha e foi atendido no Núcleo em até 12 meses) como meta própria | Muita gente entra, pouca fica |
| | Produção contada como **no máximo 1 atendimento por pessoa, por dia, em cada especialidade**, com um indicador à parte para os registros repetidos no mesmo dia | Tira a vantagem de registrar mais, sem prejudicar quem atende corretamente |
| **Abrir agenda para quem é novo** | Vagas reservadas para a primeira consulta, fim dos encaixes curtos em sequência, plano de tratamento com data de alta e lista de espera ativa | Os novos clientes mal repõem os que deixam de vir |
| | Campanha com **encaminhamento**: primeira consulta marcada no próprio evento e contato em até 30 dias | Transforma o contato em atendimento |
| | **Busca ativa** de quem deixou de vir | É a fonte de clientes que mais cresce, e a de menor custo |
| **Acompanhamento e orientação** | Conversa com as unidades em que os registros repetidos aumentaram muito e orientação única de registro para toda a rede | Prática local, que surgiu entre 2022 e 2025 |
"""


def _indice(ag):
    a0, a1 = int(ag.ano.iloc[0]), int(ag.ano.iloc[-1])
    ix = ag.assign(**{"Atendimentos": 100 * ag.atendimentos / ag.atendimentos.iloc[0],
                      "Pessoas (CPFs)": 100 * ag.cpfs / ag.cpfs.iloc[0]})
    g = ix.melt("ano", ["Atendimentos", "Pessoas (CPFs)"], var_name="serie", value_name="v")
    st.plotly_chart(fig_linhas_destaque(g, "ano", "v", "serie", titulo(
        f"Na Agenda SEST, atendimentos {var(ix.Atendimentos.iloc[-1] - 100)} e pessoas "
        f"{var(ix['Pessoas (CPFs)'].iloc[-1] - 100)} entre {a0} e {a1}",
        f"{a0} = 100: cada linha mostra quanto cresceu desde {a0} (150 = 50% a mais). "
        "Pessoas = CPFs diferentes atendidos em cada unidade (regra da meta)."),
        controle="Pessoas (CPFs)"), **CFG)


def _contatos(rt):
    t = rt[rt.recorte == "Total"].pivot(index="ano", columns="visao", values="atendidos").reset_index()
    t["contatos"] = t.Completa - t["Núcleo"]
    share = 100 * t.contatos.iloc[-1] / t.Completa.iloc[-1]
    st.plotly_chart(fig_empilhado_v(t, "ano", [("Núcleo", "Clientes do Núcleo", DESTAQUE),
                                               ("contatos", "Só Campanha ou Turma SEST", CINZA)], titulo(
        f"Em {int(t.ano.iloc[-1])}, {pct(share, 0)} das pessoas alcançadas só tiveram contato por Campanha ou Turma SEST",
        "Pessoas diferentes atendidas na rede por ano. Núcleo = consultas da Agenda SEST e cursos do SENAT.")), **CFG)


def _retencao(rt, bu, desde=2022):
    s = pd.concat([serie_base(rt, bu, v, "Total")[["ano", "retencao"]].assign(serie=v) for v in ["Núcleo", "Completa"]])
    s = s[s.ano >= desde].dropna().rename(columns={"retencao": "v"})
    n, c = (s[s.serie == v].v for v in ("Núcleo", "Completa"))
    rumo = lambda x: ("fica estável" if abs(x.iloc[-1] - x.iloc[0]) < 1 else "sobe" if x.iloc[-1] > x.iloc[0] else "cai")
    s = s.replace({"serie": {"Completa": "Com Campanha e Turma SEST"}})
    st.plotly_chart(fig_linhas_destaque(s, "ano", "v", "serie", titulo(
        f"Contando Campanha e Turma SEST, a retenção {rumo(c)} ({pct(c.iloc[0])} → {pct(c.iloc[-1])}); "
        f"no Núcleo, {rumo(n)} ({pct(n.iloc[0])} → {pct(n.iloc[-1])})",
        f"% de quem foi atendido no ano anterior e voltou no ano. A partir de {desde}: antes, Campanha e Turma SEST "
        "ainda não tinham um ano completo no sistema."), controle="Núcleo", sufixo="%"), **CFG)


def _concentracao(fu, ano):
    d = salto_proprio(fu, ano)
    k, share = int(d.salto.sum()), 100 * d[d.salto].ex_total.sum() / d.ex_total.sum()
    st.plotly_chart(fig_barras_anonimas(d.ex_total.tolist(), [DESTAQUE if s else CINZA for s in d.salto], titulo(
        f"{k} de {len(d)} unidades ({pct(100 * k / len(d), 0)}) passaram a registrar muito mais atendimentos repetidos "
        f"no mesmo dia e respondem por {pct(share, 0)} desses registros em {ano}",
        "Registro repetido = 2º, 3º... atendimento da mesma pessoa no mesmo dia, unidade e especialidade (Agenda SEST). "
        "Em destaque: alta de 5 pontos percentuais ou mais sobre a média da própria unidade em 2019–2021. "
        "Unidades não identificadas."),
        y_title="registros repetidos no mesmo dia"), **CFG)


def render():
    faltam = [n for n in ("retencao", "balanco_unidade", "conversao_campanha", "fr_unidade_ano", "volume_especialidade")
              if not (DADOS / f"{n}.parquet").exists()]
    if faltam:
        st.warning(f"Rode a extração antes: {', '.join(faltam)} (extract.run).")
        return
    rt, bu, cc = carregar_base()
    fu = carregar_fu()
    ano = int(rt.ano.max())
    st.markdown("**Os atendimentos crescem mais rápido que o número de pessoas que se tornam clientes.** Parte do "
                "crescimento vem de registrar mais atendimentos para a mesma pessoa e de contatos rápidos (Campanha e "
                "Turma SEST), que raramente viram acompanhamento. Seis evidências e o plano proposto.")

    a, b = st.columns(2)
    with a:
        _indice(carregar_agenda_ano())
    with b:
        _contatos(rt)
    a, b = st.columns(2)
    with a:
        _retencao(rt, bu)
    with b:
        _conversao(cc, key="dg_conversao")
    a, b = st.columns(2)
    with a:
        _concentracao(fu, ano)
    with b:
        _balanco(serie_base(rt, bu, "Núcleo", "SEST"), key="dg_balanco")

    st.divider()
    st.markdown("### Plano")
    st.markdown(PLANO)