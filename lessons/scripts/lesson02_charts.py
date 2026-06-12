"""Графики для Урока 2 «Теорема Литтла».

Запуск из корня проекта:
    .venv/bin/python lessons/scripts/lesson02_charts.py

Создаёт PNG в lessons/images/:
    lesson02_cumulative.png  — кумулятивные кривые A(t) и D(t), площадь между ними
    lesson02_convergence.png — симуляция: скользящие L и lambda*W сходятся
    lesson02_bytes_trap.png  — «ловушка байтов»: одинаковый поток в штуках, разный в байтах
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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
COL_MAIN = "#4C72B0"   # основной
COL_ACC = "#DD4C4C"    # акцент
COL_EXTRA = "#55A868"  # дополнительный
COL_GREY = "#888888"   # серый

IMAGES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images"
)
os.makedirs(IMAGES_DIR, exist_ok=True)


def save(fig, name):
    path = os.path.join(IMAGES_DIR, name)
    fig.savefig(path)
    plt.close(fig)
    print(f"saved {path}")


def step_curve(times, t_grid):
    """Кумулятивный счётчик: сколько событий из times <= t для каждого t из t_grid."""
    times = np.sort(times)
    return np.searchsorted(times, t_grid, side="right")


def chart_cumulative():
    """A(t) — пришло, D(t) — ушло. Вертикальный зазор = L(t), горизонтальный = W."""
    # Небольшая детерминированная «история» запросов: моменты прихода и ухода
    arrivals = np.array([0.5, 1.2, 1.8, 2.4, 3.1, 3.9, 4.6, 5.5, 6.3, 7.0])
    # время в системе у каждого запроса (W_i), уход = приход + время
    service = np.array([1.4, 1.1, 1.6, 1.3, 1.5, 1.2, 1.7, 1.0, 1.3, 1.4])
    departures = arrivals + service

    t_max = 9.0
    t = np.linspace(0, t_max, 2000)
    A = step_curve(arrivals, t)
    D = step_curve(departures, t)

    fig, ax = plt.subplots()
    ax.step(t, A, where="post", color=COL_MAIN, linewidth=2.2, label="A(t) — пришло")
    ax.step(t, D, where="post", color=COL_ACC, linewidth=2.2, label="D(t) — ушло")

    # Площадь между кривыми = суммарное время, проведённое запросами в системе
    ax.fill_between(t, D, A, step="post", color=COL_MAIN, alpha=0.12)

    # Вертикальная аннотация: L(t) — число запросов в системе в момент t0
    t0 = 4.0
    a0 = int(step_curve(arrivals, np.array([t0]))[0])
    d0 = int(step_curve(departures, np.array([t0]))[0])
    ax.annotate(
        "",
        xy=(t0, a0), xytext=(t0, d0),
        arrowprops=dict(arrowstyle="<->", color=COL_GREY, lw=1.8),
    )
    ax.text(
        t0 + 0.1, (a0 + d0) / 2,
        f"L(t) = {a0 - d0}\n(вертикальный зазор)",
        color=COL_GREY, fontsize=11, va="center",
    )

    # Горизонтальная аннотация: W одного запроса (3-й запрос, индекс 2)
    i = 2
    y_lvl = i + 1  # после прихода i-го запроса счётчик = i+1
    ax.annotate(
        "",
        xy=(arrivals[i], y_lvl), xytext=(departures[i], y_lvl),
        arrowprops=dict(arrowstyle="<->", color=COL_EXTRA, lw=1.8),
    )
    ax.text(
        (arrivals[i] + departures[i]) / 2, y_lvl + 0.25,
        "W запроса\n(горизонтальный зазор)",
        color=COL_EXTRA, fontsize=11, ha="center", va="bottom",
    )

    ax.set_title("Кумулятивные кривые прихода и ухода: геометрия теоремы Литтла")
    ax.set_xlabel("время t, с")
    ax.set_ylabel("число запросов (накопленным итогом)")
    ax.set_xlim(0, t_max)
    ax.set_ylim(0, len(arrivals) + 0.5)
    ax.legend(loc="upper left")
    # Подпись к площади
    ax.text(
        6.0, 1.0,
        "Площадь = суммарное\nвремя в системе",
        color=COL_MAIN, fontsize=10, ha="center", alpha=0.9,
    )
    save(fig, "lesson02_cumulative.png")


def chart_convergence():
    """Симуляция M/M/1-подобной системы: L и lambda*W сходятся со временем."""
    rng = np.random.default_rng(42)

    lam = 5.0          # интенсивность входящего потока, запр/с
    mu = 6.0           # интенсивность обслуживания одного сервера, запр/с
    n = 60000          # число запросов

    # Межприходные интервалы и времена обслуживания — экспоненциальные
    inter = rng.exponential(1.0 / lam, n)
    arrival = np.cumsum(inter)
    service = rng.exponential(1.0 / mu, n)

    # FIFO один сервер: начало обслуживания = max(приход, конец предыдущего)
    start = np.empty(n)
    finish = np.empty(n)
    prev_finish = 0.0
    for k in range(n):
        s = arrival[k] if arrival[k] > prev_finish else prev_finish
        start[k] = s
        prev_finish = s + service[k]
        finish[k] = prev_finish

    wait = finish - arrival  # W_i — время в системе

    horizon = arrival[-1]
    # Сетка контрольных точек по времени
    checkpoints = np.linspace(horizon * 0.02, horizon, 200)

    L_t = np.empty_like(checkpoints)       # средняя по времени длина в системе на [0, T]
    lamW_t = np.empty_like(checkpoints)    # lambda(T) * W(T) по уже завершённым запросам

    for j, T in enumerate(checkpoints):
        # Площадь = sum по запросам пересечения [arrival, finish] с [0, T]
        lo = np.minimum(arrival, T)
        hi = np.minimum(finish, T)
        area = np.sum(np.clip(hi - lo, 0.0, None))
        L_t[j] = area / T

        done = finish <= T
        n_done = int(np.sum(done))
        if n_done > 0:
            lam_emp = n_done / T
            W_emp = np.mean(wait[done])
            lamW_t[j] = lam_emp * W_emp
        else:
            lamW_t[j] = np.nan

    fig, ax = plt.subplots()
    ax.plot(checkpoints, L_t, color=COL_MAIN, linewidth=2.0,
            label="L — среднее число в системе (по времени)")
    ax.plot(checkpoints, lamW_t, color=COL_ACC, linewidth=2.0, linestyle="--",
            label=r"$\lambda \cdot W$ — поток × среднее время")

    # Теоретическое значение для M/M/1: L = rho/(1-rho)
    rho = lam / mu
    L_theory = rho / (1 - rho)
    ax.axhline(L_theory, color=COL_GREY, linewidth=1.2, linestyle=":",
               label=f"теория M/M/1: L = {L_theory:.1f}")

    ax.set_title("Теорема Литтла в симуляции: L и λ·W сходятся к одному значению")
    ax.set_xlabel("горизонт усреднения T, с")
    ax.set_ylabel("число запросов в системе")
    ax.set_ylim(0, L_theory * 1.8)
    ax.legend(loc="upper right")
    ax.text(
        horizon * 0.05, L_theory * 1.55,
        "На коротком горизонте — шум,\nна длинном — закон выполняется точно",
        fontsize=10, color=COL_GREY,
    )
    save(fig, "lesson02_convergence.png")


def chart_bytes_trap():
    """Одинаковый поток в штуках (одинаковый L в штуках), но разный в байтах."""
    rng = np.random.default_rng(7)

    lam = 1000.0       # сообщений/с — одинаково для обоих потоков
    W = 0.1            # с — одинаковое среднее время в системе
    # => L = lambda*W = 100 сообщений «висит» в среднем у обоих

    horizon = 3.0
    t_grid = np.linspace(0, horizon, 600)

    def simulate(size_sampler, label_seed):
        r = np.random.default_rng(label_seed)
        n = int(lam * horizon * 1.2)
        inter = r.exponential(1.0 / lam, n)
        arrival = np.cumsum(inter)
        arrival = arrival[arrival < horizon]
        n = len(arrival)
        dwell = r.exponential(W, n)         # время в системе, среднее = W
        finish = arrival + dwell
        sizes = size_sampler(r, n)          # размер каждого сообщения в КБ
        # L по байтам в момент t = сумма размеров сообщений, что сейчас «в системе»
        bytes_in = np.empty_like(t_grid)
        count_in = np.empty_like(t_grid)
        for i, t in enumerate(t_grid):
            inside = (arrival <= t) & (finish > t)
            bytes_in[i] = np.sum(sizes[inside])
            count_in[i] = np.sum(inside)
        return count_in, bytes_in

    # Поток A: все сообщения одинаковые, ровно 10 КБ
    def sampler_uniform(r, n):
        return np.full(n, 10.0)

    # Поток B: тот же средний размер 10 КБ, но тяжёлый хвост (немного огромных)
    def sampler_heavy(r, n):
        # 95% мелких ~1 КБ, 5% больших ~181 КБ -> среднее ~10 КБ
        big = r.random(n) < 0.05
        s = np.where(big, r.exponential(181.0, n), r.exponential(1.0, n))
        return s

    cntA, bytesA = simulate(sampler_uniform, 101)
    cntB, bytesB = simulate(sampler_heavy, 202)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)

    # Верх: число сообщений «в полёте» — у обоих колеблется около L = 100
    ax1.plot(t_grid, cntA, color=COL_MAIN, linewidth=1.6,
             label="поток A: одинаковый размер")
    ax1.plot(t_grid, cntB, color=COL_ACC, linewidth=1.6,
             label="поток B: тяжёлый хвост размеров")
    ax1.axhline(100, color=COL_GREY, linewidth=1.2, linestyle=":",
                label="L = λ·W = 100 шт")
    ax1.set_title("Один и тот же лаг в ШТУКАХ…")
    ax1.set_ylabel("сообщений в системе, шт")
    ax1.legend(loc="upper right", fontsize=9)
    ax1.set_ylim(0, 180)

    # Низ: байтовый «лаг» — у потока B рваный и непредсказуемый
    ax2.plot(t_grid, bytesA, color=COL_MAIN, linewidth=1.6,
             label="поток A: ровно 100×10 КБ ≈ 1 МБ")
    ax2.plot(t_grid, bytesB, color=COL_ACC, linewidth=1.6,
             label="поток B: скачет из-за редких гигантов")
    ax2.set_title("…но СОВСЕМ разный лаг в БАЙТАХ")
    ax2.set_xlabel("время t, с")
    ax2.set_ylabel("данных в системе, КБ")
    ax2.legend(loc="upper right", fontsize=9)

    fig.suptitle("Ловушка байтов: L = λ·W считает штуки, а не байты",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    save(fig, "lesson02_bytes_trap.png")


def main():
    chart_cumulative()
    chart_convergence()
    chart_bytes_trap()
    print("done")


if __name__ == "__main__":
    main()
