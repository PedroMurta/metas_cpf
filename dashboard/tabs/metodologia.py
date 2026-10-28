"""Metodologia: grupos de porte, referência de cada grupo e um exemplo real da conta da meta."""
from html import escape

import numpy as np
import pandas as pd
import streamlit as st
from data import AREAS, DADOS, carregar_meta, carregar_meta_areas

ANO_BASE, ANO_META, CAPTURA, PISO = 2025, 2026, 0.25, 0.05
dec = lambda v, c=1: f"{v:,.{c}f}".replace(",", "X").replace(".", ",").replace("X", ".")
num = lambda v: dec(v, 0)
var = lambda f, c=1: f"{'+' if f >= 0 else '−'}{dec(abs(100 * f), c)}%"
pct = lambda f: f"{dec(100 * f, 0)}%"

CSS = """<style>
.mt-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:8px 0 16px}
.mt-card{background:#e8f4fa;padding:20px 24px;border-radius:4px}
.mt-card h4{margin:0 0 10px;color:#0f2540;font:600 18px var(--font-body,Inter)}
.mt-card .v{color:#0f2540;font:700 22px/1.3 var(--font-body,Inter)}
.mt-card .s{color:#0f2540;font:600 16px/1.4 var(--font-body,Inter)}
.mt-faixa{background:#0f2540;color:#fff;padding:20px 28px;border-radius:4px}
.mt-faixa h3{margin:0 0 14px;padding-bottom:10px;border-bottom:1px dotted rgba(255,255,255,.35);color:#fff;font:600 22px var(--font-body,Inter)}
.mt-faixa .g{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.mt-faixa .l{color:#00b8e6;font:600 17px var(--font-body,Inter);margin-bottom:6px}
.mt-faixa .x{font:600 18px/1.4 var(--font-body,Inter)}
.mt-nota{background:#e8f4fa;color:#0f2540;padding:14px 20px;border-radius:4px;font:600 15px var(--font-body,Inter);margin:8px 0}
.mt-final{color:#0f2540;font:700 19px var(--font-body,Inter);margin:16px 0 4px}
@media (max-width:767px){.mt-cards,.mt-faixa .g{grid-template-columns:1fr}}
</style>"""


@st.cache_data
def _grupos() -> pd.DataFrame:
    """8 grupos de Sturges (todas as unidades com produção no ano-base): escala arredondada, faixa observada e contagem."""
    a = pd.read_parquet(DADOS / "agenda_4areas.parquet").query("ano == @ANO_BASE").groupby("id_unidade").atendimentos.sum()
    a = a[a > 0]
    k = int(round(1 + np.log2(a.size)))
    g = pd.cut(a, bins=k, labels=[f"G{i}" for i in range(1, k + 1)])
    t = a.groupby(g, observed=False).agg(unidades="size", de="min", ate="max")
    w = np.ceil(a.max() / k / 1000) * 1000
    t["escala"] = [f"{num(0 if i == 0 else i * w + 1)} a {num((i + 1) * w)}" for i in range(k)]
    t["faixa"] = [num(d) if d == m else f"{num(d)} a {num(m)}" for d, m in zip(t.de, t.ate)]
    return t


def _exemplo(res):
    """Unidade mais próxima das medianas de produção e de atendimentos por pessoa, com meta vinda da referência."""
    r = res[res.origem == "referência"]
    dist = ((r.cpf0 * r.apc).rank(pct=True) - 0.5).abs() + (r.apc.rank(pct=True) - 0.5).abs()
    return dist.idxmin()


def _conta(r, nome):
    base, pot = r.base, r.meta_at / r.apc_bench
    gap = max(pot - base, 0)
    regra = base + CAPTURA * gap
    minimo = r.origem == "mínimo"
    st.markdown(f"**{escape(nome)}** ({r.porte}) · {ANO_BASE}: **{num(r.cpf0 * r.apc)} atendimentos** para "
                f"**{num(r.cpf0)} pessoas** ({dec(r.apc, 2)} por pessoa). Meta de atendimentos: "
                f"**{num(r.meta_at)}**. Referência equivalente do grupo para essa unidade: **{dec(r.apc_bench, 2)}**.")
    st.html(CSS + f"""
<div class="mt-cards">
  <div class="mt-card"><h4>1. Linha de base</h4><div class="v">{num(r.meta_at)} ÷ {dec(r.apc, 2)}<br>≈ {num(base)} pessoas</div></div>
  <div class="mt-card"><h4>2. Potencial</h4><div class="v">{num(r.meta_at)} ÷ {dec(r.apc_bench, 2)}<br>≈ {num(pot)} pessoas</div></div>
  <div class="mt-card"><h4>3. Oportunidade</h4><div class="s">Diferença potencial de<br>aproximadamente {num(gap)} pessoas</div></div>
</div>
<div class="mt-faixa"><h3>Captura gradual: não é exigir 100% do potencial</h3><div class="g">
  <div><div class="l">Base</div><div class="x">~{num(base)}<br>ponto de partida</div></div>
  <div><div class="l">Gap positivo</div><div class="x">~{num(gap)}<br>pessoas de oportunidade</div></div>
  <div><div class="l">Meta: {pct(CAPTURA)} do gap</div><div class="x">~{num(base)} + {pct(CAPTURA)} do gap (~{num(CAPTURA * gap)})<br>= {num(regra)} pessoas</div></div>
</div></div>
<div class="mt-final">Meta: {num(r.meta_cpf)} pessoas ({var(r.crescimento)} frente a {ANO_BASE}).
{f"A conta daria {var(regra / r.cpf0 - 1)}; vale o mínimo de {var(PISO, 0)}." if minimo else f"Os {pct(CAPTURA)} incidem sobre o gap, não sobre a base."}</div>""")
    st.caption("Valores exibidos arredondados. O cálculo usa os valores completos e arredonda a meta para cima. "
               "Referência equivalente: as referências de cada área do grupo, combinadas pelo peso de cada área na unidade.")


def render():
    res, areas = carregar_meta(ANO_META), carregar_meta_areas(ANO_META)

    st.caption(f"Base: atendimentos e pessoas de {ANO_BASE}, último ano completo. A conta é aplicada sobre a meta de "
               f"atendimentos já pactuada para cada unidade.")
    st.subheader("1. Unidades agrupadas pelo porte")
    st.markdown(f"Oito classes de Sturges pela produção de {ANO_BASE} (odontologia, fisioterapia, nutrição e psicologia). "
                f"Cada unidade só é comparada com as do seu grupo.")
    g = _grupos()
    st.dataframe(pd.DataFrame({"Grupo": g.index.astype(str), "Escala visual*": g.escala,
                               f"Atendimentos observados em {ANO_BASE}": g.faixa, "Unidades": g.unidades}),
                 hide_index=True, width="stretch")
    st.html(CSS + '<div class="mt-nota">*A escala arredondada é ilustrativa e não determina o grupo de cada unidade. '
                  'Os cálculos usam os limites originais de Sturges.</div>')

    st.subheader("2. Referência de cada grupo")
    t = areas.groupby(["grupo", "especialidade"]).ref.first().unstack().reindex(columns=AREAS)
    st.dataframe(t.map(lambda v: dec(v, 2) if pd.notna(v) else "—").rename_axis("Grupo").reset_index(),
                 hide_index=True, width="stretch")
    st.html(CSS + '<div class="mt-nota">A referência é, em cada área, o menor nível de atendimentos por pessoa do grupo, '
                  'desconsiderando os casos extremos.</div>')
    st.caption("Atendimentos por pessoa no ano, 2025. G6, G7 e G8 compartilham a referência.")
    with st.expander("Por que não usar simplesmente o menor valor do grupo?"):
        st.markdown("O menor valor isolado costuma ser de uma unidade menor ou com menos especialidades, que atende cada "
                    "pessoa menos vezes por ter uma oferta mais restrita. Comparar todas com esse caso seria injusto. Por "
                    "isso, a referência é o nível baixo que **se repete** entre as unidades do grupo, e não o caso "
                    "isolado (tecnicamente, o percentil 25). Quando o grupo tem poucas unidades com a área (menos de 5), "
                    "a referência considera todas as unidades do país.")

    st.subheader("3. Exemplo real")
    c1, c2, c3 = st.columns([1, 2, 1], vertical_alignment="bottom")
    ver = c1.radio("Exemplo", ["Unidade típica", "Escolher unidade"], horizontal=True, key="mt_ver")
    ocultar = c3.toggle("Ocultar nomes", value=True, key="mt_ocultar")
    rot = (res.porte + " · unidade " + res.groupby("porte").cumcount().add(1).astype(str)) if ocultar else res.unidade
    if ver == "Unidade típica":
        uid = _exemplo(res)
        nome = "Unidade típica da rede" if ocultar else res.unidade[uid]
    else:
        uid = c2.selectbox("Unidade", rot.sort_values().index, format_func=rot.get, key="mt_unid")
        nome = rot[uid]
    _conta(res.loc[uid], nome)