"""Base de clientes: de onde vêm os atendidos de cada ano (novos, retidos, reativados), retenção e conversão da Campanha."""
import streamlit as st
from charts.plots import CINZA, CORES_NEGOCIO, fig_barras_v, fig_cascata, fig_empilhado_v, fig_linhas_destaque, rgba, titulo
from charts.theme import COR_NEUTRA, PLOTLY_CONFIG, fmt_number
from data import DADOS, carregar_base, serie_base

DESTAQUE = CORES_NEGOCIO["SEST"]
CFG = dict(width="stretch", config=PLOTLY_CONFIG)
curto = lambda s: str(s).split(" - ", 1)[-1].strip()
pct = lambda v, c=1: f"{fmt_number(v, c)}%"

COMO_LER = """
**Como ler**

- **Novo:** atendido pela primeira vez (na rede ou, no nível Unidade, naquela unidade). **Retido:** também foi atendido
  no ano anterior. **Reativado:** voltou depois de pelo menos um ano sem atendimento. **Não voltaram:** atendidos no ano
  anterior que não voltaram neste ano.
- **2019 é o ponto de partida:** os dados começam em 2019, então todos os atendidos naquele ano aparecem como "Base de 2019".
- **Núcleo** = consultas da Agenda SEST e cursos do SENAT. **Completa** inclui também Campanha e Turma SEST, que começaram
  a ser registradas em 2020 e por isso aumentam os novos daquele ano. O EaD do SENAT entra em 2023.
- **Retenção** = % de quem foi atendido no ano anterior e voltou. Cada unidade é comparada com ela mesma.
- **Conversão da Campanha:** % de quem teve o primeiro contato pela Campanha e depois foi atendido na Agenda SEST ou no SENAT.
"""


def _composicao(d):
    c = d.copy()
    c["estoque"] = c.novos.where(c.index == 0, 0)
    c.loc[c.index == 0, "novos"] = 0
    u = d.iloc[-1]
    series = [("estoque", "Base de 2019", rgba(COR_NEUTRA, 0.15)), ("retidos", "Retidos", CINZA),
              ("reativados", "Reativados", rgba(DESTAQUE, 0.45)), ("novos", "Novos", DESTAQUE)]
    st.plotly_chart(fig_empilhado_v(c, "ano", series, titulo(
        f"Em {u.ano}, {pct(100 * u.novos / u.atendidos, 0)} dos atendidos eram novos, "
        f"{pct(100 * u.retidos / u.atendidos, 0)} retidos e {pct(100 * u.reativados / u.atendidos, 0)} reativados",
        "Pessoas atendidas no ano, pela origem: primeira vez (novos), já vinham do ano anterior (retidos) "
        "ou voltaram após uma pausa (reativados).")), **CFG)


def _balanco(d, key="bc_balanco"):
    u = d.iloc[-1]
    if d.atend_ant.isna().iloc[-1]:
        return
    a0, a1 = int(u.ano) - 1, int(u.ano)
    cob = 100 * u.novos / u.perdidos if u.perdidos else float("nan")
    saldo = u.atendidos - u.atend_ant
    t = (f"Os novos clientes superam os que não voltaram; o total {'cresce' if saldo >= 0 else 'diminui'} "
         f"{fmt_number(abs(saldo), 0)}"
         if u.novos >= u.perdidos else
         f"Os novos clientes repõem {fmt_number(cob, 0)}% de quem não voltou; o total "
         f"{'cresce graças a quem voltou após uma pausa' if saldo >= 0 else 'diminui'} "
         f"({'+' if saldo >= 0 else '−'}{fmt_number(abs(saldo), 0)})")
    st.plotly_chart(fig_cascata([f"Atendidos {a0}", "Não voltaram", "Novos", "Reativados", f"Atendidos {a1}"],
                                [u.atend_ant, -u.perdidos, u.novos, u.reativados, u.atendidos],
                                ["absolute", "relative", "relative", "relative", "total"],
                                titulo(t, f"Como o total de pessoas mudou de {a0} para {a1}: quem não voltou, quem chegou "
                                          "pela primeira vez e quem voltou após uma pausa.")), key=key, **CFG)


def _retencao(d, rede):
    r = d.dropna(subset=["retencao"])
    if len(r) < 2:
        return
    g = r[["ano", "retencao"]].assign(serie="Retenção geral").rename(columns={"retencao": "v"})
    if rede:
        nv = d[["ano", "retencao_novos_pct"]].dropna().assign(ano=lambda x: x.ano + 1)
        g = g._append(nv.rename(columns={"retencao_novos_pct": "v"}).assign(serie="Retenção dos novos"))
    dif = r.retencao.iloc[-1] - r.retencao.iloc[0]
    t = (f"Retenção de {pct(r.retencao.iloc[-1])} em {int(r.ano.iloc[-1])}: "
         f"{'subiu' if dif >= 0 else 'caiu'} {fmt_number(abs(dif), 1)} pontos percentuais desde {int(r.ano.iloc[0])}")
    st.plotly_chart(fig_linhas_destaque(g, "ano", "v", "serie", titulo(
        t, "% de quem foi atendido no ano anterior e voltou neste ano."
           + (" Retenção dos novos: só quem foi atendido pela primeira vez no ano anterior." if rede else "")),
        controle="Retenção geral", sufixo="%"), **CFG)


def _conversao(cc, key="bc_conversao"):
    c = cc.copy()
    ult = int(c.ano_entrada.max())
    cheios = c[c.ano_entrada < ult]
    cores = [CINZA if a == ult else DESTAQUE for a in c.ano_entrada]
    st.plotly_chart(fig_barras_v(c, "ano_entrada", "pct_conv_12m", cores, titulo(
        f"Só {pct(cheios.pct_conv_12m.iloc[-1])} de quem entra pela Campanha vira cliente em até 12 meses "
        f"({pct(cheios.pct_conv_12m.iloc[0])} em {int(cheios.ano_entrada.iloc[0])})",
        f"% de quem teve o primeiro contato pela Campanha e, em até 12 meses, foi atendido na Agenda SEST ou no SENAT. "
        f"Cerca de {fmt_number(cheios.entraram_campanha.iloc[-1] / 1000, 0)} mil pessoas entram pela Campanha por ano. "
        f"{ult} ainda não completou 12 meses (cinza)."),
        sufixo="%"), key=key, **CFG)


def render():
    faltam = [n for n in ("retencao", "balanco_unidade", "conversao_campanha") if not (DADOS / f"{n}.parquet").exists()]
    if faltam:
        st.warning(f"Rode a extração antes: {', '.join(faltam)} (extract.run).")
        return
    rt, bu, cc = carregar_base()

    c1, c2, c3 = st.columns([1, 1.2, 2])
    nivel = c1.radio("Nível", ["Rede", "Unidade"], horizontal=True, key="bc_nivel")
    rede = nivel == "Rede"
    recorte = c2.radio("Recorte", ["Total", "SEST", "SENAT"] if rede else ["SEST", "SENAT"], horizontal=True, key="bc_rec")
    uid = None
    if rede:
        visao = c3.radio("Visão", ["Núcleo", "Completa"], horizontal=True, key="bc_vis",
                         help="Núcleo: consultas da Agenda SEST e cursos do SENAT. Completa: inclui também Campanha e "
                              "Turma SEST (contatos mais pontuais).")
    else:
        visao = "Núcleo"
        lab = bu[bu.entidade == recorte].drop_duplicates("id_unidade").set_index("id_unidade").unidade.dropna().sort_values()
        uid = c3.selectbox("Unidade", lab.index.tolist(), format_func=lambda i: curto(lab[i]), index=None,
                           placeholder="Digite para buscar", key="bc_unid")
        if uid is None:
            st.info("Escolha uma unidade.")
            return

    d = serie_base(rt, bu, visao, recorte, uid)
    u = d.iloc[-1]
    m = st.columns(4)
    m[0].metric(f"Atendidos {int(u.ano)}", fmt_number(u.atendidos, 0))
    for col, (k, n) in zip(m[1:], [("novos", "Novos"), ("retidos", "Retidos"), ("reativados", "Reativados")]):
        col.metric(n, fmt_number(u[k], 0), pct(100 * u[k] / u.atendidos), delta_color="off")

    a, b = st.columns(2)
    with a:
        _composicao(d)
    with b:
        _balanco(d)
    _retencao(d, rede)
    if rede:
        _conversao(cc)
    st.info(COMO_LER)