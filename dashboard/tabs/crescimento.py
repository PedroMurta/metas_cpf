import numpy as np
import pandas as pd
import streamlit as st
from charts.plots import CORES_NEGOCIO, fig_evolucao, fig_variacao, titulo
from charts.theme import PLOTLY_CONFIG, fmt_number
from data import PESSOA_UNICA, REGRA_META, carregar, cpfs, recorte, tabela_crescimento

CHOQUES = {"Turma SEST": "Turma SEST entra no SIGOP em 2020", "À Distância Livre": "EaD entra no SIGOP em 2023",
           "Campanha": "Campanha entra no SIGOP em ago/2020"}

COMO_LER = """
**Como ler estes números**

- **Por unidade (regra da meta, padrão):** cada pessoa conta 1 vez por unidade e por ano. Quem foi atendido em duas
  unidades conta 2 vezes no total.
- **Pessoa única:** cada pessoa conta 1 vez no Brasil (ou no conselho), mesmo que tenha ido a várias unidades.
  Para uma unidade só, as duas contagens dão o mesmo número.
- **O total não é a soma das especialidades:** quem usou odontologia **e** fisioterapia conta 1 vez, mesmo com as duas
  marcadas.
- **Mudanças no sistema:** Turma SEST e Campanha passaram a ser registradas no SIGOP em 2020, e o EaD do SENAT em 2023.
  O salto nesses anos vem do início do registro, não de mais procura. Desmarque esses itens para comparar com 2019.
"""

pct = lambda v: f"{'+' if v >= 0 else ''}{fmt_number(v, 1)}%"


def _bloco(ent: str, base: pd.DataFrame, cat: pd.DataFrame, a0: int, a1: int) -> tuple[pd.Series | None, dict]:
    """Filtro de especialidades + gráfico de evolução de uma entidade. Devolve a série e as séries por especialidade."""
    c = cat[cat.entidade == ent]
    todas = sorted(c.especialidade.unique())
    esp = st.pills(f"Especialidades {ent}", todas, selection_mode="multi", default=todas, key=f"esp_{ent}")
    mods = sorted(c.modalidade.unique())
    if len(mods) > 1:
        mods = st.pills(f"Modalidade {ent}", mods, selection_mode="multi", default=mods, key=f"mod_{ent}")
    itens = c[c.especialidade.isin(esp) & c.modalidade.isin(mods)]
    if itens.empty:
        st.warning("Selecione ao menos uma especialidade e uma modalidade.")
        return None, {}

    b = base[base.entidade == ent]
    serie = lambda g: cpfs(b, int(np.bitwise_or.reduce(g.bit.to_numpy()))).loc[a0:a1]
    s = serie(itens)
    if len(s) < 2:
        st.info(f"Sem dados de {ent} suficientes no período.")
        return None, {}

    notas = [v for k, v in CHOQUES.items() if k in {ent, *itens.especialidade, *itens.modalidade}]
    sub = (f"Pessoas diferentes atendidas no ano; os percentuais mostram a variação sobre o ano anterior. "
           f"{itens.especialidade.nunique()} de {len(todas)} especialidades" + "".join(f". {n}" for n in notas) + ".")
    st.plotly_chart(fig_evolucao(s.rename_axis("ano").reset_index(name="cpfs"), "ano", "cpfs", CORES_NEGOCIO[ent],
                                 titulo(f"{ent}: {pct(100 * (s.iloc[-1] / s.iloc[0] - 1))} entre {s.index[0]} e {s.index[-1]}", sub)),
                    width="stretch", config=PLOTLY_CONFIG)
    return s, {f"{ent} · {e}": serie(g) for e, g in itens.groupby("especialidade")}


def render():
    p, cat, unid = carregar()
    anos = sorted(p.ano.unique())

    c1, c2, c3 = st.columns([1.1, 1.6, 2])
    nivel = c1.radio("Nível", ["Nacional", "Conselho", "Unidade"], horizontal=True)
    regra = c2.radio("Contagem", [REGRA_META, PESSOA_UNICA], horizontal=True, disabled=nivel == "Unidade")
    nome = None
    if nivel == "Conselho":
        nome = c3.selectbox("Conselho", sorted(unid.conselho.unique()))
    elif nivel == "Unidade":
        nome = c3.selectbox("Unidade", sorted(unid.unidade.unique()), index=None, placeholder="Digite para buscar")
        if not nome:
            st.info("Escolha uma unidade para ver a evolução.")
            return
    a0, a1 = st.select_slider("Período", options=anos, value=(anos[0], anos[-1]))
    if a0 == a1:
        st.warning("Escolha um período com pelo menos dois anos.")
        return

    base = recorte(p, unid, nivel, nome, regra)
    series, por_esp = {}, {}
    for col, ent in zip(st.columns(2), ["SENAT", "SEST"]):
        with col:
            s, e = _bloco(ent, base, cat, a0, a1)
            if s is not None:
                series[ent], por_esp = s, por_esp | e
    with st.expander("Campanha (categoria separada, fora da meta)"):
        s, e = _bloco("Campanha", base, cat, a0, a1)
        if s is not None:
            series["Campanha"], por_esp = s, por_esp | e

    if series:
        dist = pd.DataFrame(series).T
        st.dataframe(tabela_crescimento(dist), width="stretch", hide_index=True,
                     column_config={str(a): st.column_config.NumberColumn(format="localized") for a in dist.columns})

    if por_esp:
        dist = pd.DataFrame(por_esp).T.dropna(how="all")
        ult = dist.iloc[:, -1] / dist.iloc[:, -2] - 1
        neg = ult[ult < 0].sort_values()
        achado = (f"Em {dist.columns[-1]}, {len(neg)} especialidade(s) perderam pessoas atendidas: "
                  + ", ".join(f"{i} ({pct(100 * v)})" for i, v in neg.items())) if len(neg) else \
                 f"Em {dist.columns[-1]}, todas as especialidades selecionadas ganharam pessoas atendidas"
        st.plotly_chart(fig_variacao(dist, titulo(achado, "Variação de pessoas atendidas sobre o ano anterior, em cada "
                                                          "especialidade. Cores mais fortes = variações maiores (escala até ±50%).")),
                        width="stretch", config=PLOTLY_CONFIG)
        with st.expander("Tabela por especialidade"):
            st.dataframe(tabela_crescimento(dist, "Especialidade"), width="stretch", hide_index=True,
                         column_config={str(a): st.column_config.NumberColumn(format="localized") for a in dist.columns})

    st.info(COMO_LER)
