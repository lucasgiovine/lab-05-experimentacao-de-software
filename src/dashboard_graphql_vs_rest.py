import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("TkAgg")           # troque por "Qt5Agg" se não tiver Tk
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Button
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

# ── paleta ────────────────────────────────────────────────────────────────────
GQL_PC1  = "#2a78d6"
GQL_PC2  = "#7ab3ed"
REST_PC1 = "#e34948"
REST_PC2 = "#f0918f"
BG       = "#f7f7f5"
CARD_BG  = "#ffffff"
GRID_CLR = "#e8e8e4"
TEXT_PRI = "#1a1a18"
TEXT_SEC = "#52514e"
TEXT_MUT = "#898781"
ACCENT   = "#2a78d6"

# ── dados ─────────────────────────────────────────────────────────────────────
gql1 = pd.read_csv("metricas_desempenho_graphql_pc1.csv")
gql2 = pd.read_csv("metricas_desempenho_graphql_pc2.csv")
r1   = pd.read_csv("metricas_desempenho_rest_pc1.csv")
r2   = pd.read_csv("metricas_desempenho_rest_pc2.csv")

TOTAIS = dict(
    gql1_t=gql1.tempo_segundos.sum(),  gql2_t=gql2.tempo_segundos.sum(),
    r1_t  =r1.tempo_segundos.sum(),    r2_t  =r2.tempo_segundos.sum(),
    gql1_b=gql1.tamanho_bytes.sum()/1e6, gql2_b=gql2.tamanho_bytes.sum()/1e6,
    r1_b  =r1.tamanho_bytes.sum()/1e6,   r2_b  =r2.tamanho_bytes.sum()/1e6,
)
mwu_t, p_t = stats.mannwhitneyu(gql1.tempo_segundos, r1.tempo_segundos, alternative="two-sided")
mwu_b, p_b = stats.mannwhitneyu(gql1.tamanho_bytes,  r1.tamanho_bytes,  alternative="two-sided")

# ── helpers visuais ───────────────────────────────────────────────────────────
def style_ax(ax):
    ax.set_facecolor(CARD_BG)
    for sp in ax.spines.values():
        sp.set_color(GRID_CLR); sp.set_linewidth(0.8)
    ax.yaxis.grid(True, color=GRID_CLR, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TEXT_SEC, labelsize=10, pad=6)
    ax.xaxis.label.set_color(TEXT_SEC)
    ax.yaxis.label.set_color(TEXT_SEC)

def ax_title(ax, main, sub=""):
    ax.set_title(main, fontsize=11, fontweight="bold", color=TEXT_PRI,
                 pad=14, loc="left")
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes,
                fontsize=8.5, color=TEXT_MUT, va="bottom")

# ── tooltip genérico via annotation ──────────────────────────────────────────
def make_tooltip(fig, ax):
    ann = ax.annotate("", xy=(0, 0), xytext=(14, 14),
                      textcoords="offset points",
                      bbox=dict(boxstyle="round,pad=0.5", fc=CARD_BG,
                                ec=GRID_CLR, lw=1, alpha=0.97),
                      fontsize=9, color=TEXT_PRI, zorder=10,
                      arrowprops=dict(arrowstyle="->", color=TEXT_MUT, lw=0.8))
    ann.set_visible(False)
    return ann

def attach_bar_tooltip(fig, ax, bars, labels, fmt="{label}\n{val}"):
    ann = make_tooltip(fig, ax)
    def on_move(event):
        if event.inaxes != ax:
            ann.set_visible(False); fig.canvas.draw_idle(); return
        hit = False
        for bar, lbl in zip(bars, labels):
            if bar.contains(event)[0]:
                x = bar.get_x() + bar.get_width() / 2
                y = bar.get_height()
                ann.xy = (x, y)
                ann.set_text(fmt.format(label=lbl, val=y))
                ann.set_visible(True); hit = True; break
        if not hit:
            ann.set_visible(False)
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect("motion_notify_event", on_move)

def attach_scatter_tooltip(fig, ax, sc, xs, ys, labels):
    ann = make_tooltip(fig, ax)
    def on_move(event):
        if event.inaxes != ax:
            ann.set_visible(False); fig.canvas.draw_idle(); return
        cont, ind = sc.contains(event)
        if cont:
            i = ind["ind"][0]
            ann.xy = (xs[i], ys[i])
            ann.set_text(labels[i])
            ann.set_visible(True)
        else:
            ann.set_visible(False)
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect("motion_notify_event", on_move)

def attach_line_tooltip(fig, ax, line, xs, ys, labels):
    ann = make_tooltip(fig, ax)
    def on_move(event):
        if event.inaxes != ax or event.xdata is None:
            ann.set_visible(False); fig.canvas.draw_idle(); return
        dists = [abs(event.xdata - x) for x in xs]
        i = int(np.argmin(dists))
        if dists[i] < 0.6:
            ann.xy = (xs[i], ys[i])
            ann.set_text(labels[i])
            ann.set_visible(True)
        else:
            ann.set_visible(False)
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect("motion_notify_event", on_move)

def attach_box_tooltip(fig, ax, boxes, labels):
    """Tooltip em cada box de um boxplot."""
    ann = make_tooltip(fig, ax)
    def on_move(event):
        if event.inaxes != ax:
            ann.set_visible(False); fig.canvas.draw_idle(); return
        hit = False
        for box, lbl in zip(boxes, labels):
            if box.contains(event)[0]:
                path = box.get_path()
                verts = path.vertices
                ymin, ymax = verts[:, 1].min(), verts[:, 1].max()
                xmid = verts[:, 0].mean()
                ann.xy = (xmid, ymax)
                ann.set_text(lbl)
                ann.set_visible(True); hit = True; break
        if not hit:
            ann.set_visible(False)
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect("motion_notify_event", on_move)

# ══════════════════════════════════════════════════════════════════════════════
# FIGURA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(20, 13), facecolor=BG)
fig.canvas.manager.set_window_title("GraphQL vs REST — Dashboard")

# ── header ────────────────────────────────────────────────────────────────────
fig.text(0.5, 0.975, "GraphQL  vs  REST  —  Experimento Controlado",
         ha="center", fontsize=18, fontweight="bold", color=TEXT_PRI)
fig.text(0.5, 0.958, "API GitHub · 100 repositórios · 2 máquinas (PC1 e PC2)",
         ha="center", fontsize=10.5, color=TEXT_SEC)

legend_items = [
    mpatches.Patch(color=GQL_PC1,  label="GraphQL – PC1"),
    mpatches.Patch(color=GQL_PC2,  label="GraphQL – PC2"),
    mpatches.Patch(color=REST_PC1, label="REST – PC1"),
    mpatches.Patch(color=REST_PC2, label="REST – PC2"),
]
fig.legend(handles=legend_items, loc="upper right",
           bbox_to_anchor=(0.99, 0.97), ncol=4,
           fontsize=9.5, frameon=True, framealpha=0.95,
           edgecolor=GRID_CLR, facecolor=CARD_BG)

# ── área de conteúdo das abas (reservada) ─────────────────────────────────────
# Botões de aba
ax_btn_rq1 = fig.add_axes([0.03, 0.895, 0.12, 0.038])
ax_btn_rq2 = fig.add_axes([0.16, 0.895, 0.12, 0.038])

btn_rq1 = Button(ax_btn_rq1, "  RQ1 · Tempo  ",
                 color=GQL_PC1, hovercolor="#1a5db0")
btn_rq2 = Button(ax_btn_rq2, "  RQ2 · Tamanho  ",
                 color=CARD_BG, hovercolor=GRID_CLR)
for btn in (btn_rq1, btn_rq2):
    btn.label.set_fontsize(10)
    btn.label.set_fontweight("bold")
btn_rq1.label.set_color("white")
btn_rq2.label.set_color(TEXT_SEC)

# ── linha separadora ─────────────────────────────────────────────────────────
fig.add_artist(plt.Line2D([0.03, 0.97], [0.892, 0.892],
                           transform=fig.transFigure,
                           color=GRID_CLR, linewidth=1.2))

# ══════════════════════════════════════════════════════════════════════════════
# CONTEÚDO DAS ABAS
# ══════════════════════════════════════════════════════════════════════════════
content_axes = []   # rastreia todos os axes para show/hide

# ─────────────────────────────────────────────────────────────────────────────
# ABA RQ1 — Tempo
# ─────────────────────────────────────────────────────────────────────────────
gs1 = gridspec.GridSpec(
    2, 3,
    figure=fig,
    left=0.06,
    right=0.97,
    top=0.84,
    bottom=0.07,
    hspace=0.75,
    wspace=0.40
)

axes_rq1 = []

# 1-A: barras tempo total
ax1a = fig.add_subplot(gs1[0, 0]); style_ax(ax1a)
lbs  = ["GQL\nPC1", "GQL\nPC2", "REST\nPC1", "REST\nPC2"]
vs   = [TOTAIS["gql1_t"], TOTAIS["gql2_t"], TOTAIS["r1_t"], TOTAIS["r2_t"]]
cols = [GQL_PC1, GQL_PC2, REST_PC1, REST_PC2]
bars1a = ax1a.bar(lbs, vs, color=cols, width=0.52, zorder=3,
                  edgecolor="white", linewidth=0.6)
for b, v in zip(bars1a, vs):
    ax1a.text(b.get_x()+b.get_width()/2, v + max(vs)*0.015,
              f"{v:.1f}s", ha="center", va="bottom",
              fontsize=9, fontweight="bold", color=TEXT_PRI)
ax1a.set_ylabel("Tempo acumulado (s)", fontsize=10, labelpad=8)
ax1a.tick_params(axis="x", length=0, labelsize=10)
ax_title(ax1a, "Tempo total acumulado",
         "soma de todas as requisições por abordagem e máquina")
attach_bar_tooltip(fig, ax1a, bars1a, lbs,
    fmt="{label}\n{val:.1f} segundos")
axes_rq1.append(ax1a)

# 1-B: boxplot tempo por requisição
ax1b = fig.add_subplot(gs1[0, 1]); style_ax(ax1b)
data_bx = [gql1.tempo_segundos, gql2.tempo_segundos,
           r1.tempo_segundos,   r2.tempo_segundos]
bp1 = ax1b.boxplot(data_bx, patch_artist=True, widths=0.48,
                   medianprops=dict(color="white", linewidth=2.2),
                   whiskerprops=dict(color=TEXT_SEC, linewidth=1),
                   capprops=dict(color=TEXT_SEC, linewidth=1),
                   flierprops=dict(marker="o", markersize=3.5,
                                   alpha=0.45, markeredgewidth=0))
for patch, cor in zip(bp1["boxes"], cols):
    patch.set_facecolor(cor)
ax1b.set_xticklabels(["GQL\nPC1","GQL\nPC2","REST\nPC1","REST\nPC2"],
                     fontsize=10)
ax1b.set_ylabel("Tempo por requisição (s)", fontsize=10, labelpad=8)
ax1b.tick_params(axis="x", length=0)
ax_title(ax1b, "Distribuição por requisição",
         "cada box = distribuição de uma chamada HTTP individual")
box_lbls = []
for i, (ser, nm) in enumerate(zip(data_bx, ["GQL PC1","GQL PC2","REST PC1","REST PC2"])):
    box_lbls.append(f"{nm}\nMed: {ser.median():.2f}s\n"
                    f"Min: {ser.min():.2f}s  Max: {ser.max():.2f}s")
attach_box_tooltip(fig, ax1b, bp1["boxes"], box_lbls)
axes_rq1.append(ax1b)

# 1-C: Mann-Whitney + razão (tabela visual)
ax1c = fig.add_subplot(gs1[0, 2])
ax1c.set_facecolor("#eef4fc")
for sp in ax1c.spines.values():
    sp.set_color("#b5cef0"); sp.set_linewidth(1)
ax1c.set_xticks([]); ax1c.set_yticks([])
ax_title(ax1c, "Resultado estatístico · RQ1",
         "teste Mann-Whitney U · α = 0,05")
razao = TOTAIS["r1_t"] / TOTAIS["gql1_t"]
linhas = [
    ("Teste",              "Mann-Whitney U",        TEXT_SEC),
    ("Estatística U",      f"{mwu_t:,.0f}",         TEXT_PRI),
    ("p-value",            f"{p_t:.2e}",            TEXT_PRI),
    ("Significativo?",     "Sim  (p < 0,05)" if p_t < 0.05 else "Não",
                           "#008300" if p_t < 0.05 else REST_PC1),
    ("",                   "",                      TEXT_MUT),
    ("Razão de tempo",     f"REST {razao:.0f}× mais lento",  ACCENT),
    ("GraphQL PC1",        f"{TOTAIS['gql1_t']:.1f}s  (22 req.)", GQL_PC1),
    ("REST PC1",           f"{TOTAIS['r1_t']:.0f}s  (4.292 req.)", REST_PC1),
    ("GraphQL PC2",        f"{TOTAIS['gql2_t']:.1f}s  (22 req.)", GQL_PC2),
    ("REST PC2",           f"{TOTAIS['r2_t']:.0f}s  (4.174 req.)", REST_PC2),
]
for i, (lbl, val, cor) in enumerate(linhas):
    y = 0.89 - i * 0.088
    ax1c.text(0.04, y, lbl,  transform=ax1c.transAxes,
              fontsize=9, color=TEXT_MUT, va="top")
    ax1c.text(0.96, y, val,  transform=ax1c.transAxes,
              fontsize=9, color=cor, va="top", ha="right", fontweight="bold")
    if i < len(linhas) - 1:
       ax1c.plot(
    [0.02, 0.98],
    [y - 0.025, y - 0.025],
    color=GRID_CLR,
    linewidth=0.6,
    transform=ax1c.transAxes
)
axes_rq1.append(ax1c)

# 1-D: evolução linha das 22 queries GraphQL
ax1d = fig.add_subplot(gs1[1, 0]); style_ax(ax1d)
idx = np.arange(1, 23)
l1, = ax1d.plot(idx, gql1.tempo_segundos.values, "o-",
                color=GQL_PC1, lw=1.8, ms=5.5, label="PC1", zorder=4)
l2, = ax1d.plot(idx, gql2.tempo_segundos.values, "s--",
                color=GQL_PC2, lw=1.8, ms=5.5, label="PC2", zorder=4)
ax1d.axhline(gql1.tempo_segundos.mean(), color=GQL_PC1,
             lw=0.9, ls=":", alpha=0.7)
ax1d.axhline(gql2.tempo_segundos.mean(), color=GQL_PC2,
             lw=0.9, ls=":", alpha=0.7)
ax1d.set_xlabel("Nº da query GraphQL", fontsize=10, labelpad=8)
ax1d.set_ylabel("Tempo (s)", fontsize=10, labelpad=8)
ax1d.legend(fontsize=9, frameon=False)
ax_title(ax1d, "Evolução das 22 queries GraphQL",
         f"PC1 média {gql1.tempo_segundos.mean():.2f}s  ·  PC2 média {gql2.tempo_segundos.mean():.2f}s")
xs1 = list(idx); ys1g1 = list(gql1.tempo_segundos.values)
ys1g2 = list(gql2.tempo_segundos.values)
lbls_pc1 = [f"Query #{i}\nPC1: {v:.3f}s" for i,v in zip(idx, ys1g1)]
lbls_pc2 = [f"Query #{i}\nPC2: {v:.3f}s" for i,v in zip(idx, ys1g2)]
attach_scatter_tooltip(fig, ax1d,
    ax1d.scatter(xs1, ys1g1, s=0, color=GQL_PC1),
    xs1, ys1g1, lbls_pc1)
attach_scatter_tooltip(fig, ax1d,
    ax1d.scatter(xs1, ys1g2, s=0, color=GQL_PC2),
    xs1, ys1g2, lbls_pc2)
attach_line_tooltip(fig, ax1d, l1, xs1, ys1g1, lbls_pc1)
axes_rq1.append(ax1d)

# 1-E: REST breakdown por tipo (PC1 vs PC2)
ax1e = fig.add_subplot(gs1[1, 1]); style_ax(ax1e)
tipos = ["get_reviews", "get_prs", "search_repos"]
r1v = [r1.groupby("tipo_req").tempo_segundos.sum().get(t,0) for t in tipos]
r2v = [r2.groupby("tipo_req").tempo_segundos.sum().get(t,0) for t in tipos]
x  = np.arange(len(tipos)); w = 0.38
br1 = ax1e.bar(x-w/2, r1v, w, color=REST_PC1, zorder=3,
               edgecolor="white", lw=0.5, label="PC1")
br2 = ax1e.bar(x+w/2, r2v, w, color=REST_PC2, zorder=3,
               edgecolor="white", lw=0.5, label="PC2")
for brs, vals in [(br1, r1v), (br2, r2v)]:
    for b, v in zip(brs, vals):
        ax1e.text(b.get_x()+b.get_width()/2, v + max(max(r1v),max(r2v))*0.015,
                  f"{v:.0f}s", ha="center", va="bottom", fontsize=8.5, color=TEXT_PRI)
ax1e.set_xticks(x)
ax1e.set_xticklabels(["get_reviews","get_prs","search_repos"], fontsize=9.5)
ax1e.set_ylabel("Tempo acumulado (s)", fontsize=10, labelpad=8)
ax1e.legend(fontsize=9, frameon=False)
ax1e.tick_params(axis="x", length=0)
ax_title(ax1e, "REST — tempo por tipo de requisição",
         "custo de cada etapa da coleta · comparação entre máquinas")
tipo_lbs1 = [f"{t}\nPC1: {v:.1f}s" for t,v in zip(tipos, r1v)]
tipo_lbs2 = [f"{t}\nPC2: {v:.1f}s" for t,v in zip(tipos, r2v)]
attach_bar_tooltip(fig, ax1e, br1, tipo_lbs1, fmt="{label}")
attach_bar_tooltip(fig, ax1e, br2, tipo_lbs2, fmt="{label}")
axes_rq1.append(ax1e)

# 1-F: Δ tempo entre PCs (variabilidade)
ax1f = fig.add_subplot(gs1[1, 2]); style_ax(ax1f)
diff_t = gql2.tempo_segundos.values - gql1.tempo_segundos.values
cols_d = [GQL_PC2 if d >= 0 else GQL_PC1 for d in diff_t]
br_d = ax1f.bar(idx, diff_t, color=cols_d, width=0.7, zorder=3,
                edgecolor="white", lw=0.4)
ax1f.axhline(0, color=TEXT_SEC, lw=0.9)
ax1f.set_xlabel("Nº da query GraphQL", fontsize=10, labelpad=8)
ax1f.set_ylabel("Δ tempo  PC2 − PC1  (s)", fontsize=10, labelpad=8)
ax_title(ax1f, "Variabilidade entre máquinas · GraphQL",
         "azul escuro = PC2 mais lento  ·  azul claro = PC2 mais rápido")
diff_lbs = [f"Query #{i}\nPC1: {a:.3f}s\nPC2: {b:.3f}s\nΔ: {d:+.3f}s"
            for i,a,b,d in zip(idx, gql1.tempo_segundos,
                                gql2.tempo_segundos, diff_t)]
attach_bar_tooltip(fig, ax1f, br_d, diff_lbs, fmt="{label}")
axes_rq1.append(ax1f)

# ─────────────────────────────────────────────────────────────────────────────
# ABA RQ2 — Tamanho
# ─────────────────────────────────────────────────────────────────────────────
gs2 = gridspec.GridSpec(
    2, 3,
    figure=fig,
    left=0.06,
    right=0.97,
    top=0.84,
    bottom=0.07,
    hspace=0.75,
    wspace=0.40
)

axes_rq2 = []

# 2-A: barras payload total
ax2a = fig.add_subplot(gs2[0, 0]); style_ax(ax2a)
vs_b = [TOTAIS["gql1_b"], TOTAIS["gql2_b"], TOTAIS["r1_b"], TOTAIS["r2_b"]]
br2a = ax2a.bar(lbs, vs_b, color=cols, width=0.52, zorder=3,
                edgecolor="white", lw=0.6)
for b, v in zip(br2a, vs_b):
    ax2a.text(b.get_x()+b.get_width()/2, v + max(vs_b)*0.015,
              f"{v:.1f} MB", ha="center", va="bottom",
              fontsize=9, fontweight="bold", color=TEXT_PRI)
ax2a.set_ylabel("Payload total (MB)", fontsize=10, labelpad=8)
ax2a.tick_params(axis="x", length=0)
ax_title(ax2a, "Payload total acumulado",
         "soma de todos os bytes transferidos")
attach_bar_tooltip(fig, ax2a, br2a, lbs,
    fmt="{label}\n{val:.2f} MB")
axes_rq2.append(ax2a)


# 2-B: boxplot tamanho por requisição
ax2b = fig.add_subplot(gs2[0, 1])
style_ax(ax2b)
data_bx2 = [
    gql1.tamanho_bytes / 1024,
    gql2.tamanho_bytes / 1024,
    r1.tamanho_bytes / 1024,
    r2.tamanho_bytes / 1024
]
labels = ["GQL PC1", "GQL PC2", "REST PC1", "REST PC2"]
means = [np.mean(s) for s in data_bx2]
ax2b.set_ylim(0, 200)
bars = ax2b.bar(labels, means, color=cols)
for bar in bars:
    height = bar.get_height()
    ax2b.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:.1f} KB",
        ha="center",
        va="bottom",
        fontsize=9
    )
ax_title(
    ax2b,
    "Tamanho médio por requisição",
    "Comparação entre GraphQL e REST"
)
ax2b.set_ylabel("Tamanho médio (KB)", fontsize=10, labelpad=8)
ax2b.tick_params(axis="x", length=0)
axes_rq2.append(ax2b)

# 2-C: tabela estatística RQ2
ax2c = fig.add_subplot(gs2[0, 2])
ax2c.set_facecolor("#eef4fc")
for sp in ax2c.spines.values():
    sp.set_color("#b5cef0"); sp.set_linewidth(1)
ax2c.set_xticks([]); ax2c.set_yticks([])
ax_title(ax2c, "Resultado estatístico · RQ2",
         "teste Mann-Whitney U · α = 0,05")
razao_b = TOTAIS["r1_b"] / TOTAIS["gql1_b"]
linhas2 = [
    ("Teste",              "Mann-Whitney U",         TEXT_SEC),
    ("Estatística U",      f"{mwu_b:,.0f}",          TEXT_PRI),
    ("p-value",            f"{p_b:.2e}",             TEXT_PRI),
    ("Significativo?",     "Sim  (p < 0,05)" if p_b < 0.05 else "Não",
                           "#008300" if p_b < 0.05 else REST_PC1),
    ("",                   "",                       TEXT_MUT),
    ("Razão de payload",   f"REST {razao_b:.0f}× maior", ACCENT),
    ("GraphQL PC1",        f"{TOTAIS['gql1_b']:.2f} MB  (~73,8 KB/req)", GQL_PC1),
    ("REST PC1",           f"{TOTAIS['r1_b']:.0f} MB  (~42 KB/req)",  REST_PC1),
    ("GraphQL PC2",        f"{TOTAIS['gql2_b']:.2f} MB  (~73,9 KB/req)", GQL_PC2),
    ("REST PC2",           f"{TOTAIS['r2_b']:.0f} MB  (~43 KB/req)",  REST_PC2),
]
for i, (lbl, val, cor) in enumerate(linhas2):
    y = 0.89 - i * 0.088
    ax2c.text(0.04, y, lbl,  transform=ax2c.transAxes,
              fontsize=9, color=TEXT_MUT, va="top")
    ax2c.text(0.96, y, val,  transform=ax2c.transAxes,
              fontsize=9, color=cor, va="top", ha="right", fontweight="bold")
    if i < len(linhas2)-1:
        ax2c.plot(
    [0.02, 0.98],
    [y - 0.025, y - 0.025],
    color=GRID_CLR,
    linewidth=0.6,
    transform=ax2c.transAxes
)
axes_rq2.append(ax2c)

# 2-D: scatter tempo × tamanho (GraphQL PC1 e PC2)
ax2d = fig.add_subplot(gs2[1, 0]); style_ax(ax2d)
sc_d1 = ax2d.scatter(gql1.tempo_segundos, gql1.tamanho_bytes/1024,
                     color=GQL_PC1, s=60, zorder=4, label="GQL PC1",
                     edgecolors="white", linewidths=0.6)
sc_d2 = ax2d.scatter(gql2.tempo_segundos, gql2.tamanho_bytes/1024,
                     color=GQL_PC2, s=60, zorder=4, label="GQL PC2",
                     edgecolors="white", linewidths=0.6, marker="^")
ax2d.set_xlabel("Tempo por requisição (s)", fontsize=10, labelpad=8)
ax2d.set_ylabel("Tamanho por requisição (KB)", fontsize=10, labelpad=8)
ax2d.legend(fontsize=9, frameon=False)
ax_title(ax2d, "Tempo × Tamanho · GraphQL",
         "cada ponto = 1 query — comparação PC1 vs PC2")
xs_d1 = list(gql1.tempo_segundos); ys_d1 = list(gql1.tamanho_bytes/1024)
xs_d2 = list(gql2.tempo_segundos); ys_d2 = list(gql2.tamanho_bytes/1024)
lbls_d1 = [f"GQL PC1 · query #{i+1}\nTempo: {t:.3f}s\nTamanho: {s:.1f} KB"
           for i,(t,s) in enumerate(zip(xs_d1,ys_d1))]
lbls_d2 = [f"GQL PC2 · query #{i+1}\nTempo: {t:.3f}s\nTamanho: {s:.1f} KB"
           for i,(t,s) in enumerate(zip(xs_d2,ys_d2))]
attach_scatter_tooltip(fig, ax2d, sc_d1, xs_d1, ys_d1, lbls_d1)
attach_scatter_tooltip(fig, ax2d, sc_d2, xs_d2, ys_d2, lbls_d2)
axes_rq2.append(ax2d)

# 2-E: REST breakdown tamanho por tipo
ax2e = fig.add_subplot(gs2[1, 1]); style_ax(ax2e)
r1b_tipos = [r1.groupby("tipo_req").tamanho_bytes.sum().get(t,0)/1e6 for t in tipos]
r2b_tipos = [r2.groupby("tipo_req").tamanho_bytes.sum().get(t,0)/1e6 for t in tipos]
br2e1 = ax2e.bar(x-w/2, r1b_tipos, w, color=REST_PC1, zorder=3,
                 edgecolor="white", lw=0.5, label="PC1")
br2e2 = ax2e.bar(x+w/2, r2b_tipos, w, color=REST_PC2, zorder=3,
                 edgecolor="white", lw=0.5, label="PC2")
for brs, vals in [(br2e1, r1b_tipos), (br2e2, r2b_tipos)]:
    for b, v in zip(brs, vals):
        ax2e.text(b.get_x()+b.get_width()/2,
                  v + max(max(r1b_tipos),max(r2b_tipos))*0.015,
                  f"{v:.1f} MB", ha="center", va="bottom",
                  fontsize=8.5, color=TEXT_PRI)
ax2e.set_xticks(x)
ax2e.set_xticklabels(["get_reviews","get_prs","search_repos"], fontsize=9.5)
ax2e.set_ylabel("Payload acumulado (MB)", fontsize=10, labelpad=8)
ax2e.legend(fontsize=9, frameon=False)
ax2e.tick_params(axis="x", length=0)
ax_title(ax2e, "REST — payload por tipo de requisição",
         "volume de dados transferidos por categoria")
tlbs1 = [f"{t}\nPC1: {v:.2f} MB" for t,v in zip(tipos,r1b_tipos)]
tlbs2 = [f"{t}\nPC2: {v:.2f} MB" for t,v in zip(tipos,r2b_tipos)]
attach_bar_tooltip(fig, ax2e, br2e1, tlbs1, fmt="{label}")
attach_bar_tooltip(fig, ax2e, br2e2, tlbs2, fmt="{label}")
axes_rq2.append(ax2e)

# 2-F: Δ payload entre PCs
ax2f = fig.add_subplot(gs2[1, 2]); style_ax(ax2f)
diff_b = (gql2.tamanho_bytes.values - gql1.tamanho_bytes.values) / 1024
cols_db = [GQL_PC2 if d >= 0 else GQL_PC1 for d in diff_b]
br2f = ax2f.bar(idx, diff_b, color=cols_db, width=0.7, zorder=3,
                edgecolor="white", lw=0.4)
ax2f.axhline(0, color=TEXT_SEC, lw=0.9)
ax2f.set_xlabel("Nº da query GraphQL", fontsize=10, labelpad=8)
ax2f.set_ylabel("Δ tamanho  PC2 − PC1  (KB)", fontsize=10, labelpad=8)
ax_title(ax2f, "Variabilidade de payload entre máquinas",
         "diferença de bytes por query · azul escuro = PC2 maior")
diff_b_lbs = [f"Query #{i}\nPC1: {a/1024:.1f} KB\nPC2: {b/1024:.1f} KB\nΔ: {d:+.1f} KB"
              for i,a,b,d in zip(idx, gql1.tamanho_bytes,
                                  gql2.tamanho_bytes, diff_b)]
attach_bar_tooltip(fig, ax2f, br2f, diff_b_lbs, fmt="{label}")
axes_rq2.append(ax2f)

# ══════════════════════════════════════════════════════════════════════════════
# LÓGICA DAS ABAS
# ══════════════════════════════════════════════════════════════════════════════
def set_tab(tab):

    for ax in axes_rq1:
        ax.set_visible(tab == 1)

    for ax in axes_rq2:
        ax.set_visible(tab == 2)

    ax_btn_rq1.spines['bottom'].set_linewidth(4)
    ax_btn_rq2.spines['bottom'].set_linewidth(4)

    if tab == 1:
        ax_btn_rq1.spines['bottom'].set_color(GQL_PC1)
        ax_btn_rq2.spines['bottom'].set_color(CARD_BG)
    else:
        ax_btn_rq2.spines['bottom'].set_color(REST_PC1)
        ax_btn_rq1.spines['bottom'].set_color(CARD_BG)

    fig.canvas.draw_idle()
    
set_tab(1)   # começa na RQ1

btn_rq1.on_clicked(lambda e: set_tab(1))
btn_rq2.on_clicked(lambda e: set_tab(2))

# ── rodapé ────────────────────────────────────────────────────────────────────
fig.text(0.5, 0.012,
         "LAB05 · PUC Minas · Laboratório de Experimentação de Software · ",
         ha="center", fontsize=8.5, color=TEXT_MUT)


plt.show()
PYEOF