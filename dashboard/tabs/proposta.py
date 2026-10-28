"""Proposta de meta de pessoas atendidas: cinco perguntas, para a rede ou para uma unidade."""
import pandas as pd
import streamlit as st
from charts.plots import (CINZA, CORES_NEGOCIO, fig_barras_agrupadas, fig_barras_v, fig_comparacao, fig_dispersao,
                          fig_empilhado_100h, rgba, titulo)
from charts.theme import COR_NEUTRA, PLOTLY_CONFIG, fmt_number
from data import (ANT, AREAS, DADOS, FAIXAS_APC, MERC, carregar, carregar_meta, carregar_meta_areas, carregar_proposta, t1_producao_pessoas,
                  t2_intensidade, t3_mercado)

DESTAQUE = CORES_NEGOCIO["SEST"]
TENUE = rgba(COR_NEUTRA, 0.6)
CFG = dict(width="stretch", config=PLOTLY_CONFIG)
ANO_BASE, ANO_META, MES, CAPTURA, PISO = 2025, 2026, 9, 0.25, 0.05
META = DADOS / f"meta_cpf_{ANO_META}.parquet"
curto = lambda s: str(s).split(" - ", 1)[-1].strip()
var = lambda f, c=1: f"{'+' if f >= 0 else '−'}{fmt_number(abs(100 * f), c)}%"
pct = lambda f, c=0: f"{fmt_number(100 * f, c)}%"
num = lambda v: fmt_number(v, 0)
cols = lambda: st.columns([1, 1.6], vertical_alignment="center")      # texto à esquerda, gráfico à direita, alinhados

REGRA = f"""
**Como a meta de pessoas é calculada**

1. **Base:** meta de atendimentos ÷ atendimentos por pessoa da própria unidade em {ANO_BASE}. É o número de pessoas que
   a produção pactuada alcança se nada mudar.
2. **Referência:** em cada área, o nível de atendimentos por pessoa que **1 em cada 4 unidades do mesmo porte** já
   pratica (8 grupos por produção, método de Sturges). Onde a unidade já atende assim, vale o nível dela.
3. **Meta:** base + {pct(CAPTURA)} da distância até o que a referência alcançaria com a mesma produção.
   **Ninguém cresce menos de {pct(PISO)}.**

A meta **não pede mais produção**: pede que a produção pactuada chegue a mais pessoas.
"""

TESTES = {"t1_no_ritmo": "Já no ritmo, sem meta", "t2_capacidade": "A produção já feita basta",
          "t3_historico": "Já cresceu isso antes", "t4_mercado": "Até 10% do mercado livre",
          "t5_campanha": "Até 10% da Campanha"}


def _pergunta(n, texto):
    st.markdown(f"### {n}. {texto}")


def _b1(d, ga, gc, uid, nome):
    _pergunta(1, "O que está acontecendo?")
    e, g = cols()
    if uid is None:
        k = int((d.ga > d.gc).sum())
        e.metric("Atendimentos (jan–set 2026 × jan–set 2025)", var(ga))
        e.metric("Pessoas atendidas", var(gc))
        e.markdown(f"Em **{k} de {len(d)} unidades** a produção cresceu mais que o número de pessoas. Parte do "
                   f"crescimento veio de atender **as mesmas pessoas mais vezes**.")
        a, c, t = ga, gc, f"A produção cresce {var(ga)}; as pessoas atendidas, {var(gc)}"
    else:
        if uid not in d.index:
            e.info(f"{nome}: sem volume suficiente para comparar 2026 com 2025.")
            return
        r = d.loc[uid]
        a, c = r.ga, r.gc
        e.metric("Atendimentos (jan–set 2026)", num(r.at26), var(a))
        e.metric("Pessoas atendidas (jan–set 2026)", num(r.c26), var(c))
        e.markdown(f"Em **{nome}**, " + ("os atendimentos cresceram mais que as pessoas: **cada pessoa recebeu mais "
                                          "atendimentos**." if a > c else
                                          "as pessoas cresceram tanto ou mais que os atendimentos: **a unidade ampliou o alcance**."))
        t = f"{nome}: atendimentos {var(a)}, pessoas {var(c)}"
    g.plotly_chart(fig_comparacao(["Atendimentos", "Pessoas"], [100 * a, 100 * c], [CINZA, DESTAQUE], titulo(
        t, "Agenda SEST (odontologia, fisioterapia, nutrição e psicologia), jan–set 2026 comparado a jan–set 2025.")),
        key="pm_b1", **CFG)


def _b2(cnt, w, uid, nome):
    _pergunta(2, "Por quê? Cada pessoa está sendo atendida mais vezes")
    e, g = cols()
    a0, a1 = w.columns
    if uid is None:
        pc = (cnt["subiu >10%"] / cnt.sum(axis=1)).reindex(AREAS)
        k = pc.idxmax()
        e.metric(f"{k}: unidades em que cada pessoa é atendida mais vezes que em {a0}", f"{round(10 * pc[k])} em cada 10")
        e.markdown(f"Em **{int(cnt.loc[k, 'subiu >10%'])} de {int(cnt.loc[k].sum())} unidades**, cada pessoa recebe hoje "
                   f"mais de 10% mais atendimentos de {k.lower()} que em {a0}. Tratamento longo pode ser necessário; "
                   f"o que chama atenção é o **aumento** dentro da mesma unidade.")
        fig = fig_comparacao(pc.index, 100 * pc.values, [DESTAQUE if i == k else CINZA for i in pc.index], titulo(
            "% das unidades em que cada pessoa passou a ser atendida mais vezes",
            f"Atendimentos por pessoa em {a1} comparados a {a0}, mesma área e unidade (aumento acima de 10%)."),
            sinal=False, casas=0)
    else:
        if uid not in w.index.get_level_values("id_unidade"):
            e.info(f"{nome}: sem volume suficiente em {a0} e {a1} para comparar.")
            return
        u = w.xs(uid, level="id_unidade").reindex(AREAS).dropna()
        dv = u[a1] / u[a0] - 1
        k = dv.idxmax()
        e.metric(f"{k}: atendimentos por pessoa em {a1}", fmt_number(u.loc[k, a1], 1), f"{var(dv[k])} desde {a0}")
        e.markdown(f"Em **{nome}**, cada pessoa recebeu em média **{fmt_number(u.loc[k, a1], 1)}** atendimentos de "
                   f"{k.lower()} em {a1}, contra **{fmt_number(u.loc[k, a0], 1)}** em {a0}.")
        df = u.reset_index().rename(columns={a0: str(a0), a1: str(a1)})
        fig = fig_barras_agrupadas(df, "especialidade", [(str(a0), str(a0), CINZA), (str(a1), str(a1), DESTAQUE)], titulo(
            f"{nome}: atendimentos por pessoa, {a0} × {a1}", "Média de atendimentos que cada pessoa recebeu no ano, por área."),
            sufixo="", sinal=False, height=340)
    g.plotly_chart(fig, key="pm_b2", **CFG)


def _b3(m, uid, nome):
    _pergunta(3, "Tem gente para atender?")
    e, g = cols()
    if uid is None:
        e.metric("Trabalhadores formais do transporte atendidos em 2025", pct(m["nac"]))
        e.markdown(f"São cerca de **{fmt_number(m['tot'] / 1e6, 1)} milhões** de trabalhadores formais no transporte. "
                   f"Em **{int(m['cnt'].iloc[:2].sum())} de {int(m['cnt'].sum())} unidades**, a unidade atendeu no "
                   f"máximo **1 em cada 5** trabalhadores da sua área.")
        df = m["cnt"].rename_axis("faixa").reset_index(name="n")
        fig = fig_barras_v(df, "faixa", "n", [DESTAQUE, DESTAQUE, CINZA, CINZA], titulo(
            "Quantas unidades atendem cada parcela do próprio mercado",
            "Pessoas do transporte atendidas em 2025 ÷ trabalhadores formais do transporte (RAIS 2024) nos municípios "
            "da unidade. Ordem de grandeza: a RAIS não inclui autônomos."), casas=0)
    else:
        if uid not in m["pen"].index:
            e.info(f"{nome}: sem mercado de referência calculado.")
            return
        at, mk = m["atend"][uid], m["mercado"][uid]
        e.metric("Parcela do mercado da unidade atendida em 2025", pct(m["pen"][uid]))
        e.markdown(f"**{nome}** atendeu **{num(at)}** pessoas do transporte em 2025, numa área com cerca de "
                   f"**{num(mk)}** trabalhadores formais do transporte.")
        fig = fig_comparacao(["Atendidos", "Ainda não atendidos"], [at, max(mk - at, 0)], [DESTAQUE, CINZA], titulo(
            f"{nome}: mercado de trabalhadores formais do transporte",
            "RAIS 2024 nos municípios de atuação. Ordem de grandeza: a RAIS não inclui autônomos."),
            sufixo="", sinal=False, casas=0)
    g.plotly_chart(fig, key="pm_b3", **CFG)


def _b4(res, areas, uid, nome):
    _pergunta(4, "O que propomos?")
    st.info(REGRA)
    e, g = cols()
    if uid is None:
        prod = res.meta_at.sum() / (res.cpf0 * res.apc).sum() - 1
        pes = res.meta_cpf.sum() / res.cpf0.sum() - 1
        org = res.origem.value_counts()
        e.metric(f"Meta de pessoas {ANO_META}", num(res.meta_cpf.sum()), var(pes))
        e.metric(f"Meta de atendimentos {ANO_META} (já pactuada)", var(prod))
        pot = (res.cpf0 * res.apc / res.apc_bench - res.cpf0).sum()
        e.markdown(f"Em **{len(res)} unidades**, a meta pede **{num(res.meta_cpf.sum() - res.cpf0.sum())} pessoas a "
                   f"mais** que em {ANO_BASE}. Se cada área atendesse no nível de referência, a produção de {ANO_BASE} "
                   f"já alcançaria **{num(pot)} pessoas a mais** ({var(pot / res.cpf0.sum())}): a meta pede só uma parte "
                   f"desse caminho. Em **{org.get('referência', 0)}** unidades, a meta vem da referência; em "
                   f"**{org.get('mínimo', 0)}**, vale o mínimo de {pct(PISO)}; **{org.get('própria', 0)}** já atendem no "
                   f"nível de referência.")
        fig = fig_comparacao([f"Atendimentos (meta pactuada)", "Pessoas (meta proposta)"], [100 * prod, 100 * pes],
                             [CINZA, DESTAQUE], titulo(
            f"A produção pactuada cresce {var(prod)}; a meta pede {var(pes)} pessoas",
            f"Meta {ANO_META} sobre {ANO_BASE}, odontologia, fisioterapia, nutrição e psicologia."))
    else:
        if uid not in res.index:
            e.info(f"{nome}: sem meta de pessoas (menos de 2 anos, sem histórico próprio ou sem meta de atendimentos).")
            return
        r = res.loc[uid]
        pot = r.meta_at / r.apc_bench
        e.metric(f"Meta de pessoas {ANO_META}", num(r.meta_cpf), var(r.crescimento))
        e.metric("Atendimentos por pessoa: unidade × referência equivalente",
                 f"{fmt_number(r.apc, 1)} × {fmt_number(r.apc_bench, 1)}")
        conta = (f"- **Base:** {num(r.meta_at)} atendimentos ÷ {fmt_number(r.apc, 2)} = **{num(r.base)}** pessoas\n"
                 f"- **Com o nível da referência:** {num(r.meta_at)} ÷ {fmt_number(r.apc_bench, 2)} = **{num(pot)}**\n"
                 f"- **Meta:** {num(r.base)} + {pct(CAPTURA)} × ({num(pot)} − {num(r.base)})")
        nota = {"mínimo": f"A regra daria menos de {pct(PISO)}, então vale o **mínimo de {pct(PISO)}**.",
                "própria": f"{nome} já atende **no nível de referência** em todas as áreas: a meta é a própria base.",
                "referência": f"A meta pede **{pct(CAPTURA)} do caminho** até a referência do porte {r.grupo}."}[r.origem]
        e.markdown(conta + f" → **{num(r.meta_cpf)}**\n\n{nota}")
        fig = fig_comparacao([f"Pessoas {ANO_BASE}", "Base", f"Meta {ANO_META}"], [r.cpf0, r.base, r.meta_cpf],
                             [CINZA, CINZA, DESTAQUE], titulo(
            f"{nome}: de {num(r.cpf0)} para {num(r.meta_cpf)} pessoas ({var(r.crescimento)})",
            f"Pessoas distintas atendidas no ano, 4 áreas. Porte {r.porte}."), sufixo="", sinal=False, casas=0)
    g.plotly_chart(fig, key="pm_b4", **CFG)
    if uid is None:
        t = areas.groupby(["grupo", "especialidade"]).ref.first().unstack().reindex(columns=AREAS).round(1)
        st.caption("Referência: atendimentos por pessoa no ano que 1 em cada 4 unidades do mesmo porte já pratica, por área "
                   "(P25; nacional quando o porte tem menos de 5 unidades com a área). Não é número de sessões a prescrever.")
        st.dataframe(t.rename_axis("Porte").reset_index(), hide_index=True, width="stretch")
    elif uid in res.index:
        a = areas[areas.id_unidade == uid].set_index("especialidade").reindex(AREAS).dropna(subset=["apc"])
        st.caption(f"{nome}: atendimentos por pessoa em {ANO_BASE}, por área, e a referência do porte.")
        st.dataframe(pd.DataFrame({"Área": a.index, "Pessoas": a.cpfs.map(num), "Atend./pessoa": a.apc.round(1),
                                   "Referência": a.ref.round(1),
                                   "Situação": (a.apc > a.ref).map({True: "acima da referência",
                                                                    False: "já no nível de referência"})}),
                     hide_index=True, width="stretch")


def _b5(res, uid, nome, rotulo):
    _pergunta(5, "É possível?")
    e, g = cols()
    if uid is None:
        tx = res[list(TESTES)].mean()
        fact = (res.factiveis >= 3).mean()
        extra = (res.meta_cpf - res.cpf0).sum()
        e.metric("É desafio: unidades que já estariam cumprindo sem meta", pct(tx.t1_no_ritmo))
        e.metric("É possível: passam em 3 ou 4 dos 4 testes de factibilidade", pct(fact))
        e.markdown(f"As **{num(extra)} pessoas a mais** equivalem a **{pct(extra / res.folga.sum(), 1)}** dos "
                   f"trabalhadores do transporte ainda não atendidos, ou a converter **{pct(extra / res.campanha.sum(), 1)}** "
                   f"das pessoas que a Campanha alcançou em {ANO_BASE}.")
        fig = fig_comparacao(list(TESTES.values()), 100 * tx.values, [TENUE] + [DESTAQUE] * 4, titulo(
            f"Desafio para a maioria ({pct(1 - tx.t1_no_ritmo)} ainda não está no ritmo) e possível para {pct(fact)}",
            f"% das unidades que passam em cada teste. Teste 1: jan–set {ANO_META}, com a regra aplicada a {ANO_BASE}."),
            sinal=False, casas=0)
    else:
        if uid not in res.index:
            e.info(f"{nome}: sem meta de pessoas.")
            return
        r = res.loc[uid]
        ok = r.real_jan_set >= r.meta_jan_set
        e.metric("Testes de factibilidade atendidos", f"{int(r.factiveis)} de 4")
        e.metric(f"Produção jan–set {ANO_META} ÷ meta pactuada", pct(r.ritmo_producao))
        e.markdown("\n".join(f"- {'✔' if r[k] else '✘'} {v}" for k, v in TESTES.items()))
        fig = fig_comparacao(["Meta jan–set", "Realizado jan–set"], [r.meta_jan_set, r.real_jan_set],
                             [CINZA, DESTAQUE if ok else TENUE], titulo(
            f"{nome}: {'já no ritmo da meta' if ok else 'abaixo do ritmo da meta'} em setembro",
            f"Pessoas distintas, jan–set {ANO_META}. Meta jan–set = mesma regra aplicada a jan–set {ANO_BASE}."),
            sufixo="", sinal=False, casas=0)
    g.plotly_chart(fig, key="pm_b5", **CFG)
    if uid is None:
        a = res[res.atencao].sort_values("ritmo_producao")
        st.markdown(f"**Atenção ({len(a)} unidades, 0–1 testes):** todas entregam pelo menos "
                    f"**{pct(a.ritmo_producao.min())}** da produção pactuada até setembro. A dificuldade vem de metas de "
                    f"produção que crescem muito, não da regra da meta de pessoas.")
        st.dataframe(pd.DataFrame({"Unidade": rotulo(a), "Pessoas 2025": a.cpf0.map(num), "Meta": a.meta_cpf.map(num),
                                   "Crescimento": a.crescimento.map(var), "Testes": a.factiveis,
                                   "Produção ÷ pactuada": a.ritmo_producao.map(pct)}), hide_index=True, width="stretch")


def _tecnico(d1, intens, cnt, w, res, rotulo):
    with st.expander("Detalhes técnicos"):
        mais = d1.ga > d1.gc
        st.plotly_chart(fig_dispersao(100 * d1.gc, 100 * d1.ga, mais, titulo(
            f"Unidades: variação de pessoas × atendimentos (na rede, {pct(intens)} do crescimento veio de mais atendimentos por pessoa)",
            "Jan–set 2026 vs 2025, unidades com 300+ pessoas. Acima da diagonal, cada pessoa recebeu mais atendimentos."),
            "variação de pessoas", "variação de atendimentos", lim=(-30, 60),
            rotulos=("pessoas cresceram mais", "atendimentos cresceram mais")), key="pm_t1", **CFG)
        pc = cnt.div(cnt.sum(axis=1), axis=0) * 100
        a0, a1 = w.columns
        st.plotly_chart(fig_empilhado_100h(pc, list(zip(FAIXAS_APC, FAIXAS_APC, [TENUE, CINZA, DESTAQUE])), titulo(
            f"Atendimentos por pessoa {a1} ÷ {a0}, por área (% das unidades)", "Mesma unidade e área, 100+ pessoas nos dois anos.")),
            key="pm_t2", **CFG)
        st.markdown("**Meta por unidade**")
        st.dataframe(pd.DataFrame({
            "Unidade": rotulo(res), "Porte": res.porte, "Pessoas 2025": res.cpf0, "Atend./pessoa": res.apc.round(2),
            "Referência": res.apc_bench.round(2), "Meta de atendimentos": res.meta_at, "Base": res.base.round(0),
            "Meta de pessoas": res.meta_cpf, "Crescimento": res.crescimento.map(var), "Origem": res.origem,
            "Testes (de 4)": res.factiveis, "Já no ritmo": res.t1_no_ritmo,
        }).sort_values("Unidade"), hide_index=True, width="stretch")
        st.caption(
            f"Parâmetros: captura {pct(CAPTURA)}, mínimo {pct(PISO)}, grupos de Sturges sobre a produção {ANO_BASE} de todas "
            f"as unidades (G6–G8 com referência comum). Referência por área: P25 dos atendimentos por pessoa das unidades "
            f"elegíveis do porte com 50+ atendimentos na área (P25 nacional se forem menos de 5); a área já abaixo do P25 "
            f"fica com o próprio nível. Ficam sem meta: unidades com menos de 2 anos, "
            f"com a agenda inteira nova ou sem histórico próprio. Testes: (2) a produção jan–set {ANO_META} alcança a meta no "
            f"melhor nível histórico da unidade (2019, 2022, 2023); (3) crescimento pedido ≤ maior crescimento anual "
            f"{ANO_BASE - 2}–{ANO_BASE}; (4) pessoas a mais ≤ 10% do transporte não atendido (RAIS 2024); (5) ≤ 10% das "
            f"pessoas alcançadas pela Campanha {ANO_BASE}.")


def render():
    faltam = [str(f) for f in [DADOS / "agenda_4areas_ytd.parquet", META, ANT / "pessoas_publico.parquet",
                               MERC / "dim_uo_municipio.parquet", MERC / "fato_rais_municipio_totais.parquet"]
              if not f.exists()]
    if faltam:
        st.warning("Arquivos não encontrados:\n\n" + "\n\n".join(faltam))
        return
    p = carregar_proposta(ANO_BASE)
    nomes = carregar()[2].drop_duplicates("id_unidade").set_index("id_unidade").unidade.map(curto)
    res = carregar_meta(ANO_META)
    areas = carregar_meta_areas(ANO_META)

    d1, ga, gc, intens = t1_producao_pessoas(p["ytd"], p["inaug"], ANO_BASE, ANO_META)
    cnt, w = t2_intensidade(p["v"], a0=ANO_BASE - 1, a1=ANO_BASE)        # ano anterior × ano-base
    m3 = t3_mercado(p["uo"], p["rais"], p["pub"], p["inaug"])

    c1, c2, c3 = st.columns([1, 2, 1], vertical_alignment="bottom")
    ver = c1.radio("Ver", ["Rede", "Uma unidade"], horizontal=True, key="pm_ver")
    ocultar = c3.toggle("Ocultar nomes das unidades", value=True, key="pm_ocultar")
    rotulo = lambda d: (d.porte + " · unidade " + pd.Series(range(1, len(d) + 1), index=d.index).astype(str)
                        if ocultar else d.unidade)
    uid, nome = None, "Rede"
    if ver == "Uma unidade":
        opts = sorted(set(d1.index) | set(res.index) | set(m3["pen"].index), key=lambda i: nomes.get(i, ""))
        uid = c2.selectbox("Unidade", opts, format_func=lambda i: nomes.get(i, str(i)), index=None,
                           placeholder="Digite para buscar", key="pm_unid")
        if uid is None:
            st.info("Escolha uma unidade.")
            return
        nome = nomes.get(uid, str(uid))

    _b1(d1, ga, gc, uid, nome)
    _b2(cnt, w, uid, nome)
    _b3(m3, uid, nome)
    _b4(res, areas, uid, nome)
    _b5(res, uid, nome, rotulo)
    st.divider()
    _tecnico(d1, intens, cnt, w, res, rotulo)