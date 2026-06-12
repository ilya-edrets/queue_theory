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

# ──────────────────────────────────────────────────────────────────────────────
# График 1. Правило квадратного корня (square-root staffing)
#   Левая панель:  сколько серверов k нужно при нагрузке R
#       — «наивное удвоение»: фиксированный запас в % → k = R * (1 + m)
#       — square-root:        k = R + c*sqrt(R)
#   Правая панель: допустимая утилизация ρ = R/k от масштаба R (растёт)
# ──────────────────────────────────────────────────────────────────────────────
R = np.linspace(1, 200, 400)         # предложенная нагрузка (offered load)
c = 1.5                              # коэффициент качества (чем больше — тем меньше очередь)
margin = 0.25                        # «наивный» фиксированный запас 25%

k_naive = R * (1.0 + margin)         # наивно: всегда +25% серверов
k_sqrt  = R + c * np.sqrt(R)         # square-root staffing

rho_naive = R / k_naive              # = const = 1/(1+margin)
rho_sqrt  = R / k_sqrt               # растёт с масштабом

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))

# --- левая панель: число серверов ---
ax1.plot(R, k_naive, color=RED, lw=2.5,
         label=f"Наивно: фиксированный запас +{int(margin*100)}%")
ax1.plot(R, k_sqrt, color=BLUE, lw=2.5,
         label=r"Square-root: $k = R + c\sqrt{R}$")
ax1.plot(R, R, color=GRAY, lw=1.2, linestyle=":",
         label="Минимум: k = R (без запаса)")

# подсветим разрыв на большом масштабе
R0 = 160
ax1.annotate("на большом масштабе\nнаивный запас — это\nмного лишних серверов",
             xy=(R0, R0 * (1 + margin)), xytext=(60, 165),
             color=RED, fontsize=10,
             arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))
ax1.fill_between(R, k_sqrt, k_naive, color=RED, alpha=0.07)

ax1.set_xlim(0, 200)
ax1.set_ylim(0, 260)
ax1.set_xlabel("Предложенная нагрузка R = λ·E[S] (число занятых серверов)")
ax1.set_ylabel("Сколько серверов k нужно держать")
ax1.set_title("Сколько серверов нужно для одного качества", fontweight="bold")
ax1.legend(loc="upper left", fontsize=10)

# --- правая панель: допустимая утилизация ---
ax2.plot(R, rho_sqrt * 100, color=BLUE, lw=2.5,
         label=r"Square-root: $\rho = R/(R + c\sqrt{R})$")
ax2.plot(R, rho_naive * 100, color=RED, lw=2.5,
         label=f"Наивно: ρ = {100/(1+margin):.0f}% всегда")

for Rp in (4, 25, 100):
    rp = Rp / (Rp + c * np.sqrt(Rp)) * 100
    ax2.scatter([Rp], [rp], color=BLUE, zorder=5, s=35)
    ax2.annotate(f"R={Rp}\nρ≈{rp:.0f}%", xy=(Rp, rp), xytext=(Rp + 8, rp - 9),
                 color=BLUE, fontsize=9,
                 arrowprops=dict(arrowstyle="->", color=BLUE, lw=1.0))

ax2.set_xlim(0, 200)
ax2.set_ylim(40, 100)
ax2.set_xlabel("Масштаб системы R (число занятых серверов)")
ax2.set_ylabel("Допустимая утилизация ρ, %")
ax2.set_title("Большие системы безопасно работают плотнее", fontweight="bold")
ax2.legend(loc="lower right", fontsize=10)

plt.tight_layout()
plt.savefig(OUT / "lesson07_sqrt_staffing.png")
plt.close()
print("Сохранён: lesson07_sqrt_staffing.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 2. FIFO vs PS: среднее время отклика от вариативности C² при ρ = const
#   FIFO (M/G/1): W = E[S] + W_q,  W_q = ρ·E[S]·(1+C²) / (2(1−ρ))  (Поллачек—Хинчин)
#   PS  (M/G/1-PS): W = E[S]/(1−ρ)  — НЕ зависит от C² (insensitivity)
# ──────────────────────────────────────────────────────────────────────────────
ES = 1.0           # среднее время обслуживания = 1 (нормировка)
rho = 0.7          # фиксированная утилизация
Csq = np.linspace(0, 8, 400)

Wq_fifo = rho * ES * (1.0 + Csq) / (2.0 * (1.0 - rho))
W_fifo  = ES + Wq_fifo                       # полное время отклика в FIFO
W_ps    = ES / (1.0 - rho) * np.ones_like(Csq)   # PS — горизонталь

fig, ax = plt.subplots(figsize=(8.5, 5.2))
ax.plot(Csq, W_fifo, color=RED, lw=2.5,
        label="FIFO (M/G/1) — растёт линейно по C²")
ax.plot(Csq, W_ps, color=BLUE, lw=2.5,
        label=r"PS (M/G/1-PS): $W = E[S]/(1-\rho)$ — не зависит от C²")

# отметим C²=1 (экспонента) и тяжёлый хвост
for cc in (1.0, 6.0):
    wf = ES + rho * ES * (1 + cc) / (2 * (1 - rho))
    ax.scatter([cc], [wf], color=RED, zorder=5, s=35)

ax.annotate("однородные задачи (C²≈0):\nFIFO даже чуть лучше PS",
            xy=(0.1, ES + rho * ES * 1.0 / (2 * (1 - rho))),
            xytext=(1.2, 2.4),
            color=GRAY, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.2))
ax.annotate("тяжёлый хвост (большой C²):\nFIFO разносит, PS держит",
            xy=(6.0, ES + rho * ES * (1 + 6.0) / (2 * (1 - rho))),
            xytext=(2.6, 8.0),
            color=RED, fontsize=10,
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))

ax.set_xlim(0, 8)
ax.set_ylim(0, 10)
ax.set_xlabel("Вариативность размеров задач C² (квадрат коэффициента вариации)")
ax.set_ylabel("Среднее время отклика W (в единицах E[S])")
ax.set_title("FIFO vs Processor Sharing при одной утилизации ρ = 0.7",
             fontweight="bold")
ax.legend(loc="upper left", fontsize=10)
plt.tight_layout()
plt.savefig(OUT / "lesson07_fifo_vs_ps.png")
plt.close()
print("Сохранён: lesson07_fifo_vs_ps.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 3. Head-of-line blocking: Gantt-диаграмма обработки 4 задач
#   Одна длинная (B, 8 ед.) и три коротких (A, C, D — по 1 ед.),
#   все пришли в момент t=0. FIFO в порядке B, A, C, D vs PS.
# ──────────────────────────────────────────────────────────────────────────────
# Размеры задач
jobs = ["A (1)", "B (8)", "C (1)", "D (1)"]      # имя (размер)
size = {"A (1)": 1, "B (8)": 8, "C (1)": 1, "D (1)": 1}
colors = {"A (1)": GREEN, "B (8)": RED, "C (1)": BLUE, "D (1)": "#C29B3A"}
order_fifo = ["B (8)", "A (1)", "C (1)", "D (1)"]   # длинная приехала первой

fig, (axf, axp) = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True)

# --- FIFO: задачи идут строго по очереди ---
t = 0.0
finish_fifo = {}
for name in order_fifo:
    d = size[name]
    axf.barh(name, d, left=t, color=colors[name], edgecolor="white", height=0.6)
    axf.text(t + d / 2, name, f"{int(d)}", va="center", ha="center",
             color="white", fontsize=10, fontweight="bold")
    t += d
    finish_fifo[name] = t

# подписи времени завершения справа
for name in jobs:
    axf.text(finish_fifo[name] + 0.15, name, f"готово в {finish_fifo[name]:.0f}",
             va="center", ha="left", fontsize=9, color=GRAY)

axf.set_title("FIFO: короткие A, C, D застряли за длинной B (head-of-line blocking)",
              fontweight="bold", fontsize=12)
axf.set_xlim(0, 13.5)
axf.invert_yaxis()
axf.grid(True, axis="x", alpha=0.3)

# --- PS: ресурс делится поровну между активными задачами ---
# Точная PS-симуляция при одновременном старте (все в t=0).
# Скорость на задачу = 1/(число активных). Считаем моменты завершения.
remaining = dict(size)
active = set(remaining)
t = 0.0
# для рисования сегментов: для каждой задачи список (start, width) кусков
segments = {n: [] for n in jobs}
finish_ps = {}
while active:
    n_active = len(active)
    # сколько времени до ближайшего завершения: min(remaining)/ (1/n) = min*n
    dmin = min(remaining[n] for n in active)
    dt = dmin * n_active
    for n in active:
        segments[n].append((t, dt, n_active))
        remaining[n] -= dt / n_active
    t += dt
    done = [n for n in active if remaining[n] <= 1e-9]
    for n in done:
        finish_ps[n] = t
        active.discard(n)

# рисуем: высоту каждого сегмента масштабируем по доле ресурса (1/n_active)
for name in jobs:
    for (start, width, n_active) in segments[name]:
        h = 0.6 / n_active * 1.0     # тонкая полоса = меньше ресурса
        axp.barh(name, width, left=start, color=colors[name],
                 edgecolor="white", height=0.62, alpha=0.35 if n_active > 1 else 0.9)
    axp.text(finish_ps[name] + 0.15, name, f"готово в {finish_ps[name]:.1f}",
             va="center", ha="left", fontsize=9, color=GRAY)

axp.set_title("PS (разделение ресурса): A, C, D проскакивают быстро, B растягивается",
              fontweight="bold", fontsize=12)
axp.set_xlim(0, 13.5)
axp.set_xlabel("Время (единицы обслуживания)")
axp.invert_yaxis()
axp.grid(True, axis="x", alpha=0.3)

plt.tight_layout()
plt.savefig(OUT / "lesson07_hol_blocking.png")
plt.close()
print("Сохранён: lesson07_hol_blocking.png")

# Печатаем числа, чтобы свериться в тексте урока
mean_fifo = np.mean(list(finish_fifo.values()))
mean_ps = np.mean(list(finish_ps.values()))
print(f"FIFO finish times: {finish_fifo}, mean={mean_fifo:.2f}")
print(f"PS   finish times: {{ {', '.join(f'{k}:{v:.2f}' for k,v in finish_ps.items())} }}, mean={mean_ps:.2f}")
