import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

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
C_BLUE  = "#4C72B0"
C_RED   = "#DD4C4C"
C_GREEN = "#55A868"
C_GRAY  = "#888888"

OUT_DIR = "lessons/images"
os.makedirs(OUT_DIR, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# График 1: Stacked bar — из чего складывается latency для трёх сценариев
# ──────────────────────────────────────────────────────────────────────────────

scenarios = [
    "Локальный GPU\n(тензор 100 МБ)",
    "API-сервис\n(Москва → Москва)",
    "API-сервис\n(Москва → Амстердам)",
]

# Компоненты latency, мс
propagation   = np.array([0.003, 2.0,  36.0])   # время распространения
transmission  = np.array([3.1,   0.8,   0.8])   # время передачи (PCIe / сеть)
processing    = np.array([12.0,  5.0,   5.0])   # вычисление / обработка
queueing      = np.array([1.5,   3.0,   3.0])   # ожидание в очереди

x = np.arange(len(scenarios))
bar_w = 0.5

fig, ax = plt.subplots()

b1 = ax.bar(x, propagation,  bar_w, label="Распространение (propagation)",  color=C_BLUE)
b2 = ax.bar(x, transmission, bar_w, label="Передача (transmission)",         color=C_GREEN,
            bottom=propagation)
b3 = ax.bar(x, processing,   bar_w, label="Обработка (processing)",          color=C_GRAY,
            bottom=propagation + transmission)
b4 = ax.bar(x, queueing,     bar_w, label="Очередь (queueing)",              color=C_RED,
            bottom=propagation + transmission + processing)

ax.set_xticks(x)
ax.set_xticklabels(scenarios, fontsize=11)
ax.set_ylabel("Задержка, мс")
ax.set_title("Из чего складывается latency запроса")
ax.legend(loc="upper left", fontsize=10)

# Аннотация: в третьем сценарии propagation доминирует
total3 = propagation[2] + transmission[2] + processing[2] + queueing[2]
ax.annotate(
    f"Распространение\n{propagation[2]:.0f} мс ({propagation[2]/total3*100:.0f}%)",
    xy=(2, propagation[2] / 2),
    xytext=(1.45, 28),
    fontsize=9,
    color=C_BLUE,
    arrowprops=dict(arrowstyle="->", color=C_BLUE, lw=1.2),
)

plt.savefig(f"{OUT_DIR}/lesson01_latency_breakdown.png")
plt.close()
print("Сохранён: lesson01_latency_breakdown.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 2: Transmission time vs размер сообщения при разной пропускной способности
#           + горизонтальная линия propagation time (Москва–Амстердам, ~36 мс)
# ──────────────────────────────────────────────────────────────────────────────

size_mb = np.linspace(0.1, 500, 500)   # размер сообщения, МБ
size_b  = size_mb * 8                  # в мегабитах

# Пропускные способности
channels = {
    "1 Гбит/с (стандартный датацентр)":  1_000,    # Мбит/с
    "10 Гбит/с (highload датацентр)":   10_000,
    "PCIe 4.0 x16 (~256 Гбит/с)":      256_000,
}
colors = [C_GRAY, C_GREEN, C_BLUE]

prop_delay_ms = 36.0   # Москва–Амстердам, мс

fig, ax = plt.subplots()

for (label, bw_mbps), color in zip(channels.items(), colors):
    tx_ms = size_b / bw_mbps * 1000   # время передачи, мс
    ax.plot(size_mb, tx_ms, label=label, color=color, lw=2)

ax.axhline(prop_delay_ms, color=C_RED, lw=2, ls="--",
           label=f"Propagation Москва–Амстердам ({prop_delay_ms:.0f} мс)")

ax.set_xlabel("Размер сообщения, МБ")
ax.set_ylabel("Время, мс")
ax.set_title("Transmission time vs propagation time\nпри разной пропускной способности")
ax.legend(fontsize=9, loc="upper left")
ax.set_xlim(0, 500)
ax.set_ylim(0, 130)

# Аннотация: зона, где transmission > propagation для 1 Гбит/с
cross_mb = prop_delay_ms * 1_000 / 8 / 1000   # ~4500 МБ — вне диапазона для 1Гбит
# Для 10 Гбит/с: cross = 36 * 10000 / 8 / 1000 = 45 МБ
cross_10g = prop_delay_ms * 10_000 / 8 / 1000
ax.annotate(
    f"Transmission = Propagation\n≈ {cross_10g:.0f} МБ (10 Гбит/с)",
    xy=(cross_10g, prop_delay_ms),
    xytext=(cross_10g + 40, prop_delay_ms + 25),
    fontsize=9,
    color=C_GREEN,
    arrowprops=dict(arrowstyle="->", color=C_GREEN, lw=1.2),
)

plt.savefig(f"{OUT_DIR}/lesson01_tx_vs_prop.png")
plt.close()
print("Сохранён: lesson01_tx_vs_prop.png")

# ──────────────────────────────────────────────────────────────────────────────
# График 3 (опциональный): Время доставки тензора на GPU
#           — пересылка по PCIe vs вычисление, в зависимости от размера батча
# ──────────────────────────────────────────────────────────────────────────────

# Предположения:
#   размер одного примера = 3 * 224 * 224 * 4 байт ≈ 0.602 МБ (float32, RGB 224x224)
#   PCIe 4.0 x16 = 32 ГБ/с (пиковая, реальная ~26 ГБ/с, возьмём 26)
#   Время вычисления ~ 0.08 мс / пример (грубая оценка ResNet-50 на A100)
example_size_mb = 3 * 224 * 224 * 4 / 1024 / 1024   # ≈ 0.575 МБ

pcie_bw_gb_s = 26.0                                  # ГБ/с
pcie_bw_mb_s = pcie_bw_gb_s * 1024                   # МБ/с

compute_per_example_ms = 0.08                        # мс / пример

batch_sizes = np.array([1, 2, 4, 8, 16, 32, 64, 128, 256])

transfer_ms = batch_sizes * example_size_mb / pcie_bw_mb_s * 1000
compute_ms  = batch_sizes * compute_per_example_ms

fig, ax = plt.subplots()

ax.plot(batch_sizes, transfer_ms, color=C_BLUE,  lw=2, marker="o", ms=5,
        label="Пересылка по PCIe 4.0 x16 (26 ГБ/с)")
ax.plot(batch_sizes, compute_ms,  color=C_RED,   lw=2, marker="s", ms=5,
        label="Вычисление (≈ 0.08 мс/пример, A100)")

ax.set_xscale("log", base=2)
ax.set_xticks(batch_sizes)
ax.set_xticklabels(batch_sizes)
ax.set_xlabel("Размер батча (число изображений 224×224 float32)")
ax.set_ylabel("Время, мс")
ax.set_title("Пересылка тензора vs вычисление на GPU\n(ResNet-50, изображения 224×224)")
ax.legend(fontsize=10)

# Аннотация: для малых батчей PCIe незначительна
ax.annotate(
    "При малом батче\nпередача << вычисление",
    xy=(1, transfer_ms[0]),
    xytext=(4, transfer_ms[0] + 4),
    fontsize=9,
    color=C_BLUE,
    arrowprops=dict(arrowstyle="->", color=C_BLUE, lw=1.2),
)

plt.savefig(f"{OUT_DIR}/lesson01_gpu_transfer_vs_compute.png")
plt.close()
print("Сохранён: lesson01_gpu_transfer_vs_compute.png")
