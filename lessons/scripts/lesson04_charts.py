import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
BLUE  = "#4C72B0"
RED   = "#DD4C4C"
GREEN = "#55A868"
GRAY  = "#888888"

OUT = Path("lessons/images")
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)

# ──────────────────────────────────────────────────────────────────────────────
# График 1. CCDF (хвост) P(X > x) экспоненты и Парето в log-log осях
# ──────────────────────────────────────────────────────────────────────────────
# Экспонента и Парето подобраны так, чтобы иметь одинаковое среднее = 1.
#   Экспонента: mean = 1/λ  → λ = 1
#   Парето:     mean = α·xm/(α−1) = 1, берём α = 2, xm = 0.5
x = np.logspace(np.log10(0.5), np.log10(500), 600)

lam = 1.0
ccdf_exp = np.exp(-lam * x)            # P(X > x) для экспоненты

alpha, xm = 2.0, 0.5
ccdf_pareto = (xm / x) ** alpha        # P(X > x) для Парето, x >= xm

fig, ax = plt.subplots(figsize=(8, 5))
ax.loglog(x, ccdf_exp, color=BLUE, lw=2.5,
          label="Экспонента (лёгкий хвост)")
ax.loglog(x, ccdf_pareto, color=RED, lw=2.5,
          label="Парето (тяжёлый хвост)")

ax.annotate("экспонента «ныряет»\n(хвост обрывается)",
            xy=(8, np.exp(-8)), xytext=(2.0, 1e-5),
            color=BLUE, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.3))
ax.annotate("Парето — прямая линия\n(хвост тянется)",
            xy=(120, (xm / 120) ** alpha), xytext=(6, 3e-3),
            color=RED, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))

ax.set_xlim(0.5, 500)
ax.set_ylim(1e-7, 1.2)
ax.set_xlabel("Размер запроса x (лог-шкала)")
ax.set_ylabel("P(X > x) — доля запросов крупнее x (лог-шкала)")
ax.set_title("Хвост распределения: экспонента vs Парето", fontweight="bold")
ax.legend(loc="lower left", fontsize=11)
ax.grid(True, which="both", alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "lesson04_ccdf_loglog.png")
plt.close()
print("Сохранён: lesson04_ccdf_loglog.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 2. Условное ожидание остатка E[X − t | X > t] от прошедшего времени t
# ──────────────────────────────────────────────────────────────────────────────
# Все три распределения нормированы на среднее = 1.
t = np.linspace(0, 4, 500)

# Экспонента (λ=1): остаток всегда = 1/λ = 1 (отсутствие памяти)
mean_residual_exp = np.ones_like(t)

# Парето (α=2, xm=0.5): при x>=xm  E[X−t | X>t] = t/(α−1) = t  (растёт!)
# Для t < xm условный остаток = E[X] − t = 1 − t (ещё не вошли в хвост)
mean_residual_pareto = np.where(t < xm, 1.0 - t, t / (alpha - 1.0))

# Равномерное на [0, 2] (среднее = 1): E[X−t | X>t] = (2 − t)/2 (убывает к 0)
b = 2.0
mean_residual_uniform = np.where(t < b, (b - t) / 2.0, np.nan)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(t, mean_residual_exp, color=BLUE, lw=2.5,
        label="Экспонента — без памяти (горизонталь)")
ax.plot(t, mean_residual_pareto, color=RED, lw=2.5,
        label="Парето — остаток растёт")
ax.plot(t, mean_residual_uniform, color=GREEN, lw=2.5, linestyle="--",
        label="Равномерное — остаток убывает")

ax.axhline(1.0, color=GRAY, lw=1.0, linestyle=":", alpha=0.7)

ax.annotate("чем дольше ждём —\nтем больше ждать",
            xy=(3.2, 3.2 / (alpha - 1.0)), xytext=(1.4, 2.6),
            color=RED, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))
ax.annotate("«скоро закончится»",
            xy=(1.6, (b - 1.6) / 2.0), xytext=(2.0, 0.55),
            color=GREEN, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.3))

ax.set_xlim(0, 4)
ax.set_ylim(0, 3.5)
ax.set_xlabel("Уже прошло времени t (в долях среднего)")
ax.set_ylabel("Ожидаемый остаток  E[X − t | X > t]")
ax.set_title("«Сколько ещё ждать», если запрос уже идёт время t",
             fontweight="bold")
ax.legend(loc="upper left", fontsize=10)
plt.tight_layout()
plt.savefig(OUT / "lesson04_residual.png")
plt.close()
print("Сохранён: lesson04_residual.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 3. Иллюстрация 80/20 — кривая Лоренца нагрузки
# ──────────────────────────────────────────────────────────────────────────────
# Генерим размеры задач из Парето (тяжёлый хвост) и из экспоненты для контраста.
N = 50_000

sizes_pareto = (rng.pareto(1.2, size=N) + 1) * 1.0   # тяжёлый хвост
sizes_exp = rng.exponential(1.0, size=N)             # лёгкий хвост


def lorenz(sizes):
    s = np.sort(sizes)                # по возрастанию
    cum = np.cumsum(s)
    cum = cum / cum[-1]
    frac_requests = np.arange(1, len(s) + 1) / len(s)
    # доля нагрузки от самых ТЯЖЁЛЫХ: разворачиваем
    frac_load_from_heaviest = 1.0 - np.concatenate(([0.0], cum[:-1]))
    frac_heaviest = 1.0 - np.concatenate(([0.0], frac_requests[:-1]))
    return frac_heaviest[::-1], frac_load_from_heaviest[::-1]


fh_p, fl_p = lorenz(sizes_pareto)
fh_e, fl_e = lorenz(sizes_exp)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(fh_p * 100, fl_p * 100, color=RED, lw=2.5,
        label="Парето (тяжёлый хвост)")
ax.plot(fh_e * 100, fl_e * 100, color=BLUE, lw=2.5,
        label="Экспонента (лёгкий хвост)")
ax.plot([0, 100], [0, 100], color=GRAY, lw=1.2, linestyle=":",
        label="Равномерно (все задачи одинаковы)")

# Отметим точку 20% → ~80% для Парето
idx20 = np.searchsorted(fh_p, 0.20)
load20 = fl_p[idx20] * 100
ax.scatter([20], [load20], color=RED, zorder=5, s=40)
ax.annotate(f"20% самых тяжёлых задач\nдают ~{load20:.0f}% нагрузки",
            xy=(20, load20), xytext=(33, 55),
            color=RED, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))
ax.plot([20, 20], [0, load20], color=RED, lw=1.0, linestyle="--", alpha=0.5)
ax.plot([0, 20], [load20, load20], color=RED, lw=1.0, linestyle="--", alpha=0.5)

ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_xlabel("Доля самых тяжёлых запросов, %")
ax.set_ylabel("Доля суммарной нагрузки, %")
ax.set_title("Принцип 80/20: немного запросов создают большую часть нагрузки",
             fontweight="bold")
ax.legend(loc="lower right", fontsize=10)
plt.tight_layout()
plt.savefig(OUT / "lesson04_pareto_8020.png")
plt.close()
print("Сохранён: lesson04_pareto_8020.png")
