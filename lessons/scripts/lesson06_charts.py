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

rng = np.random.default_rng(6)

# ──────────────────────────────────────────────────────────────────────────────
# График 1. Один и тот же бёрстовый трафик в трёх разрешениях агрегации
# ──────────────────────────────────────────────────────────────────────────────
#
# Модель мгновенной нагрузки: окно 15 секунд, базовый "пол" разбивается на
# чередование "всплеск 1 с при 100% мощности" и "тишина 1 с при 0%".
# Средняя утилизация = 50%, но мгновенная скачет между 0% и 100%.

DT = 0.01                      # шаг "истинной" нагрузки = 10 мс
T  = 15.0                      # окно мониторинга, секунды
t  = np.arange(0, T, DT)

# Мгновенная утилизация: квадратная волна с периодом 2 с (1 с пик / 1 с тишина)
inst = np.where((np.floor(t) % 2) == 0, 1.0, 0.0)   # доля 0..1


def aggregate(signal, t_axis, window):
    """Усреднить signal по непересекающимся окнам ширины window."""
    n_bins = int(np.ceil(T / window))
    centers = []
    values = []
    for i in range(n_bins):
        lo, hi = i * window, (i + 1) * window
        mask = (t_axis >= lo) & (t_axis < hi)
        if mask.any():
            centers.append((lo + min(hi, T)) / 2)
            values.append(signal[mask].mean())
    return np.array(centers), np.array(values)


resolutions = [
    (0.01, "Шаг 10 мс — видны пики 100%", RED),
    (1.0,  "Шаг 1 с — пики ещё различимы", BLUE),
    (15.0, "Шаг 15 с — ровные 50%", GREEN),
]

fig, axes = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
fig.suptitle("Один и тот же бёрстовый трафик в трёх разрешениях мониторинга",
             fontsize=13, fontweight="bold")

for ax, (window, title, color) in zip(axes, resolutions):
    if window <= DT:
        c, v = t, inst
        ax.fill_between(c, 0, v * 100, step="post", color=color, alpha=0.35)
        ax.plot(c, v * 100, drawstyle="steps-post", color=color, lw=1.2)
    else:
        c, v = aggregate(inst, t, window)
        # рисуем как ступеньки на всю ширину окна
        edges = np.arange(0, T + window, window)
        edges = edges[edges <= T + 1e-9]
        ax.bar(edges[:len(v)], v * 100, width=window, align="edge",
               color=color, alpha=0.55, edgecolor="white")
    ax.axhline(50, color=GRAY, lw=1.2, ls="--")
    ax.set_ylim(0, 110)
    ax.set_ylabel("Утилизация, %")
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_yticks([0, 50, 100])

axes[0].annotate("мгновенно ~100%", xy=(0.5, 100), xytext=(2.0, 70),
                 color=RED, fontsize=10,
                 arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))
axes[2].annotate("мониторинг показывает\nспокойные 50%", xy=(7.5, 50),
                 xytext=(8.5, 80), color=GREEN, fontsize=10,
                 arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.2))
axes[-1].set_xlabel("Время, секунды")
plt.tight_layout()
plt.savefig(OUT / "lesson06_aggregation.png")
plt.close()
print("Сохранён: lesson06_aggregation.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 2. Симуляция latency: бёрстовый трафик vs ровный поток
#           при ОДИНАКОВОЙ средней утилизации
# ──────────────────────────────────────────────────────────────────────────────
#
# Один сервер (FIFO), время обслуживания детерминированное = 1 единица.
# Средняя интенсивность подобрана так, что rho = 0.5 в обоих случаях.
# Разница только в РАСПРЕДЕЛЕНИИ моментов прихода:
#   - ровный поток: запросы строго через равные интервалы (низкая вариативность);
#   - бёрстовый: запросы приходят пачками (высокая вариативность).

def simulate_fifo(arrivals, service_time):
    """Возвращает массив latency (ожидание + обслуживание) для каждого запроса."""
    arrivals = np.sort(arrivals)
    free_at = 0.0
    latencies = np.empty(len(arrivals))
    for i, a in enumerate(arrivals):
        start = max(a, free_at)
        finish = start + service_time
        free_at = finish
        latencies[i] = finish - a
    return latencies

SERVICE = 1.0          # время обслуживания одного запроса
N = 20000              # число запросов
RHO = 0.5              # целевая утилизация
mean_gap = SERVICE / RHO   # средний интервал между приходами = 2.0

# Ровный поток: интервалы почти константа (детерминированный приход, D)
gaps_even = np.full(N, mean_gap)
arr_even = np.cumsum(gaps_even)
lat_even = simulate_fifo(arr_even, SERVICE)

# Бёрстовый поток: та же средняя интенсивность, но пачками.
# Чередуем короткие интервалы (пачка) и длинные паузы так, чтобы среднее = mean_gap.
burst_len = 8                       # запросов в пачке
gap_in_burst = 0.15 * SERVICE       # плотно внутри пачки
# подбираем паузу между пачками, чтобы средний интервал = mean_gap
# среднее = ((burst_len-1)*gap_in_burst + pause) / burst_len = mean_gap
pause = burst_len * mean_gap - (burst_len - 1) * gap_in_burst
gaps_burst = []
while len(gaps_burst) < N:
    gaps_burst.extend([gap_in_burst] * (burst_len - 1))
    gaps_burst.append(pause)
gaps_burst = np.array(gaps_burst[:N])
arr_burst = np.cumsum(gaps_burst)
lat_burst = simulate_fifo(arr_burst, SERVICE)

# отбрасываем разогрев
warm = 200
lat_even = lat_even[warm:]
lat_burst = lat_burst[warm:]

p50_e, p99_e = np.percentile(lat_even, [50, 99])
p50_b, p99_b = np.percentile(lat_burst, [50, 99])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5),
                               gridspec_kw={"width_ratios": [1.4, 1]})

# Левая панель: гистограммы latency
bins = np.linspace(0, max(lat_burst.max(), 5), 50)
ax1.hist(lat_even, bins=bins, color=GREEN, alpha=0.7,
         label=f"Ровный поток (p99 = {p99_e:.1f})")
ax1.hist(lat_burst, bins=bins, color=RED, alpha=0.6,
         label=f"Бёрстовый поток (p99 = {p99_b:.1f})")
ax1.set_xlabel("Latency запроса (в единицах времени обслуживания)")
ax1.set_ylabel("Число запросов")
ax1.set_title("Распределение latency при ρ = 0.5", fontweight="bold")
ax1.legend(loc="upper right", fontsize=10)

# Правая панель: перцентили рядом
labels = ["p50", "p99"]
x = np.arange(len(labels))
w = 0.38
ax2.bar(x - w/2, [p50_e, p99_e], w, color=GREEN, label="Ровный поток")
ax2.bar(x + w/2, [p50_b, p99_b], w, color=RED, label="Бёрстовый поток")
for xi, ve, vb in zip(x, [p50_e, p99_e], [p50_b, p99_b]):
    ax2.text(xi - w/2, ve + 0.05, f"{ve:.1f}", ha="center", va="bottom", fontsize=9)
    ax2.text(xi + w/2, vb + 0.05, f"{vb:.1f}", ha="center", va="bottom", fontsize=9)
ax2.set_xticks(x)
ax2.set_xticklabels(labels)
ax2.set_ylabel("Latency")
ax2.set_title("Перцентили: средняя ρ та же,\nхвосты — разные", fontweight="bold",
              fontsize=12)
ax2.legend(loc="upper left", fontsize=10)

plt.tight_layout()
plt.savefig(OUT / "lesson06_burst_latency.png")
plt.close()
print("Сохранён: lesson06_burst_latency.png")
print(f"  Ровный поток:   p50={p50_e:.2f}  p99={p99_e:.2f}")
print(f"  Бёрстовый поток: p50={p50_b:.2f}  p99={p99_b:.2f}")

# ──────────────────────────────────────────────────────────────────────────────
# График 3. Парадокс инспекции: автобусы и пассажиры
# ──────────────────────────────────────────────────────────────────────────────
#
# Интервалы между автобусами вариативны (среднее = 10 минут).
# Пассажиры приходят равномерно на временной оси -> чаще попадают в длинные
# интервалы. Считаем фактическое среднее ожидание и сравниваем с "наивным" E[X]/2.

MEAN_INTERVAL = 10.0      # минут, среднее между автобусами
# Сделаем интервалы вариативными: смесь коротких и длинных
n_buses = 12
# чередуем короткие (4 мин) и длинные (16 мин) -> среднее = 10
intervals = np.array([4, 16, 4, 16, 4, 16, 4, 16, 4, 16, 4, 16], dtype=float)
bus_times = np.concatenate(([0.0], np.cumsum(intervals)))
total_T = bus_times[-1]

# Пассажиры приходят равномерно
n_pass = 400
pass_times = np.sort(rng.uniform(0, total_T, size=n_pass))

# Для каждого пассажира — ожидание до следующего автобуса
next_bus_idx = np.searchsorted(bus_times, pass_times, side="right")
wait = bus_times[next_bus_idx] - pass_times

# длина интервала, в который попал пассажир
interval_len = intervals[next_bus_idx - 1]

mean_wait_actual = wait.mean()
naive = MEAN_INTERVAL / 2.0

# Теоретическое E[R] = E[X^2] / (2 E[X])
EX = intervals.mean()
EX2 = (intervals ** 2).mean()
ER_theory = EX2 / (2 * EX)
C2 = intervals.var() / EX**2

fig, (axA, axB) = plt.subplots(2, 1, figsize=(11, 7),
                               gridspec_kw={"height_ratios": [2, 1.3]})

# Верх: временная ось с автобусами и пассажирами
for i in range(len(intervals)):
    lo, hi = bus_times[i], bus_times[i + 1]
    color = RED if intervals[i] > MEAN_INTERVAL else GREEN
    axA.axvspan(lo, hi, color=color, alpha=0.12)
for bt in bus_times:
    axA.axvline(bt, color=GRAY, lw=2.0)
# пассажиры
in_long = interval_len > MEAN_INTERVAL
axA.scatter(pass_times[in_long], rng.uniform(0.55, 0.75, in_long.sum()),
            s=14, color=RED, alpha=0.7, label="пассажиры в длинных интервалах")
axA.scatter(pass_times[~in_long], rng.uniform(0.25, 0.45, (~in_long).sum()),
            s=14, color=GREEN, alpha=0.7, label="пассажиры в коротких интервалах")
axA.set_xlim(0, total_T)
axA.set_ylim(0, 1)
axA.set_yticks([])
axA.set_xlabel("Время, минуты")
axA.set_title("Автобусы (серые линии) ходят в среднем раз в 10 минут.\n"
              "Пассажиры приходят равномерно — но большинство попадает в ДЛИННЫЕ интервалы",
              fontsize=12, fontweight="bold")
axA.legend(loc="upper right", fontsize=9, framealpha=0.9)
share_long = in_long.mean() * 100
axA.text(0.01, 0.92,
         f"{share_long:.0f}% пассажиров попали в длинные интервалы\n"
         f"(хотя длинных интервалов — ровно половина)",
         transform=axA.transAxes, fontsize=10, va="top",
         bbox=dict(facecolor="white", edgecolor=RED, boxstyle="round,pad=0.3"))

# Низ: фактическое среднее ожидание vs наивное E[X]/2
bars = ["Наивно: E[X]/2", "Теория: E[X²]/(2E[X])", "Симуляция"]
vals = [naive, ER_theory, mean_wait_actual]
colors = [GRAY, BLUE, RED]
ypos = np.arange(len(bars))
axB.barh(ypos, vals, color=colors, alpha=0.8)
for yi, v in zip(ypos, vals):
    axB.text(v + 0.1, yi, f"{v:.1f} мин", va="center", fontsize=11, fontweight="bold")
axB.set_yticks(ypos)
axB.set_yticklabels(bars)
axB.invert_yaxis()
axB.set_xlabel("Среднее ожидание пассажира, минуты")
axB.set_title(f"Среднее ожидание ≈ {mean_wait_actual:.1f} мин, а не наивные {naive:.0f} мин"
              f"   (C² = {C2:.2f})", fontsize=12, fontweight="bold")
axB.grid(axis="y", alpha=0)

plt.tight_layout()
plt.savefig(OUT / "lesson06_inspection_paradox.png")
plt.close()
print("Сохранён: lesson06_inspection_paradox.png")
print(f"  E[X]={EX:.1f}  E[X^2]={EX2:.1f}  C^2={C2:.2f}")
print(f"  Наивно E[X]/2={naive:.2f}  Теория E[R]={ER_theory:.2f}  Симуляция={mean_wait_actual:.2f}")
