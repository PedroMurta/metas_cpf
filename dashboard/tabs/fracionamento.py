"""Fracionamento na Agenda SEST: registros além do 1º do cliente no mesmo dia, unidade e especialidade."""
import pandas as pd
import streamlit as st
from charts.plots import CINZA, CORES_NEGOCIO, fig_barras_h, fig_linhas_destaque, titulo
from charts.theme import COR_NEUTRA, PLOTLY_CONFIG, fmt_number
from data import DADOS, PADROES, carregar_fr, classificar, perfil_prof, por_unidade, serie_unidade

DESTAQUE = CORES_NEGOCIO["SEST"]
CFG = dict(width="stretch", config=PLOTLY_CONFIG)
curto = lambda s: str(s).split(" - ", 1)[-1].strip()
pct = lambda v, c=1: f"{fmt_number(v, c)}%"
pp = lambda v: f"{'+' if v >= 0 else ''}{fmt_number(v, 1)} p.p."
cores = lambda vals, lim: [DESTAQUE if v > lim else CINZA for v in vals]

COMO_LER = """
**Como ler**

- **Registro repetido no mesmo dia:** o 2º, 3º... atendimento da mesma pessoa, na mesma unidade e especialidade, no mesmo dia.
- **Cada unidade (e cada profissional) é comparada com ela mesma** no ano de comparação, não com a rede.
  Em **cor**: alta acima do mínimo escolhido (em pontos percentuais). Em cinza: sem alta relevante.
- Se a alta aparece na **equipe toda**, indica uma regra da gestão local; se aparece em **alguns profissionais**, uma
  prática individual.
- Unidades ou profissionais sem volume suficiente no ano de comparação ficam de fora.
- O SIGOP não registra o procedimento feito: parte dos registros repetidos pode ser legítima (por exemplo, avaliação +
  procedimento). A meta de **pessoas** não é afetada por esses registros; a meta de **atendimentos** é.
- Com **"Ocultar nomes"** ligado, as unidades aparecem numeradas pela ordem do ranking do recorte escolhido.
"""

INTRO = """
**O que esta aba mostra:** quando a mesma pessoa tem dois ou mais atendimentos registrados no mesmo dia, na mesma
especialidade, cada registro conta para a meta de atendimentos. Isso pode ser legítimo, mas, quando cresce muito em uma
unidade, costuma indicar mudança na forma de registrar. Aqui se vê onde esses registros aumentaram, comparando cada
unidade com ela mesma.
"""


def _ranking(u, esp, ano, ref, alta):
    h = u.dropna(subset=["d_ex_total"])
    n, sem = int((h.d_ex_total > alta).sum()), len(u) - len(h)
    top = h.head(20).assign(rot=lambda d: d.unidade.map(curto))
    st.plotly_chart(fig_barras_h(top, "d_ex_total", "rot", cores(top.d_ex_total, alta), titulo(
        f"{n} de {len(h)} unidades aumentaram em mais de {fmt_number(alta, 1)} pontos percentuais os registros repetidos "
        f"no mesmo dia, em relação a {ref}",
        f"Quanto mudou, de {ref} para {ano}, a parcela dos atendimentos de {esp.lower()} que são registros repetidos no "
        f"mesmo dia. Cada unidade comparada com ela mesma. 20 maiores altas." + (f" {sem} sem volume em {ref}." if sem else "")),
        ref=alta, ref_txt=f"+{fmt_number(alta, 1)} p.p.", sufixo=" p.p.", sinal=True), **CFG)


def _evolucao(fu, esp, uid, nome, ano, ref):
    s = serie_unidade(fu, esp, uid).assign(grupo=nome)
    v = s.set_index("ano").pct
    v0, v1 = v.get(ref), v.get(ano)
    t = (f"{nome}: {pct(v0)} em {ref} → {pct(v1)} em {ano} ({pp(v1 - v0)})" if pd.notna(v0) and pd.notna(v1)
         else f"{nome}: sem dado em {ref} para comparar")
    fig = fig_linhas_destaque(s, "ano", "pct", "grupo", titulo(
        t, f"% dos atendimentos que são registros repetidos no mesmo dia, por ano. Linha pontilhada: nível da própria "
           f"unidade em {ref}."), sufixo="%")
    if pd.notna(v0):
        fig.add_hline(y=v0, line_dash="dot", line_color=COR_NEUTRA)
    st.plotly_chart(fig, **CFG)


def _profissionais(prof, uid, ano, ref, alta, corte):
    p = (prof[prof.id_unidade == uid].sort_values("d_dia_mult", ascending=False)
         .assign(rot=lambda d: "Prof. " + d.id_prof.astype(str)))
    h = p.dropna(subset=["d_dia_mult"])
    if h.empty:
        st.info(f"Nenhum profissional desta unidade tem volume em {ano} e em {ref} para comparar.")
        return p
    k, novos = int((h.d_dia_mult > alta).sum()), len(p) - len(h)
    leitura = ("equipe toda" if 100 * k / len(h) >= corte else
               "alguns profissionais" if k else "sem alta")
    st.plotly_chart(fig_barras_h(h, "d_dia_mult", "rot", cores(h.d_dia_mult, alta), titulo(
        f"{k} de {len(h)} profissionais aumentaram em mais de {fmt_number(alta, 1)} pontos percentuais em relação a "
        f"{ref}: {leitura}",
        f"Quanto mudou, de {ref} para {ano}, a parcela dos atendimentos do profissional feitos em dias com 2 ou mais "
        f"registros da mesma pessoa." + (f" {novos} sem volume em {ref}." if novos else "")),
        ref=alta, ref_txt=f"+{fmt_number(alta, 1)} p.p.", sufixo=" p.p.", sinal=True), **CFG)
    return p


def _detalhes(u, prof, p, fc, esp, ano, ref, uid, alta, corte, rot, anon):
    with st.expander("Tabelas e casos"):
        st.markdown(f"**Registros repetidos por tipo (% dos atendimentos em {ano}) e variação em relação a {ref}, por unidade**")
        cols = {f"pct_{c}": n for c, n in {**PADROES, "ex_total": f"Total {ano}"}.items()}
        cols |= {"pct_ex_ref": f"Total {ref}", "d_ex_total": "Var. (p.p.)"}
        st.dataframe(u[["unidade", "atend", *cols]].rename(columns=cols), width="stretch", hide_index=True,
                     column_config={n: st.column_config.NumberColumn(format="%.1f") for n in cols.values()})
        st.markdown(f"**Unidades pela alta dos profissionais em relação a {ref}**")
        cl = classificar(prof, alta, corte)
        cl = cl.assign(unidade=cl.id_unidade.map(rot).fillna("Unidade —" if anon else cl.unidade.map(curto)))
        st.dataframe(cl.drop(columns="id_unidade"), width="stretch", hide_index=True)
        if len(p):
            st.markdown("**Profissionais da unidade**")
            st.dataframe(p[["rot", "atend", "pct_encaixe", "pct_ate10min", "pct_dia_mult", "pct_dia_mult_ref",
                            "d_dia_mult", "dur_mediana"]]
                         .rename(columns={"rot": "profissional", "pct_dia_mult_ref": f"pct_dia_mult {ref}",
                                          "d_dia_mult": "var. (p.p.)"}), width="stretch", hide_index=True)
        c = fc[(fc.especialidade == esp) & (fc.ano == ano) & (fc.id_unidade == uid)]
        if len(c):
            st.markdown(f"**{len(c)} dias com 5 ou mais registros da mesma pessoa**")
            st.dataframe(c[["dt", "n", "n_prof", "sequencia"]].sort_values(["n", "dt"], ascending=[False, True]),
                         width="stretch", hide_index=True)


def render():
    faltam = [n for n in ("fr_unidade_ano", "fr_prof_ano", "fr_casos") if not (DADOS / f"{n}.parquet").exists()]
    if faltam:
        st.warning(f"Rode a extração antes: {', '.join(faltam)} (extract.run).")
        return
    fu, fp, fc = carregar_fr()
    st.markdown(INTRO)

    c1, c2, c3 = st.columns([1.5, 1, 1])
    esps = sorted(fu.especialidade.unique())
    esp = c1.selectbox("Especialidade", esps, key="fr_esp",
                       index=esps.index("Fisioterapia") if "Fisioterapia" in esps else 0)
    anos = sorted(fu.ano.unique())
    ano = c2.selectbox("Ano", anos[1:], index=len(anos) - 2, key="fr_ano")
    refs = [a for a in anos if a < ano]
    ref = c3.selectbox("Comparar com (própria unidade)", refs, index=refs.index(ano - 2) if ano - 2 in refs else 0,
                       key="fr_ref")
    anon = st.toggle("Ocultar nomes das unidades", value=True, key="fr_anon")
    with st.expander("Parâmetros"):
        a, b, c, d = st.columns(4)
        min_u = a.number_input("Mín. atendimentos da unidade", 0, 50000, 1000, 500, key="fr_minu")
        min_p = b.number_input("Mín. atendimentos do profissional", 0, 5000, 300, 50, key="fr_minp")
        alta = c.slider("Alta mínima (pontos percentuais)", 0.5, 10.0, 2.0, 0.5, key="fr_alta")
        corte = d.slider("% da equipe para considerar 'equipe toda'", 50, 100, 75, 5, key="fr_corte")

    u = por_unidade(fu, esp, ano, ref, min_u)
    if u.empty or not u.ex_total.sum():
        st.info("Sem extras no mesmo dia neste recorte.")
        return
    ordem = u.sort_values("d_ex_total", ascending=False, na_position="last").id_unidade
    rot = ({i: f"Unidade {n}" for n, i in enumerate(ordem, 1)} if anon
           else dict(zip(u.id_unidade, u.unidade.map(curto))))
    u = u.assign(unidade=u.id_unidade.map(rot))

    k = u[["atend", "ex_total", "visitas", "visitas_3mais"]].sum()
    m = st.columns(3)
    m[0].metric("Atendimentos", fmt_number(k.atend, 0))
    m[1].metric("Registros repetidos no mesmo dia", pct(100 * k.ex_total / k.atend), help=f"{fmt_number(k.ex_total, 0)} atendimentos")
    m[2].metric("Visitas com 3 ou mais registros", pct(100 * k.visitas_3mais / k.visitas, 2),
                help="Visita = uma pessoa, em um dia, em uma especialidade.")

    _ranking(u, esp, ano, ref, alta)
    st.divider()
    lab = u.set_index("id_unidade").unidade
    opcoes = ordem.tolist()
    uid = st.selectbox("Unidade", opcoes, format_func=lambda i: lab[i], key=f"fr_unid_{esp}_{anon}")
    nome = lab[uid]
    col1, col2 = st.columns(2)
    with col1:
        _evolucao(fu, esp, uid, nome, ano, ref)
    with col2:
        prof = perfil_prof(fp, esp, ano, ref, min_p)
        p = _profissionais(prof, uid, ano, ref, alta, corte) if len(prof) else prof
    _detalhes(u, prof, p, fc, esp, ano, ref, uid, alta, corte, rot, anon)
    st.info(COMO_LER)