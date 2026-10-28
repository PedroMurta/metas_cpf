"""
Tema visual padronizado — Paleta Institucional Sólida
+ Helpers de formatação reutilizáveis (pt-BR)

Mesmas funções e assinaturas de sempre (apply_theme, criar_gradiente, fmt_*,
get_formatter, PLOTLY_CONFIG). Só o visual mudou: paleta sólida na identidade
da Matriz, hover elegante, grid horizontal sutil, cantos arredondados nas barras
e spline leve nas linhas.
"""
from __future__ import annotations
import math
import plotly.graph_objects as go

# ── Paleta institucional sólida (era pastel) ──
# Base: azul-assinatura, navy e laranja SENAT + apoio sólido e harmônico.
COLORS = {
    "primary": "#0c64a3", "secondary": "#ea580c", "accent": "#c0392b",
    "success": "#15803d", "purple": "#7627d6", "orange": "#d97706",
    "light_blue": "#2a78d6", "mint": "#0ca30c", "peach": "#e06666", "lavender": "#8fac1b",
}

COLORS_ESPECIALIDADES = {
    "Odontologia": "#0c64a3", "Fisioterapia": "#ea580c",
    "Psicologia": "#c0392b", "Nutrição": "#15803d", "Radiologia": "#7627d6",
}

# Colorway categórico sólido: cores distinguíveis, sem os tons lavados de antes.
PLOTLY_COLORWAY = [
    "#0c64a3", "#ea580c", "#15803d", "#c0392b", "#7627d6",
    "#d97706", "#2a78d6", "#0ca30c", "#8fac1b", "#574b63",
]

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}

# strftime %b sai em inglês no locale C do servidor — rótulos de mês sempre daqui
MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def fmt_mes_pt(dt_series):
    """Série datetime → rótulos 'Fev/26' em pt-BR."""
    import pandas as pd
    dt = pd.to_datetime(dt_series, errors="coerce")
    return dt.map(lambda d: f"{MESES_PT[d.month - 1]}/{d:%y}" if pd.notna(d) else None)


FONT_FAMILY = "Inter, system-ui, -apple-system, Segoe UI, sans-serif"
TEXT_COLOR = "#1a1a1a"           # texto principal (era #3d3a2a amarelado)
TITULO_COR = "#002969"           # navy institucional para títulos
EIXO_COR   = "rgba(0,0,0,0.55)"  # texto dos eixos
GRID_COR   = "rgba(0,0,0,0.06)"  # grade horizontal sutil

# ── Tokens semânticos (fonte única — não usar hex avulso nos gráficos) ──
# Estados/julgamento: um verde, um vermelho, um âmbar — em todo o app.
COR_POSITIVO  = "#15803d"   # bom / acima da meta / na faixa / subiu
COR_NEGATIVO  = "#b91c1c"   # ruim / fora da faixa / caiu
COR_ALERTA    = "#d97706"   # atenção / limites (mín/máx) / parcial
COR_DESTAQUE  = "#4a81bf"   # unidade selecionada / elemento ativo
COR_NEUTRA    = "#6b7280"   # texto secundário / estável
COR_NEUTRA_GRAFICA = "#94a3b8"  # linhas/pontos neutros de fundo
# Linhas de referência: meta = verde pontilhado; limites de faixa = âmbar.
REF_META   = {"color": COR_POSITIVO, "width": 1.5, "dash": "dot"}
REF_LIMITE = {"color": COR_ALERTA,   "width": 1.5, "dash": "dot"}


# =============================================================================
# Formatação pt-BR (INALTERADA)
# =============================================================================

def fmt_int(n) -> str:
    """1234567 -> '1.234.567'"""
    try:
        return f"{int(round(float(n))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(n)


def fmt_number(n: float, decimals: int = 0) -> str:
    """Número pt-BR com casas decimais: 1234.5 -> '1.234,5'"""
    decimals = max(decimals, 0)
    try:
        return f"{float(n):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(n)


def fmt_brl(n: float, decimals: int = 0) -> str:
    """Moeda: 1234.5 -> 'R$ 1.234' (ou 'R$ 1.234,50' com decimals=2)"""
    return f"R$ {fmt_number(n, decimals)}"


def fmt_pct(n: float, decimals: int = 1) -> str:
    """Percentual: 87.3 -> '87,3%'"""
    return f"{fmt_number(n, decimals)}%"


def fmt_abbrev(n: float, decimals: int = 1) -> str:
    """Abreviação pt-BR: 1_500_000 -> '1,5 mi'"""
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    absn = abs(n)
    if absn < 1_000:
        return fmt_int(n)
    if absn < 1_000_000:
        return f"{fmt_number(n / 1_000, decimals)} mil"
    if absn < 1_000_000_000:
        return f"{fmt_number(n / 1_000_000, decimals)} mi"
    return f"{fmt_number(n / 1_000_000_000, decimals)} bi"


FORMATTERS = {
    "int": fmt_int, "brl": fmt_brl, "pct": fmt_pct,
    "abbrev": fmt_abbrev, "number": fmt_number,
}


def get_formatter(fmt: str | None):
    """Resolve nome -> função. Default: fmt_int. Aceita callable direto."""
    if callable(fmt):
        return fmt
    return FORMATTERS.get(fmt or "int", fmt_int)


def cor_execucao(pct: float, ok: float = 100, atencao: float = 70,
                 melhor_menor: bool = False) -> str:
    """Semáforo padrão dos cards de execução: verde/âmbar/vermelho.
    melhor_menor=True inverte a leitura (ex.: custo)."""
    if melhor_menor:
        return COR_POSITIVO if pct <= ok else COR_ALERTA if pct <= atencao else COR_NEGATIVO
    return COR_POSITIVO if pct >= ok else COR_ALERTA if pct >= atencao else COR_NEGATIVO


# =============================================================================
# Tema Plotly — MESMA ASSINATURA, visual repaginado
# =============================================================================

def apply_theme(
    fig: go.Figure,
    title: str | None = None,
    show_grid: bool = False,
    *,
    height: int | None = None,
    margin: dict | None = None,
    legend: dict | None = None,
) -> go.Figure:
    base_margin = dict(l=10, r=10, t=52 if title else 10, b=10)
    if margin:
        base_margin.update(margin)

    base_legend = dict(
        orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05,
        bgcolor="rgba(255,255,255,0.9)", bordercolor="rgba(0,41,105,0.15)", borderwidth=1,
        font=dict(family=FONT_FAMILY, size=12, color=TEXT_COLOR),
    )
    if legend:
        base_legend.update(legend)

    # ── POLISH 1: cantos arredondados nas barras (defensivo p/ Plotly antigo) ──
    try:
        fig.update_traces(selector=dict(type="bar"), marker=dict(cornerradius=6))
    except (ValueError, TypeError):
        pass

    # ── POLISH 2: spline leve + halo nas linhas ──
    fig.update_traces(selector=dict(type="scatter", mode="lines+markers"),
                      line=dict(shape="spline", smoothing=0.5),
                      marker=dict(line=dict(width=1.2, color="white")))
    fig.update_traces(selector=dict(type="scatter", mode="lines"),
                      line=dict(shape="spline", smoothing=0.5))

    layout_kwargs = dict(
        margin=base_margin,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, size=12, color=TEXT_COLOR),
        colorway=PLOTLY_COLORWAY,
        legend=base_legend,
        # ── POLISH 3: hover elegante (borda navy sutil) ──
        hoverlabel=dict(
            bgcolor="white", bordercolor="rgba(0,41,105,0.22)",
            font=dict(size=12, color=TEXT_COLOR, family=FONT_FAMILY),
        ),
    )

    if title:
        layout_kwargs["title"] = dict(
            text=title, x=0.5, xanchor="center",
            font=dict(family=FONT_FAMILY, size=15, color=TITULO_COR, weight=600),
        )

    if height is not None:
        layout_kwargs["height"] = int(height)

    fig.update_layout(**layout_kwargs)

    # ── POLISH 4: grid horizontal sutil e uniforme (era os dois eixos ou nada) ──
    if show_grid:
        fig.update_xaxes(showgrid=False, zeroline=False, showline=False,
                         tickfont=dict(family=FONT_FAMILY, size=11, color=EIXO_COR))
        fig.update_yaxes(showgrid=True, gridcolor=GRID_COR, zeroline=False, showline=False,
                         tickfont=dict(family=FONT_FAMILY, size=11, color=EIXO_COR))
    else:
        fig.update_xaxes(showgrid=False, zeroline=False, showline=False,
                         tickfont=dict(family=FONT_FAMILY, size=11, color=EIXO_COR))
        fig.update_yaxes(showgrid=False, zeroline=False, showline=False,
                         tickfont=dict(family=FONT_FAMILY, size=11, color=EIXO_COR))

    return fig


def criar_gradiente(n_items: int, cor_base: str = "#0c64a3") -> list[str]:
    """INALTERADA (só o default virou o azul institucional)."""
    if n_items <= 0:
        return []
    r_base, g_base, b_base = int(cor_base[1:3], 16), int(cor_base[3:5], 16), int(cor_base[5:7], 16)
    r_claro, g_claro, b_claro = min(255, int(r_base * 1.2)), min(255, int(g_base * 1.2)), min(255, int(b_base * 1.2))
    cores, denom = [], max(n_items - 1, 1)
    for i in range(n_items):
        ratio = i / denom
        r = int(r_claro + (r_base - r_claro) * ratio)
        g = int(g_claro + (g_base - g_claro) * ratio)
        b = int(b_claro + (b_base - b_claro) * ratio)
        cores.append(f"rgb({r}, {g}, {b})")
    return cores
