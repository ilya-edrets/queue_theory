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
ORANGE = "#E08A1E"

OUT = Path("lessons/images")
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)

# ──────────────────────────────────────────────────────────────────────────────
# Симуляция тредпула с микробёрстами.
#
# Дискретная по времени модель одного обработчика (single server, FIFO).
# Шаг dt = 1 мс. На каждом шаге приходит случайное число «работы» (в мс CPU),
# которое кладётся в очередь. Обработчик за шаг успевает сделать ровно 1 мс работы.
# Средняя нагрузка ~50 %, но рабочая нагрузка приходит МИКРОБЁРСТАМИ:
# короткие (десятки мс) залпы 100 %-загрузки на фоне почти пустой системы.
# ──────────────────────────────────────────────────────────────────────────────

T_TOTAL = 60_000          # 60 секунд симуляции
dt = 1.0                  # шаг 1 мс
n = T_TOTAL               # число шагов (мс)
t_ms = np.arange(n)
t_s = t_ms / 1000.0

# Базовый «ровный» фоновый поток работы: в среднем 0.42 мс работы на 1 мс времени
# (≈42 % мгновенной загрузки в спокойные периоды).
base_rate = 0.42
arrivals = rng.exponential(base_rate, size=n)

# Добавляем микробёрсты: каждые ~0.8–1.5 с короткий залп 25–55 мс,
# в течение которого приходит работы заметно больше, чем сервер успевает съесть
# (очередь растёт), но потом система успевает её разгрести до следующего бёрста.
t = 0
burst_marks = []
while t < n - 100:
    gap = int(rng.uniform(700, 1500))      # пауза между бёрстами
    t += gap
    if t >= n - 100:
        break
    dur = int(rng.uniform(25, 55))         # длительность бёрста, мс
    # во время бёрста приходит ~1.6 мс работы на каждый 1 мс времени -> очередь растёт
    arrivals[t:t + dur] += rng.exponential(1.4, size=dur)
    burst_marks.append((t, dur))
    t += dur

# Прогон одно-серверной очереди: queue — накопленная невыполненная работа (мс).
# busy[i] — доля 1-мс слота, реально занятая работой (от 0 до 1): это и есть
# мгновенная утилизация на этом шаге.
queue = np.zeros(n)
q = 0.0
busy = np.zeros(n)
for i in range(n):
    q += arrivals[i]
    done = min(q, 1.0)    # за 1-мс слот сервер может сделать максимум 1 мс работы
    q -= done
    busy[i] = done        # доля слота, занятая работой = мгновенная утилизация
    queue[i] = q          # сколько работы (мс) ждёт в очереди в конце шага

# Мгновенная утилизация = занят/не занят; усредняем по окну 15 с -> «слепой» график.
WIN_MS = 15_000
def moving_mean(x, w, require_full=False):
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.full_like(x, np.nan, dtype=float)
    for i in range(len(x)):
        a = max(0, i - w + 1)
        if require_full and (i + 1) < w:
            continue   # окно ещё не заполнено — не показываем
        out[i] = (c[i + 1] - c[a]) / (i + 1 - a)
    return out

# Утилизация за полное окно 15 с (NaN, пока окно не заполнилось).
util_15s = moving_mean(busy, WIN_MS, require_full=True) * 100.0

# ──────────────────────────────────────────────────────────────────────────────
# SelfPing: каждые 10 мс кладём в очередь пустую задачу и смотрим,
# сколько уже накопленной работы ей придётся подождать (= q в этот момент).
# К замеру добавляем период пинга (10 мс) -> оценка сверху. Берём max по окну 15 с.
# ──────────────────────────────────────────────────────────────────────────────

PING_PERIOD = 10                       # мс
ping_idx = np.arange(0, n, PING_PERIOD)
ping_wait = queue[ping_idx]            # время ожидания пинг-задачи (мс)
ping_t_s = ping_idx / 1000.0
ping_est = ping_wait + PING_PERIOD     # оценка сверху: замер + период

# Максимум замеров SelfPing на скользящем окне 15 с (по пинг-сэмплам)
ping_per_win = WIN_MS // PING_PERIOD
def moving_max(x, w):
    out = np.full_like(x, np.nan, dtype=float)
    for i in range(len(x)):
        a = max(0, i - w + 1)
        out[i] = np.max(x[a:i + 1])
    return out

ping_est_max15 = moving_max(ping_est, ping_per_win)

# Реальный максимум ожидания ЛЮБОЙ задачи на окне 15 с (для графика 2)
real_max15 = moving_max(queue, WIN_MS)

# ──────────────────────────────────────────────────────────────────────────────
# График 1. Слепой график утилизации vs зоркий SelfPing
# ──────────────────────────────────────────────────────────────────────────────

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

# --- Верхняя панель: мгновенная нагрузка + слепое усреднение по 15 с ---
# Мгновенная утилизация, сглаженная по 50 мс для читаемости фона
util_inst_50 = moving_mean(busy, 50) * 100.0
ax1.fill_between(t_s, 0, util_inst_50, color=BLUE, alpha=0.18,
                 label="Мгновенная загрузка (окно 50 мс)")
ax1.plot(t_s, util_15s, color=RED, lw=2.8,
         label="График утилизации, усреднённый по 15 с")
ax1.axhline(100, color=GRAY, lw=1, linestyle=":")
ax1.text(0.3, 103, "100 %", color=GRAY, fontsize=10)

# Пометим несколько бёрстов
for (bt, bd) in burst_marks[:6]:
    ax1.axvspan(bt / 1000, (bt + bd) / 1000, color=ORANGE, alpha=0.12)
ax1.annotate("микробёрсты: внутри 100 %,\nно график 15 с их не видит",
             xy=(burst_marks[2][0] / 1000, 100),
             xytext=(12, 118), fontsize=10, color=ORANGE, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.3))

ax1.set_ylim(0, 135)
ax1.set_ylabel("Утилизация, %")
ax1.set_title("Сверху — мониторинг утилизации: ровные ~50 %, всё «спокойно»",
              fontweight="bold", fontsize=12)
ax1.legend(loc="upper right", fontsize=9, framealpha=0.9)

# --- Нижняя панель: замеры SelfPing + max по 15 с ---
ax2.plot(ping_t_s, ping_wait, color=GRAY, lw=0.8, alpha=0.7,
         label="Замер SelfPing: ожидание пинга (каждые 10 мс)")
ax2.scatter(ping_t_s, ping_wait, s=4, color=BLUE, alpha=0.5, zorder=2)
ax2.plot(ping_t_s, ping_est_max15, color=RED, lw=2.8,
         label="Максимум SelfPing на окне 15 с (замер + период)")

ax2.annotate("SelfPing ловит всплески\nожидания до десятков мс",
             xy=(ping_t_s[np.argmax(ping_wait)], np.max(ping_wait)),
             xytext=(18, np.max(ping_wait) * 0.78), fontsize=10,
             color=RED, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))

ax2.set_ylim(0, np.max(ping_est_max15) * 1.25)
ax2.set_xlim(0, 60)
ax2.set_xlabel("Время, с")
ax2.set_ylabel("Время ожидания, мс")
ax2.set_title("Снизу — SelfPing: тот же интервал, но всплески latency видны",
              fontweight="bold", fontsize=12)
ax2.legend(loc="upper right", fontsize=9, framealpha=0.9)

plt.tight_layout()
plt.savefig(OUT / "lesson08_selfping_sim.png")
plt.close()
print("Сохранён: lesson08_selfping_sim.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 2. Оценка сверху: реальный max ожидания vs оценка SelfPing
# ──────────────────────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(t_s, real_max15, color=GRAY, lw=2.2,
        label="Реальный максимум ожидания любой задачи (окно 15 с)")
ax.plot(ping_t_s, ping_est_max15, color=RED, lw=2.5,
        label="Оценка SelfPing сверху: замер + период (окно 15 с)")
ax.fill_between(ping_t_s, real_max15[ping_idx], ping_est_max15,
                where=(ping_est_max15 >= real_max15[ping_idx]),
                color=GREEN, alpha=0.15,
                label="запас: оценка ≥ реальности")

ax.set_xlim(0, 60)
ax.set_ylim(0, max(np.max(real_max15), np.max(ping_est_max15)) * 1.2)
ax.set_xlabel("Время, с")
ax.set_ylabel("Время ожидания, мс")
ax.set_title("SelfPing даёт честную оценку СВЕРХУ\n(пинг мог проскочить пик, но период 10 мс это покрывает)",
             fontweight="bold")
ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
plt.tight_layout()
plt.savefig(OUT / "lesson08_upper_bound.png")
plt.close()
print("Сохранён: lesson08_upper_bound.png")

# ──────────────────────────────────────────────────────────────────────────────
# Числа для текста урока
# ──────────────────────────────────────────────────────────────────────────────
print("\n--- Числа для урока ---")
print(f"Средняя утилизация за всю симуляцию: {busy.mean()*100:.1f} %")
print(f"Максимум графика утилизации (полное окно 15 с): {np.nanmax(util_15s):.1f} %")
print(f"Минимум графика утилизации (полное окно 15 с): {np.nanmin(util_15s):.1f} %")
print(f"Максимум мгновенной загрузки (окно 50 мс): {np.nanmax(util_inst_50):.1f} %")
print(f"Максимальное реальное ожидание задачи: {queue.max():.1f} мс")
print(f"Максимальный замер SelfPing: {ping_wait.max():.1f} мс")
print(f"Максимум оценки SelfPing (замер+период): {ping_est.max():.1f} мс")
print(f"Число бёрстов за 60 с: {len(burst_marks)}")
overhead = (1.0 / PING_PERIOD)  # доля времени на пинги при ~0 мс работе пинга
print(f"Частота пингов: каждые {PING_PERIOD} мс ({n//PING_PERIOD} пингов за минуту)")
