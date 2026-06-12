import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np
from pathlib import Path

plt.rcParams.update({
    "figure.figsize": (8, 5),
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "font.size": 12,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# Палитра
BLUE   = "#4C72B0"
RED    = "#DD4C4C"
GREEN  = "#55A868"
GRAY   = "#888888"

OUT = Path("lessons/images")
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)

# ──────────────────────────────────────────────────────────────────────────────
# График 1. Три потока событий на временной оси
# ──────────────────────────────────────────────────────────────────────────────

T = 20.0   # длина оси времени (секунды)

# M: пуассоновский поток (λ = 1 событие/сек)
lam = 1.0
interarrivals_m = rng.exponential(1.0 / lam, size=60)
arrivals_m = np.cumsum(interarrivals_m)
arrivals_m = arrivals_m[arrivals_m < T]

# D: детерминированный поток (строго каждые 1.5 сек)
arrivals_d = np.arange(0.5, T, 1.5)

# G: батчи (bursty) — пачки по 3–5 событий через большие паузы
burst_times = np.arange(1.0, T, 4.5)
arrivals_g = []
for bt in burst_times:
    n = rng.integers(3, 6)
    jitter = rng.uniform(0.0, 0.25, size=n)
    arrivals_g.extend((bt + jitter).tolist())
arrivals_g = np.array(sorted(arrivals_g))
arrivals_g = arrivals_g[arrivals_g < T]

fig, axes = plt.subplots(3, 1, figsize=(10, 5), sharex=True)
fig.suptitle("Три типа входящих потоков", fontsize=13, fontweight="bold")

streams = [
    (arrivals_m, BLUE,  "M  — пуассоновский (случайные интервалы)"),
    (arrivals_d, GREEN, "D  — детерминированный (равные интервалы)"),
    (arrivals_g, RED,   "G  — батчи / бёрсты (нерегулярные пачки)"),
]

for ax, (times, color, label) in zip(axes, streams):
    ax.eventplot(times, lineoffsets=0.5, linelengths=0.7, linewidths=1.5, color=color)
    ax.set_xlim(0, T)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_ylabel(label, fontsize=10, rotation=0, ha="right", va="center", labelpad=4)
    ax.yaxis.set_label_coords(-0.02, 0.5)
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", alpha=0)
    ax.spines["left"].set_visible(False)

axes[-1].set_xlabel("Время (сек)")
plt.tight_layout()
plt.savefig(OUT / "lesson03_streams.png")
plt.close()
print("Сохранён: lesson03_streams.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 2. Плотности распределений интервалов
# ──────────────────────────────────────────────────────────────────────────────

x = np.linspace(0, 5, 500)

# Экспоненциальное (M): λ=1
pdf_exp = np.exp(-x)

# Логнормальное (G): медиана ~1, σ=0.7
mu_ln, sigma_ln = 0.0, 0.7
pdf_lnorm = (1 / (x * sigma_ln * np.sqrt(2 * np.pi))) * np.exp(
    -((np.log(np.maximum(x, 1e-9)) - mu_ln) ** 2) / (2 * sigma_ln ** 2)
)

fig, ax = plt.subplots(figsize=(8, 5))

ax.plot(x, pdf_exp,   color=BLUE,  lw=2.5, label="M — экспоненциальное\n(пуассоновский поток)")
ax.plot(x, pdf_lnorm, color=GREEN, lw=2.5, linestyle="--",
        label="G — логнормальное\n(произвольное распределение)")

# D: дельта-функция — вертикальная линия в точке 1
ax.axvline(x=1.0, color=RED, lw=2.5, linestyle=":",
           label="D — детерминированное\n(все интервалы = 1 сек)")
ax.annotate("δ(x−1)", xy=(1.0, 0.95), xycoords=("data", "axes fraction"),
            xytext=(1.4, 0.88), textcoords=("data", "axes fraction"),
            color=RED, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))

ax.set_xlim(0, 5)
ax.set_ylim(0, 1.1)
ax.set_xlabel("Интервал между событиями (сек)")
ax.set_ylabel("Плотность вероятности")
ax.set_title("Распределения межсобытийных интервалов", fontweight="bold")
ax.legend(loc="upper right", fontsize=10)
plt.tight_layout()
plt.savefig(OUT / "lesson03_distributions.png")
plt.close()
print("Сохранён: lesson03_distributions.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 3. Схема системы массового обслуживания
# ──────────────────────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(10, 5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 6)
ax.set_aspect("equal")
ax.axis("off")
ax.grid(False)
fig.patch.set_facecolor("white")

def arrow(ax, x0, y0, x1, y1, color=GRAY):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5,
                                mutation_scale=16))

def box(ax, x, y, w, h, color, label, sublabel=None, fontsize=11):
    rect = mpatches.FancyBboxPatch((x - w/2, y - h/2), w, h,
                                   boxstyle="round,pad=0.1",
                                   facecolor=color, edgecolor="white",
                                   alpha=0.88, zorder=3)
    ax.add_patch(rect)
    ax.text(x, y + (0.15 if sublabel else 0), label,
            ha="center", va="center", fontsize=fontsize,
            color="white", fontweight="bold", zorder=4)
    if sublabel:
        ax.text(x, y - 0.32, sublabel, ha="center", va="center",
                fontsize=9, color="white", alpha=0.9, zorder=4)

# Источник
box(ax, 1.1, 3.0, 1.6, 1.2, BLUE, "Источник", "запросы\nλ req/s")

# Стрелка источник → очередь
arrow(ax, 1.9, 3.0, 2.9, 3.0)

# Очередь
queue_x, queue_y = 3.7, 3.0
queue_w, queue_h = 1.5, 1.0
rect_q = mpatches.FancyBboxPatch((queue_x - queue_w/2, queue_y - queue_h/2),
                                  queue_w, queue_h,
                                  boxstyle="round,pad=0.05",
                                  facecolor=GREEN, edgecolor="white",
                                  alpha=0.85, zorder=3)
ax.add_patch(rect_q)
ax.text(queue_x, queue_y + 0.18, "Очередь", ha="center", va="center",
        fontsize=11, color="white", fontweight="bold", zorder=4)
ax.text(queue_x, queue_y - 0.22, "A/S/k", ha="center", va="center",
        fontsize=10, color="white", alpha=0.9, zorder=4)

# Стрелка очередь → серверы
arrow(ax, 4.45, 3.0, 5.2, 3.0)

# k серверов
server_ys = [4.2, 3.0, 1.8]
server_labels = ["Сервер 1", "Сервер 2", "Сервер k"]
for i, (sy, slabel) in enumerate(zip(server_ys, server_labels)):
    box(ax, 6.1, sy, 1.5, 0.85, RED, slabel, fontsize=10)
    arrow(ax, 5.2, 3.0, 5.35, sy)
    arrow(ax, 6.85, sy, 7.5, sy)

# Метка "k серверов"
ax.text(6.1, 5.1, "k серверов", ha="center", va="bottom",
        fontsize=10, color=RED, fontweight="bold")

# Сбор в выход
ax.plot([7.5, 8.2, 8.2, 8.2], [4.2, 4.2, 1.8, 3.0],
        color=GRAY, lw=1.5, zorder=2)
arrow(ax, 8.2, 3.0, 8.9, 3.0)

# Выход
box(ax, 9.5, 3.0, 1.0, 1.0, BLUE, "Выход", "μ req/s")

# Нотация внизу
ax.text(5.0, 0.5,
        "Нотация Кендалла:   A / S / k",
        ha="center", va="center", fontsize=12,
        color="#333333", fontstyle="italic",
        bbox=dict(facecolor="#F0F4FB", edgecolor=BLUE, boxstyle="round,pad=0.3"))

ax.set_title("Схема системы массового обслуживания", fontsize=13, fontweight="bold", pad=10)
plt.tight_layout()
plt.savefig(OUT / "lesson03_system_schema.png")
plt.close()
print("Сохранён: lesson03_system_schema.png")
