"""Introdução: por que a meta de pessoas atendidas é necessária, possível e um desafio — para quem não é técnico."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from charts.plots import CINZA, CORES_NEGOCIO, finalizar, titulo
from charts.theme import PLOTLY_CONFIG
from data import DADOS, carregar_meta, carregar_proposta, t1_producao_pessoas
from tabs.proposta import ANO_BASE, ANO_META, CAPTURA, PISO, num, pct, var

DESTAQUE = CORES_NEGOCIO["SEST"]
ANO_INI = 2022                                             # início da série: depois da pandemia
CFG = dict(width="stretch", config=PLOTLY_CONFIG)


@st.cache_data
def _historico() -> pd.DataFrame:
    """Atendimentos e pessoas da Agenda (4 áreas) por ano, soma das unidades."""
    return pd.read_parquet(DADOS / "agenda_4areas.parquet").groupby("ano")[["atendimentos", "cpfs"]].sum()


dec = lambda v: f"{v:.1f}".replace(".", ",")


def _exemplo(res):
    """Unidade mais próxima das medianas de produção e de atendimentos por pessoa, com meta vinda da referência."""
    r = res[res.origem == "referência"]
    dist = ((r.cpf0 * r.apc).rank(pct=True) - 0.5).abs() + (r.apc.rank(pct=True) - 0.5).abs()
    return r.loc[dist.idxmin()]


def _numero(col, rotulo, valor, texto):
    col.markdown(f"<div style='font-size:0.9rem;opacity:0.7'>{rotulo}</div>"
                 f"<div style='font-size:2.4rem;font-weight:600;line-height:1.15'>{valor}</div>", unsafe_allow_html=True)
    col.caption(texto)


def _fig_historico(h, prod, pes):
    """Atendimentos por pessoa por ano (cinza) e o nível implícito na meta do ano seguinte (destaque)."""
    apc = h.atendimentos / h.cpfs
    apc[ANO_META] = apc[ANO_BASE] * (1 + prod) / (1 + pes)          # meta de atendimentos ÷ meta de pessoas
    br = lambda v: f"{v:.1f}".replace(".", ",")
    rot = [str(a) if a < ANO_META else f"Meta {a}" for a in apc.index]
    fig = go.Figure(go.Bar(x=rot, y=apc.values, marker_color=[CINZA] * (len(apc) - 1) + [DESTAQUE],
                           text=[br(v) for v in apc.values], textposition="outside", cliponaxis=False,
                           hovertemplate="%{x}: %{text} atendimentos por pessoa<extra></extra>"))
    a0, a1 = apc.index[0], ANO_BASE
    fig = finalizar(fig, titulo(
        f"Cada pessoa passou de {br(apc[a0])} para {br(apc[a1])} atendimentos por ano. Com a meta, seriam {br(apc[ANO_META])}",
        f"Atendimentos ÷ pessoas atendidas, Agenda SEST (odontologia, fisioterapia, nutrição e psicologia). "
        f"Desde {a0}, para não misturar com a pandemia."), 400)
    fig.update_xaxes(type="category", showgrid=False)
    fig.update_yaxes(visible=False, range=[0, apc.max() * 1.2])
    return fig


def _fig_escala(extra, folga, camp):
    """Pessoas a mais pedidas pela meta × tamanho das fontes de onde elas podem vir."""
    rot = [f"Pessoas a mais pedidas pela meta", f"Pessoas que a Campanha alcançou em {ANO_BASE}",
           "Trabalhadores do transporte que ainda não atendemos"]
    val = [extra, camp, folga]
    fig = go.Figure(go.Bar(y=rot, x=val, orientation="h", marker_color=[DESTAQUE, CINZA, CINZA],
                           text=[num(v) for v in val], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:,.0f}<extra></extra>"))
    fig = finalizar(fig, titulo(
        f"A meta pede {num(extra)} pessoas: uma fração pequena de quem já está ao nosso alcance",
        "Mercado: trabalhadores formais do transporte (RAIS 2024) nos municípios das unidades, menos os já atendidos."), 300)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(visible=False, range=[0, max(val) * 1.15])
    return fig


def render():
    res = carregar_meta(ANO_META)
    p = carregar_proposta(ANO_BASE)
    _, ga, gc, _ = t1_producao_pessoas(p["ytd"], p["inaug"], ANO_BASE, ANO_META)
    h = _historico().loc[ANO_INI:ANO_BASE]
    pes = res.meta_cpf.sum() / res.cpf0.sum() - 1
    prod = res.meta_at.sum() / (res.cpf0 * res.apc).sum() - 1
    extra = (res.meta_cpf - res.cpf0).sum()
    pot = (res.cpf0 * res.apc / res.apc_bench - res.cpf0).sum()
    a0s, a1s = (f"{h.atendimentos.iloc[k] / h.cpfs.iloc[k]:.1f}".replace(".", ",") for k in (0, -1))

    st.markdown(f"## Meta {ANO_META}: atender mais pessoas com os atendimentos que já estão previstos")
    c1, c2, c3 = st.columns(3)
    _numero(c1, f"Meta de pessoas atendidas em {ANO_META}", num(res.meta_cpf.sum()),
            f"{num(extra)} pessoas a mais que em {ANO_BASE}, somando as {len(res)} unidades.")
    _numero(c2, f"Crescimento de pessoas atendidas", var(pes),
            f"Sobre {ANO_BASE}. Cada unidade tem a sua meta, e todas crescem pelo menos {pct(PISO)}.")
    _numero(c3, "Crescimento de atendimentos já previsto", var(prod),
            "A meta de pessoas não pede atendimentos além dos já previstos.")
    st.markdown(f"""
**Por que essa meta?** Porque, nos últimos anos, os atendimentos cresceram mais rápido que o número de pessoas
atendidas. A meta de pessoas garante que o crescimento chegue a **mais trabalhadores do transporte e às suas
famílias**, e não só às mesmas pessoas, mais vezes.
""")
    st.divider()

    st.markdown("### Por que é necessária: cada pessoa está recebendo mais atendimentos")
    e, g = st.columns([1, 1.6], vertical_alignment="center")
    e.markdown(f"""
Entre {h.index[0]} e {ANO_BASE}, o número médio de atendimentos por pessoa passou de **{a0s}** para **{a1s}**.
Em {ANO_META}, até setembro, os atendimentos cresceram **{var(ga)}**, e as pessoas atendidas, **{var(gc)}**.

Tratamentos que pedem várias sessões são legítimos. O ponto é que parte do crescimento está indo para **as mesmas
pessoas**, e não para quem ainda não conhece o SEST.

Hoje, cumprir a meta de atendimentos atendendo 10 mil ou 12 mil pessoas dá no mesmo. **A meta de pessoas passa a
valorizar quem amplia o alcance.**
""")
    g.plotly_chart(_fig_historico(h, prod, pes), key="in_hist", **CFG)

    st.markdown("### Como funciona: os mesmos atendimentos, chegando a mais gente")
    u = _exemplo(res)
    pot_u = u.meta_at / u.apc_bench
    st.info(f"""
**Exemplo real** (unidade típica da rede, perto da mediana em atendimentos e em atendimentos por pessoa; não identificada)

Em {ANO_BASE}, a unidade fez **{num(u.cpf0 * u.apc)} atendimentos para {num(u.cpf0)} pessoas**, ou seja,
**{dec(u.apc)} por pessoa**. Para {ANO_META}, a meta de atendimentos dela é de **{num(u.meta_at)}**.

- Se continuar com {dec(u.apc)} atendimentos por pessoa, vai atender **{num(u.base)} pessoas**.
- Em cada área, 1 em cada 4 unidades do mesmo porte atende com menos retornos por pessoa. No conjunto das áreas
  dessa unidade, isso equivale a **{dec(u.apc_bench)} por pessoa**, e os mesmos atendimentos chegariam a
  **{num(pot_u)} pessoas**.
- A meta pede só **{pct(CAPTURA)} dessa diferença**: {num(u.base)} + {pct(CAPTURA)} × ({num(pot_u)} − {num(u.base)}) =
  **{num(u.meta_cpf)} pessoas ({var(u.crescimento)})**, com a mesma meta de atendimentos.
""")

    st.markdown("### Por que é possível: há gente para atender e caminhos para chegar até ela")
    e, g = st.columns([1, 1.6], vertical_alignment="center")
    e.markdown(f"""
- **Há margem:** se cada área atendesse no ritmo que 1 em cada 4 unidades do mesmo porte já pratica, os
  atendimentos de {ANO_BASE} alcançariam **{num(pot)} pessoas a mais** ({var(pot / res.cpf0.sum())}). A meta pede
  só uma parte desse caminho.
- **Há público:** as **{num(extra)} pessoas a mais** representam **{pct(extra / res.folga.sum(), 1)}** dos
  trabalhadores do transporte que ainda não atendemos.
- **Há porta de entrada:** bastaria que **1 em cada {round(res.campanha.sum() / extra)}** pessoas que passam pela
  Campanha voltasse para um atendimento.
- **Não pede mais atendimentos:** pede que os já previstos sejam distribuídos entre mais pessoas.
""")
    g.plotly_chart(_fig_escala(extra, res.folga.sum(), res.campanha.sum()), key="in_escala", **CFG)

    st.markdown("### O que muda na prática")
    st.markdown(f"""
Hoje, sem a meta, as pessoas atendidas crescem **{var(gc)}**. A meta pede **{var(pes)}**: um passo a mais, que
depende de três ações já ao alcance das unidades:

1. **Abrir agenda para quem é novo**, sem deixar de cuidar de quem está em tratamento.
2. **Transformar o contato da Campanha em atendimento**, com encaminhamento para a primeira consulta.
3. **Trazer de volta quem deixou de vir.**

A conta da meta de cada unidade está na aba **Proposta**.
""")