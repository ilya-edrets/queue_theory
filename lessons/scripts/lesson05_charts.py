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
BLUE   = "#4C72B0"
RED    = "#DD4C4C"
GREEN  = "#55A868"
GRAY   = "#888888"

OUT = Path("lessons/images")
OUT.mkdir(parents=True, exist_ok=True)


def wq_over_es(rho, cs2):
    """W_q в единицах E[S] по формуле Поллачека — Хинчина."""
    return (rho / (1.0 - rho)) * (1.0 + cs2) / 2.0


# ──────────────────────────────────────────────────────────────────────────────
# График 1. «Хоккейная клюшка»: W_q (в единицах E[S]) от ρ для разных C²
# ──────────────────────────────────────────────────────────────────────────────

rho = np.linspace(0.01, 0.985, 500)

curves = [
    (0.0,  GREEN, "C² = 0 (D — детерминированное)"),
    (1.0,  BLUE,  "C² = 1 (M — экспоненциальное)"),
    (4.0,  "#E08A1E", "C² = 4 (умеренный разброс)"),
    (10.0, RED,   "C² = 10 (тяжёлый хвост)"),
]

fig, ax = plt.subplots(figsize=(9, 5.5))

for cs2, color, label in curves:
    ax.plot(rho, wq_over_es(rho, cs2), color=color, lw=2.5, label=label)

# Вертикальная асимптота ρ = 1
ax.axvline(x=1.0, color=GRAY, lw=1.5, linestyle="--")
ax.text(1.0, 18.5, " ρ → 1", color=GRAY, fontsize=11, va="top", ha="left")

# Зоны: комфорт / риск / ад
ax.axvspan(0.0, 0.70, color=GREEN, alpha=0.07)
ax.axvspan(0.70, 0.85, color="#E08A1E", alpha=0.07)
ax.axvspan(0.85, 1.0, color=RED, alpha=0.08)

ax.text(0.35, 19.3, "комфорт\n60–80 %", color=GREEN, fontsize=10,
        ha="center", va="top", fontweight="bold")
ax.text(0.775, 19.3, "риск", color="#B5710F", fontsize=10,
        ha="center", va="top", fontweight="bold")
ax.text(0.93, 19.3, "ад", color=RED, fontsize=10,
        ha="center", va="top", fontweight="bold")

ax.set_xlim(0, 1.05)
ax.set_ylim(0, 20)
ax.set_xlabel("Утилизация ρ")
ax.set_ylabel("Время ожидания $W_q$ (в единицах $E[S]$)")
ax.set_title("Время ожидания взрывается при $\\rho \\to 1$\n(формула Поллачека — Хинчина)",
             fontweight="bold")
ax.legend(loc="center left", fontsize=10, framealpha=0.9)
plt.tight_layout()
plt.savefig(OUT / "lesson05_hockey_stick.png")
plt.close()
print("Сохранён: lesson05_hockey_stick.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 2. «Цена последних процентов»: рост W_q при ρ = 0.5 → 0.9 → 0.95 → 0.99
# ──────────────────────────────────────────────────────────────────────────────

rhos = [0.5, 0.9, 0.95, 0.99]
# Берём M/M/1 (C² = 1): W_q / E[S] = ρ / (1 - ρ)
vals = [r / (1.0 - r) for r in rhos]
labels = [f"ρ = {r}" for r in rhos]

fig, ax = plt.subplots(figsize=(8, 5))
colors = [GREEN, "#E08A1E", RED, "#8B1A1A"]
bars = ax.bar(labels, vals, color=colors, alpha=0.9, width=0.6)

for b, v, r in zip(bars, vals, rhos):
    ax.text(b.get_x() + b.get_width() / 2, v + 1.5,
            f"{v:.0f}·E[S]", ha="center", va="bottom",
            fontsize=11, fontweight="bold")

# Аннотация: во сколько раз растёт при шагах
base = vals[0]
ax.annotate(f"×{vals[1]/vals[0]:.0f}", xy=(1, vals[1]), xytext=(0.5, vals[1] + 8),
            fontsize=11, color=GRAY, ha="center")
ax.annotate(f"×{vals[3]/vals[2]:.0f} к предыдущему",
            xy=(3, vals[3]), xytext=(2.1, vals[3] - 12),
            fontsize=10, color="#8B1A1A", ha="center",
            arrowprops=dict(arrowstyle="->", color="#8B1A1A", lw=1.2))

ax.set_ylim(0, 115)
ax.set_ylabel("Время ожидания $W_q$ (в единицах $E[S]$)")
ax.set_title("Цена последних процентов утилизации\n(M/M/1, C² = 1)", fontweight="bold")
ax.grid(axis="x", alpha=0)
plt.tight_layout()
plt.savefig(OUT / "lesson05_price_of_load.png")
plt.close()
print("Сохранён: lesson05_price_of_load.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 3. Пример: смесь 1мс/100мс vs все по 50мс (одинаковая ρ)
# ──────────────────────────────────────────────────────────────────────────────

# Смесь 50/50: половина запросов по 1 мс, половина по 100 мс.
# E[S] = 50.5 мс. Подберём λ так, чтобы ρ было одинаковым в обоих случаях.
# Для честного сравнения зафиксируем ρ = 0.8 и одинаковое E[S] обеими системами
# нельзя (E[S] разные). Поэтому фиксируем λ и сравниваем при ОДНОЙ ρ.
# Берём ρ = 0.8 для каждой системы (одинаковая средняя загрузка).

rho_ex = 0.8

# Система A: смесь 1 мс и 100 мс (50/50)
p = 0.5
ES_a = p * 1 + (1 - p) * 100          # = 50.5 мс
ES2_a = p * 1**2 + (1 - p) * 100**2   # = 5000.5 мс²
cs2_a = ES2_a / ES_a**2 - 1
Wq_a = (rho_ex / (1 - rho_ex)) * (ES_a * (1 + cs2_a) / 2)

# Система B: все запросы по 50 мс (детерминированные)
ES_b = 50.0
cs2_b = 0.0
Wq_b = (rho_ex / (1 - rho_ex)) * (ES_b * (1 + cs2_b) / 2)

names = ["Смесь\n1 мс и 100 мс\n(C² ≈ {:.2f})".format(cs2_a),
         "Все по 50 мс\n(C² = 0)"]
wq_vals = [Wq_a, Wq_b]

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(names, wq_vals, color=[RED, GREEN], alpha=0.9, width=0.55)

for b, v in zip(bars, wq_vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 30,
            f"{v:.0f} мс", ha="center", va="bottom",
            fontsize=13, fontweight="bold")

ratio = Wq_a / Wq_b
ax.annotate(f"в {ratio:.1f} раза\nдольше ожидание",
            xy=(0, Wq_a), xytext=(0.55, Wq_a * 0.7),
            fontsize=11, color=RED, ha="center", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.4))

ax.set_ylim(0, Wq_a * 1.25)
ax.set_ylabel("Среднее ожидание в очереди $W_q$ (мс)")
ax.set_title("Одинаковая загрузка ρ = 0.8, разный разброс размеров задач",
             fontweight="bold")
ax.grid(axis="x", alpha=0)
plt.tight_layout()
plt.savefig(OUT / "lesson05_variability.png")
plt.close()
print("Сохранён: lesson05_variability.png")

# Печать чисел для текста урока
print("\n--- Числа для урока ---")
print(f"Смесь: E[S]={ES_a} мс, E[S^2]={ES2_a} мс^2, C^2={cs2_a:.3f}, Wq={Wq_a:.1f} мс")
print(f"Детерм.: E[S]={ES_b} мс, C^2={cs2_b}, Wq={Wq_b:.1f} мс")
print(f"Отношение Wq: {ratio:.2f}")
print(f"M/M/1 vs M/D/1 множитель вариативности: {(1+1)/2} vs {(1+0)/2}")
