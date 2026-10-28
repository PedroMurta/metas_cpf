"""Componentes Plotly do estudo — tema institucional de charts/theme.py (mesmo visual de ../meta_cpfs_unicos)."""
from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go
from charts.theme import (apply_theme, get_formatter, fmt_number, COLORS, COR_NEUTRA, COR_POSITIVO, COR_NEGATIVO,
                          TEXT_COLOR)

CORES_NEGOCIO = {"SEST": COLORS["primary"], "SENAT": COLORS["secondary"], "Campanha": COLORS["purple"]}
LEGENDA_BAIXO = dict(orientation="h", x=0, xanchor="left", y=-0.1, yanchor="top", borderwidth=0)


def titulo(achado: str, detalhe: str = "") -> str:
    """Storytelling: achado em negrito + detalhe técnico em cinza."""
    sub = f"<br><span style='font-size:12px;color:{COR_NEUTRA}'>{detalhe}</span>" if detalhe else ""
    return f"<b>{achado}</b>{sub}"


def finalizar(fig: go.Figure, title: str, height: int | None) -> go.Figure:
    fig = apply_theme(fig, title, show_grid=True, height=height, legend=LEGENDA_BAIXO,
                      margin=dict(t=80 if title else 10, b=40))
    if title:
        fig.update_layout(title=dict(x=0, xanchor="left"))
    return fig


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def fig_evolucao(df, x, y, cor, title="", *, value_fmt="abbrev", height=400) -> go.Figure:
    """Barras por período + selo de variação entre períodos e conector entre os topos."""
    fmt, xs, ys = get_formatter(value_fmt), df[x].astype(str).tolist(), df[y].tolist()
    largura, topo = 0.55, max(ys) * 1.22
    fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=cor, width=largura, text=[fmt(v) for v in ys],
                           textposition="outside", textfont=dict(size=12, color=TEXT_COLOR),
                           hovertemplate="%{x}: %{text}<extra></extra>"))
    for i in range(1, len(ys)):
        var = 100 * (ys[i] / ys[i - 1] - 1)
        c, seta = (COR_POSITIVO, "▲") if var >= 0 else (COR_NEGATIVO, "▼")
        fig.add_shape(type="line", x0=i - 1 + largura / 2, x1=i - largura / 2, y0=ys[i - 1], y1=ys[i],
                      line=dict(color=c, width=1.5, dash="dot"))
        fig.add_annotation(x=i - 0.5, y=topo, showarrow=False, text=f"{seta} {fmt_number(abs(var), 1)}%",
                           font=dict(size=13, color=c), bgcolor=rgba(c, 0.10),
                           bordercolor=rgba(c, 0.35), borderwidth=1, borderpad=5)
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(type="category")
    fig.update_yaxes(showticklabels=False, showgrid=False, range=[0, max(ys) * 1.35])
    return fig


def fig_variacao(dist: pd.DataFrame, title="", *, limite=50, height=None) -> go.Figure:
    """Heatmap da variação % vs ano anterior (linhas = séries, colunas = anos). Cor limitada a ±limite."""
    var = dist.div(dist.shift(axis=1)).sub(1).mul(100).iloc[:, 1:]
    txt = var.map(lambda v: "" if pd.isna(v) else f"{'+' if v >= 0 else ''}{fmt_number(v, 1)}%")
    fig = go.Figure(go.Heatmap(z=var.values, x=[f"{a - 1}→{a}" for a in var.columns], y=var.index,
                               zmin=-limite, zmax=limite, showscale=False, xgap=2, ygap=2,
                               colorscale=[[0, COR_NEGATIVO], [0.5, "white"], [1, COR_POSITIVO]],
                               text=txt.values, texttemplate="%{text}",
                               hovertemplate="%{y}<br>%{x}: %{text}<extra></extra>"))
    fig = finalizar(fig, title, height or max(260, 34 * len(var) + 130))
    fig.update_xaxes(type="category")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


# ---- Fracionamento -------------------------------------------------------------------------------------------
CINZA = rgba(COR_NEUTRA, 0.35)
CORES_PADRAO = {"ex_duplicidade": COR_NEGATIVO, "ex_consecutivo": rgba(COR_NEGATIVO, 0.55),
                "ex_espacado": CINZA, "ex_prof_dif": CORES_NEGOCIO["SEST"]}
CORES_CLASSE = {"Equipe toda": CORES_NEGOCIO["SEST"], "Alguns profissionais": rgba(COR_NEUTRA, 0.7),
                "Sem alta": rgba(COR_NEUTRA, 0.25)}


def _altura(n: int) -> int:
    return max(380, 24 * n + 150)


def fig_empilhado_h(df, rotulo, series, title="") -> go.Figure:
    """Barras horizontais empilhadas (% dos atendimentos). series = [(coluna, nome, cor), ...]."""
    fig = go.Figure([go.Bar(y=df[rotulo], x=df[c], name=n, orientation="h", marker_color=cor,
                            hovertemplate=f"%{{y}}<br>{n}: %{{x:.1f}}%<extra></extra>") for c, n, cor in series])
    fig = finalizar(fig, title, _altura(len(df)))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="% dos atendimentos", ticksuffix="%")
    fig.update_yaxes(autorange="reversed", type="category", showgrid=False)
    return fig


def fig_linhas_destaque(g, x, y, grupo, title="", controle="Demais unidades", height=440) -> go.Figure:
    """Controle em cinza tracejado, destaques na cor SEST, rótulo direto no fim de cada linha (sem legenda)."""
    fig = go.Figure()
    for nome, d in g.sort_values(x).groupby(grupo):
        base = nome == controle
        cor = COR_NEUTRA if base else CORES_NEGOCIO["SEST"]
        fig.add_scatter(x=d[x], y=d[y], mode="lines+markers", name=nome,
                        line=dict(color=cor, width=4 if base else 2, dash="dash" if base else "solid"),
                        hovertemplate=f"{nome}<br>%{{x}}: %{{y:.2f}}<extra></extra>")
        fig.add_annotation(x=d[x].iloc[-1], y=d[y].iloc[-1], text=nome, xanchor="left", xshift=8,
                           showarrow=False, font=dict(size=11, color=cor))
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False, margin=dict(r=230))
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title="Atendimentos por visita")
    return fig


def fig_barras_h(df, x, y, cores, title="", ref=None, ref_txt="", sufixo="%", sinal=False) -> go.Figure:
    """Barras horizontais, cor por linha e linha de referência opcional. `sinal` mostra + nos positivos."""
    fig = go.Figure(go.Bar(x=df[x], y=df[y], orientation="h", marker_color=cores,
                           text=[f"{'+' if sinal and v >= 0 else ''}{fmt_number(v, 1)}{sufixo}" for v in df[x]],
                           textposition="outside", textfont=dict(size=11, color=TEXT_COLOR),
                           hovertemplate="%{y}: %{text}<extra></extra>"))
    if ref is not None:
        fig.add_vline(x=ref, line_dash="dot", line_color=COR_NEUTRA, annotation_text=ref_txt,
                      annotation_position="top right", annotation_font_color=COR_NEUTRA)
    fig = finalizar(fig, title, _altura(len(df)))
    fig.update_layout(showlegend=False)
    lo, hi = (min(df[x].min(), 0), max(df[x].max(), ref or 0)) if len(df) else (0, 1)
    fig.update_xaxes(ticksuffix=sufixo, range=[lo * 1.15, hi * 1.15])
    fig.update_yaxes(autorange="reversed", type="category", showgrid=False)
    return fig


def fig_linhas_destaque(g, x, y, grupo, title="", controle="Restante da rede", y_title="", sufixo="",
                        height=400) -> go.Figure:
    """Controle em cinza tracejado, destaque na cor SEST, rótulo direto no fim de cada linha (sem legenda)."""
    fig = go.Figure()
    for nome, d in g.sort_values(x).groupby(grupo):
        base = nome == controle
        cor = COR_NEUTRA if base else CORES_NEGOCIO["SEST"]
        fig.add_scatter(x=d[x], y=d[y], mode="lines+markers", name=nome,
                        line=dict(color=cor, width=2 if base else 3, dash="dash" if base else "solid"),
                        hovertemplate=f"{nome}<br>%{{x}}: %{{y:.1f}}{sufixo}<extra></extra>")
        fig.add_annotation(x=d[x].iloc[-1], y=d[y].iloc[-1], text=f"<b>{nome}</b>", xanchor="left", xshift=8,
                           showarrow=False, font=dict(size=12, color=cor))
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False, margin=dict(r=200))
    fig.update_xaxes(dtick=1, showgrid=False)
    fig.update_yaxes(title=y_title, ticksuffix=sufixo, rangemode="tozero")
    return fig


# ---- Base de clientes ----------------------------------------------------------------------------------------
def fig_empilhado_v(df, x, series, title="", height=420) -> go.Figure:
    """Barras verticais empilhadas. series = [(coluna, nome, cor), ...]."""
    fig = go.Figure([go.Bar(x=df[x].astype(str), y=df[c], name=n, marker_color=cor,
                            hovertemplate=f"{n}<br>%{{x}}: %{{y:,.0f}}<extra></extra>") for c, n, cor in series])
    fig = finalizar(fig, title, height)
    fig.update_layout(barmode="stack", bargap=0.3)
    fig.update_xaxes(type="category", showgrid=False)
    return fig


def fig_cascata(rotulos, valores, medidas, title="", height=400) -> go.Figure:
    """Cascata: medidas 'absolute' | 'relative' | 'total'. Queda em vermelho, entrada em verde, bases em cinza."""
    fmt = lambda v: f"{'+' if v > 0 else ''}{fmt_number(v, 0)}"
    fig = go.Figure(go.Waterfall(x=rotulos, y=valores, measure=medidas, textposition="outside",
                                 text=[fmt_number(v, 0) if m != "relative" else fmt(v) for v, m in zip(valores, medidas)],
                                 decreasing=dict(marker=dict(color=COR_NEGATIVO)),
                                 increasing=dict(marker=dict(color=COR_POSITIVO)),
                                 totals=dict(marker=dict(color=COR_NEUTRA)),
                                 connector=dict(line=dict(color=CINZA, width=1, dash="dot"))))
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False)
    fig.update_yaxes(showticklabels=False, showgrid=False)
    return fig


def fig_barras_v(df, x, y, cores, title="", sufixo="", height=380) -> go.Figure:
    """Barras verticais com valor no topo e cor por barra."""
    fig = go.Figure(go.Bar(x=df[x].astype(str), y=df[y], marker_color=cores, width=0.55,
                           text=[f"{fmt_number(v, 1)}{sufixo}" for v in df[y]], textposition="outside",
                           textfont=dict(size=12, color=TEXT_COLOR), hovertemplate="%{x}: %{text}<extra></extra>"))
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(type="category", showgrid=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, range=[0, df[y].max() * 1.25])
    return fig


def fig_barras_anonimas(valores, cores, title="", y_title="", height=380) -> go.Figure:
    """Barras ordenadas sem rótulo de categoria (unidades não identificadas)."""
    fig = go.Figure(go.Bar(x=list(range(1, len(valores) + 1)), y=valores, marker_color=cores,
                           hovertemplate="%{y:,.0f}<extra></extra>"))
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False, bargap=0.1)
    fig.update_xaxes(showticklabels=False, showgrid=False, title="unidades, da que mais tem registros repetidos para a que menos")
    fig.update_yaxes(title=y_title)
    return fig


def fig_barras_v(df, x, y, cores, title="", sufixo="", height=380, casas=1) -> go.Figure:
    """Barras verticais com valor no topo e cor por barra."""
    fig = go.Figure(go.Bar(x=df[x].astype(str), y=df[y], marker_color=cores, width=0.55,
                           text=[f"{fmt_number(v, casas)}{sufixo}" for v in df[y]], textposition="outside",
                           textfont=dict(size=12, color=TEXT_COLOR), hovertemplate="%{x}: %{text}<extra></extra>"))
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(type="category", showgrid=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, range=[0, df[y].max() * 1.25])
    return fig


def fig_dispersao(x, y, destaque, title="", x_title="", y_title="", lim=None, rotulos=("demais", "destaque"),
                  height=480) -> go.Figure:
    """Dispersão em % com diagonal y = x. Pontos sem identificação."""
    fig = go.Figure()
    for sel, cor, nome in [(~destaque, CINZA, rotulos[0]), (destaque, CORES_NEGOCIO["SEST"], rotulos[1])]:
        fig.add_scatter(x=x[sel], y=y[sel], mode="markers", name=nome,
                        marker=dict(color=cor, size=9, opacity=0.85, line=dict(color="white", width=1)),
                        hovertemplate="x %{x:+.1f}% · y %{y:+.1f}%<extra></extra>")
    a, b = lim or (min(x.min(), y.min()), max(x.max(), y.max()))
    fig.add_scatter(x=[a, b], y=[a, b], mode="lines", line=dict(color=COR_NEUTRA, dash="dot", width=1),
                    showlegend=False, hoverinfo="skip")
    fig = finalizar(fig, title, height)
    fig.update_xaxes(title=x_title, ticksuffix="%", range=lim, zeroline=True, zerolinecolor=CINZA)
    fig.update_yaxes(title=y_title, ticksuffix="%", range=lim, zeroline=True, zerolinecolor=CINZA)
    return fig


def fig_empilhado_100h(df, series, title="", height=340) -> go.Figure:
    """Barras horizontais 100% (índice = categorias). series = [(coluna, nome, cor), ...] com valores em %."""
    fig = go.Figure([go.Bar(y=df.index, x=df[c], name=n, orientation="h", marker_color=cor,
                            text=[f"{v:.0f}%" for v in df[c]], textposition="inside",
                            hovertemplate=f"%{{y}}: %{{x:.0f}}%<extra>{n}</extra>") for c, n, cor in series])
    fig = finalizar(fig, title, height)
    fig.update_layout(barmode="stack")
    fig.update_xaxes(range=[0, 100], ticksuffix="%", title="% das unidades")
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return fig


def fig_barras_agrupadas(df, x, series, title="", sufixo="%", height=440, sinal=True, casas=1) -> go.Figure:
    """Barras verticais agrupadas com rótulo de valor. series = [(coluna, nome, cor), ...]."""
    fmt = lambda v: f"{'+' if sinal and v >= 0 else ''}{fmt_number(v, casas)}{sufixo}"
    fig = go.Figure([go.Bar(x=df[x], y=df[c], name=n, marker_color=cor, textposition="outside",
                            text=[fmt(v) for v in df[c]], hovertemplate=f"%{{x}}: %{{text}}<extra>{n}</extra>")
                     for c, n, cor in series])
    fig = finalizar(fig, title, height)
    vals = df[[c for c, _, _ in series]]
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_xaxes(type="category", showgrid=False)
    fig.update_yaxes(ticksuffix=sufixo, showgrid=False, zeroline=True, zerolinecolor=CINZA,
                     range=[min(0, vals.min().min()) * 1.25, vals.max().max() * 1.25])
    return fig


def fig_comparacao(rotulos, valores, cores, title="", sufixo="%", casas=1, sinal=True, height=340) -> go.Figure:
    """Poucas barras lado a lado, valor no topo; aceita negativos."""
    valores = list(valores)
    txt = [f"{'+' if sinal and v >= 0 else ''}{fmt_number(v, casas)}{sufixo}" for v in valores]
    fig = go.Figure(go.Bar(x=list(rotulos), y=valores, marker_color=cores, width=0.5, text=txt, textposition="outside",
                           textfont=dict(size=14, color=TEXT_COLOR), hovertemplate="%{x}: %{text}<extra></extra>"))
    fig = finalizar(fig, title, height)
    lo, hi = min(0, min(valores)), max(0, max(valores))
    pad = (hi - lo) * 0.3 or 1
    fig.update_layout(showlegend=False)
    fig.update_xaxes(type="category", showgrid=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=True, zerolinecolor=CINZA,
                     range=[lo - (pad if lo < 0 else 0), hi + pad])
    return fig