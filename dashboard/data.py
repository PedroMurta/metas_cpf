"""Leitura dos parquets gerados por extract.run — o dashboard não consulta o banco."""
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

DADOS = Path(__file__).resolve().parents[1] / "dados"
REGRA_META, PESSOA_UNICA = "CPF por unidade (regra da meta)", "Pessoa única no nível"


@st.cache_data
def carregar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Perfil de uso com bitmask de itens, catálogo de itens (especialidade|modalidade) e cadastro de unidades."""
    p = pd.read_parquet(DADOS / "perfil_cpf.parquet")
    cat = (p[["entidade", "itens"]].explode("itens").rename(columns={"itens": "item"})
           .drop_duplicates().sort_values(["entidade", "item"]).reset_index(drop=True))
    cat[["especialidade", "modalidade"]] = cat.item.str.split("|", expand=True)
    cat["bit"] = np.left_shift(np.int64(1), cat.index.to_numpy(dtype="int64"))
    bit = dict(zip(cat.item, cat.bit))
    p["bits"] = p.pop("itens").map(lambda t: sum(int(bit[i]) for i in t)).astype("int64")
    unid = (pd.read_parquet(DADOS / "volume_especialidade.parquet", columns=["id_unidade", "unidade", "conselho"])
            .drop_duplicates("id_unidade").fillna({"conselho": ""}).replace({"conselho": {"": "Sem regional"}}))
    return p, cat, unid


def recorte(p: pd.DataFrame, unid: pd.DataFrame, nivel: str, nome: str | None, regra: str) -> pd.DataFrame:
    """Linhas do perfil para o nível escolhido. Na regra da meta, conselho e nacional são somas de unidades."""
    if nivel == "Unidade":
        return p[(p.nivel == "unidade") & p.id_unidade.isin(unid.loc[unid.unidade == nome, "id_unidade"])]
    if regra == PESSOA_UNICA:
        return p[p.nivel == "nacional"] if nivel == "Nacional" else p[(p.nivel == "conselho") & (p.conselho == nome)]
    u = p[p.nivel == "unidade"]
    return u if nivel == "Nacional" else u[u.id_unidade.isin(unid.loc[unid.conselho == nome, "id_unidade"])]


def cpfs(p: pd.DataFrame, mascara: int) -> pd.Series:
    """CPFs distintos por ano de quem usou ao menos um item da máscara."""
    return p.loc[(p.bits.to_numpy() & mascara) != 0].groupby("ano").cpfs.sum()


def tabela_crescimento(dist: pd.DataFrame, nomes: str = "Negócio") -> pd.DataFrame:
    """Valores por ano + variação ano a ano + acumulado do período."""
    from charts.theme import fmt_number
    pct = lambda v: "—" if pd.isna(v) else f"{'+' if v >= 0 else ''}{fmt_number(v, 1)}%"
    yoy = dist.div(dist.shift(axis=1)).sub(1).mul(100).iloc[:, 1:]
    yoy.columns = [f"{a - 1}→{a}" for a in yoy.columns]
    a0, a1 = dist.columns[0], dist.columns[-1]
    yoy[f"{a0}→{a1}"] = 100 * (dist[a1] / dist[a0] - 1)
    t = dist.round(0).astype("Int64").join(yoy.map(pct))
    t.columns = t.columns.map(str)
    return t.reset_index(names=nomes)


# ---- Fracionamento -------------------------------------------------------------------------------------------------
PADROES = {"ex_duplicidade": "Duplicidade (mesmo prof., mesmo horário)",
           "ex_consecutivo": "Consecutivo (mesmo prof., ≤60 min)",
           "ex_espacado": "Mesmo prof., >60 min",
           "ex_prof_dif": "Profissionais diferentes"}


@st.cache_data
def carregar_fr() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fracionamento: unidade×ano, profissional×ano e casos com 5+ registros no dia, com nome/conselho da unidade."""
    unid = carregar()[2]
    ler = lambda n: pd.read_parquet(DADOS / f"{n}.parquet").merge(unid, on="id_unidade", how="left")
    fu, fp, fc = ler("fr_unidade_ano"), ler("fr_prof_ano"), ler("fr_casos")
    fu["ex_total"] = fu[list(PADROES)].sum(axis=1)
    return fu, fp, fc


@st.cache_data
def carregar_fu() -> pd.DataFrame:
    """Registros repetidos por unidade × ano (só agregados), com nome/conselho da unidade."""
    fu = pd.read_parquet(DADOS / "fr_unidade_ano.parquet").merge(carregar()[2], on="id_unidade", how="left")
    return fu.assign(ex_total=fu[list(PADROES)].sum(axis=1))


def por_unidade(fu: pd.DataFrame, esp: str, ano: int, ref: int, min_atend: int = 1000) -> pd.DataFrame:
    """% de extras por padrão no ano e variação (p.p.) do total sobre o próprio ano de comparação da unidade."""
    f = fu[(fu.especialidade == esp) & (fu.atend >= min_atend)]
    r = f[f.ano == ref].set_index("id_unidade")
    f = f[f.ano == ano].copy()
    for c in [*PADROES, "ex_total"]:
        f[f"pct_{c}"] = 100 * f[c] / f.atend
    f["pct_3mais"] = 100 * f.visitas_3mais / f.visitas
    f = f.join((100 * r.ex_total / r.atend).rename("pct_ex_ref"), on="id_unidade")
    f["d_ex_total"] = f.pct_ex_total - f.pct_ex_ref
    return f.sort_values("d_ex_total", ascending=False)


def serie_atend_visita(fu: pd.DataFrame, esp: str, destaque: list[int]) -> pd.DataFrame:
    """Atendimentos por visita no tempo: unidades em destaque separadas, resto agregado como controle."""
    f = fu[fu.especialidade == esp]
    f = f.assign(grupo=np.where(f.id_unidade.isin(destaque), f.unidade, "Demais unidades"))
    g = f.groupby(["grupo", "ano"], as_index=False)[["atend", "visitas"]].sum()
    return g.assign(atend_visita=g.atend / g.visitas)


def degraus(fu: pd.DataFrame, esp: str, min_pp: float = 5.0) -> pd.DataFrame:
    """Maior salto anual (p.p.) no % de extras com profissionais diferentes, por unidade."""
    p = fu[fu.especialidade == esp].pivot_table(index="id_unidade", columns="ano",
                                                values=["ex_prof_dif", "atend"], aggfunc="sum")
    d = (100 * p["ex_prof_dif"] / p["atend"]).diff(axis=1)
    out = pd.DataFrame({"salto_pp": d.max(axis=1), "ano_salto": d.idxmax(axis=1)}).dropna()
    return out[out.salto_pp >= min_pp].sort_values("salto_pp", ascending=False).reset_index()


def perfil_prof(fp: pd.DataFrame, esp: str, ano: int, ref: int, min_atend: int = 300) -> pd.DataFrame:
    """Percentuais por profissional no ano e variação (p.p.) do % em dias com 2+ registros sobre o próprio ano de comparação."""
    f = fp[(fp.especialidade == esp) & (fp.atend >= min_atend)]
    r = f[f.ano == ref].set_index(["id_unidade", "id_prof"])
    f = f[f.ano == ano].copy()
    for c, n in {"pct_encaixe": "n_encaixe", "pct_ate10min": "n_ate10", "pct_dia_mult": "n_dia_mult"}.items():
        f[c] = 100 * f[n] / f.atend
    f = f.join((100 * r.n_dia_mult / r.atend).rename("pct_dia_mult_ref"), on=["id_unidade", "id_prof"])
    f["d_dia_mult"] = f.pct_dia_mult - f.pct_dia_mult_ref
    return f


def classificar(prof: pd.DataFrame, alta: float = 2.0, corte: float = 75) -> pd.DataFrame:
    """Equipe toda (≥corte% dos profissionais com alta > `alta` p.p. sobre o próprio histórico), alguns ou nenhum."""
    h = prof.dropna(subset=["d_dia_mult"])
    g = (h.assign(subiu=h.d_dia_mult > alta)
         .groupby(["id_unidade", "unidade"], as_index=False)
         .agg(profissionais=("id_prof", "size"), atend=("atend", "sum"), prof_subiram=("subiu", "sum")))
    g["pct_prof_subiram"] = 100 * g.prof_subiram / g.profissionais
    g["padrao"] = np.select([g.pct_prof_subiram >= corte, g.prof_subiram > 0],
                            ["Equipe toda", "Alguns profissionais"], "Sem alta")
    return g.sort_values("pct_prof_subiram", ascending=False)


def serie_unidade(fu: pd.DataFrame, esp: str, uid: int) -> pd.DataFrame:
    """% de extras no mesmo dia por ano na unidade."""
    g = fu[(fu.especialidade == esp) & (fu.id_unidade == uid)].groupby("ano", as_index=False)[["atend", "ex_total"]].sum()
    return g.assign(pct=100 * g.ex_total / g.atend)


def salto_proprio(fu: pd.DataFrame, ano: int, ref: tuple[int, int] = (2019, 2021), pp: float = 5.0,
                  min_atend: int = 1000) -> pd.DataFrame:
    """Extras no mesmo dia por unidade (todas as especialidades) no ano vs a média da própria unidade no período ref."""
    g = fu.groupby(["id_unidade", "ano"])[["atend", "ex_total"]].sum()
    pct_ = 100 * g.ex_total / g.atend
    base = pct_[pct_.index.get_level_values("ano").isin(range(ref[0], ref[1] + 1))].groupby(level="id_unidade").mean()
    d = g.xs(ano, level="ano").assign(pct=lambda x: 100 * x.ex_total / x.atend, ref=base).dropna(subset=["ref"])
    d = d[d.atend >= min_atend]
    return d.assign(salto=d.pct - d.ref >= pp).sort_values("ex_total", ascending=False).reset_index()


# ---- Base de clientes ----------------------------------------------------------------------------------------------
@st.cache_data
def carregar_base() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fluxos de clientes: rede por visão/recorte, unidade (Núcleo) e conversão da Campanha."""
    unid = carregar()[2]
    rt = pd.read_parquet(DADOS / "retencao.parquet")
    bu = pd.read_parquet(DADOS / "balanco_unidade.parquet").merge(unid, on="id_unidade", how="left")
    cc = pd.read_parquet(DADOS / "conversao_campanha.parquet")
    return rt, bu, cc


def serie_base(rt: pd.DataFrame, bu: pd.DataFrame, visao: str, recorte: str, id_unidade: int | None = None) -> pd.DataFrame:
    """Atendidos = novos + retidos + reativados por ano; perdidos e retenção (retidos em t ÷ atendidos em t-1)."""
    cols = ["ano", "atendidos", "novos", "retidos", "reativados"]
    d = (bu[(bu.entidade == recorte) & (bu.id_unidade == id_unidade)] if id_unidade is not None
         else rt[(rt.visao == visao) & (rt.recorte == recorte)])
    d = d[cols + (["retencao_novos_pct"] if id_unidade is None else [])].set_index("ano").sort_index()
    d = d.reindex(range(d.index.min(), d.index.max() + 1))
    d["atend_ant"] = d.atendidos.shift()
    d["perdidos"] = d.atend_ant - d.retidos
    d["retencao"] = 100 * d.retidos / d.atend_ant
    return d.reset_index()


@st.cache_data
def carregar_agenda_ano() -> pd.DataFrame:
    """Agenda SEST por ano: atendimentos e CPFs distintos somados por unidade (regra da meta)."""
    v = pd.read_parquet(DADOS / "volume_especialidade.parquet",
                        columns=["nivel", "ano", "fonte", "atendimentos", "cpfs"])
    v = v[(v.nivel == "ano_fonte") & (v.fonte == "Agenda de Atendimento")]
    return v.groupby("ano", as_index=False)[["atendimentos", "cpfs"]].sum()


# ---- Proposta de meta ----------------------------------------------------------------------------------------------
# A meta é calculada no notebook (notebooks/meta_cpf.ipynb, regra em metodologia.py) e lida aqui pronta.
AREAS = ["Odontologia", "Fisioterapia", "Nutrição", "Psicologia"]
ANT = MERC = DADOS          # deploy: insumos externos ficam em dados/
FAIXAS_APC = ["caiu >10%", "estável (±10%)", "subiu >10%"]
FAIXAS_MERC = ["até 10%", "10–20%", "20–40%", "acima de 40%"]


@st.cache_data
def carregar_proposta(ano_base: int = 2025) -> dict:
    """Insumos das perguntas 1–3: SIGOP (dados/), RAIS e público do transporte (estudos vizinhos)."""
    uo = pd.read_parquet(MERC / "dim_uo_municipio.parquet")
    pub = pd.read_parquet(ANT / "pessoas_publico.parquet")
    return dict(
        uo=uo, inaug=uo.groupby("id_unidade").data_inauguracao.first().dt.year,
        v=pd.read_parquet(DADOS / "volume_especialidade.parquet",
                          columns=["nivel", "fonte", "especialidade", "id_unidade", "ano", "atendimentos", "cpfs"]),
        ytd=pd.read_parquet(DADOS / "agenda_4areas_ytd.parquet"),
        rais=(pd.read_parquet(MERC / "fato_rais_municipio_totais.parquet").query("ano_base == 2024")
              .set_index("codigo_ibge").qtd_trabalhadores),
        pub=pub.query("negocio == 'SEST' and publico == 'Transporte' and ano == @ano_base"))


@st.cache_data
def carregar_meta(ano_meta: int = 2026) -> pd.DataFrame:
    """Meta de pessoas por unidade, com a referência, a origem da meta e os cinco testes (saída do notebook)."""
    return pd.read_parquet(DADOS / f"meta_cpf_{ano_meta}.parquet")


@st.cache_data
def carregar_meta_areas(ano_meta: int = 2026) -> pd.DataFrame:
    """Atendimentos por pessoa de cada unidade × área e a referência (P25 do porte) usada na meta."""
    return pd.read_parquet(DADOS / f"meta_cpf_{ano_meta}_areas.parquet")


def madura(ids, inaug, ano=2025, idade=2):
    """Exclui unidades com menos de `idade` anos de inauguração no ano-base."""
    return ~((ano - pd.Index(ids).map(inaug)) < idade)


def _agenda_area(v):
    return v[(v.nivel == "ano_especialidade") & (v.fonte == "Agenda de Atendimento") & v.especialidade.isin(AREAS)]


def t1_producao_pessoas(ytd, inaug, a0=2025, a1=2026, min_cpf=300):
    """Jan–mês a1 vs a0 por unidade (absolutos e variações) e na rede; parte do crescimento vinda de atend./pessoa."""
    t = ytd[ytd.especialidade == ""].pivot_table(["atendimentos", "cpfs"], "id_unidade", "ano").dropna()
    t = t[(t.cpfs[a0] >= min_cpf) & madura(t.index, inaug, a0)]
    d = pd.DataFrame({"at25": t.atendimentos[a0], "at26": t.atendimentos[a1], "c25": t.cpfs[a0], "c26": t.cpfs[a1]})
    d["ga"], d["gc"] = d.at26 / d.at25 - 1, d.c26 / d.c25 - 1
    s = d[["at25", "at26", "c25", "c26"]].sum()
    ga, gc = s.at26 / s.at25 - 1, s.c26 / s.c25 - 1
    return d, ga, gc, 1 - np.log1p(gc) / np.log1p(ga)


def t2_intensidade(v, a0=2019, a1=2025, min_cpf=100, corte=0.10):
    """Atendimentos por pessoa (a0 e a1) por área e unidade, e nº de unidades por faixa de variação (±corte)."""
    u = _agenda_area(v).groupby(["especialidade", "id_unidade", "ano"])[["atendimentos", "cpfs"]].sum()
    u = u[u.cpfs >= min_cpf]
    w = (u.atendimentos / u.cpfs).unstack("ano")[[a0, a1]].dropna()
    f = pd.cut(w[a1] / w[a0] - 1, [-np.inf, -corte, corte, np.inf], labels=FAIXAS_APC)
    cnt = f.groupby(level="especialidade", observed=False).value_counts().unstack().reindex(AREAS)
    return cnt, w


def t3_mercado(uo, rais, pub, inaug):
    """Pessoas do transporte atendidas ÷ trabalhadores formais (RAIS) da área de cada unidade."""
    mercado = (uo.codigo_ibge.map(rais).fillna(0) * uo.fator_rateio).groupby(uo.id_unidade).sum()
    atend = pub[pub.nivel == "unidade"].groupby("id_unidade").pessoas.sum()
    pen = (atend / mercado[mercado > 0]).dropna()
    pen = pen[madura(pen.index, inaug)]
    cnt = pd.cut(pen, [0, 0.1, 0.2, 0.4, np.inf], labels=FAIXAS_MERC).value_counts().reindex(FAIXAS_MERC)
    return dict(cnt=cnt, nac=pub[pub.nivel == "nacional"].pessoas.sum() / rais.sum(), tot=rais.sum(),
                pen=pen, mercado=mercado, atend=atend)