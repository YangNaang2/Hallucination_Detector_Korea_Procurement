# -*- coding: utf-8 -*-
"""베어링 파트 갱신 — 오프라인 RL 정비 정책 최적화. 메인 + 보충 2장용 이미지 3종."""
import matplotlib
matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

INK, MUTE, RED, BLU, GOLD = "#111111", "#6B6B6B", "#B23A32", "#42618A", "#C8912F"


def box(ax, x, y, w, h, fc, ec, lw=2.0, r=1.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=%s" % r,
                                fc=fc, ec=ec, lw=lw, zorder=2))


def arrow(ax, x0, y0, x1, y1, color=INK, lw=2.2):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=16, lw=lw, color=color,
                                 shrinkA=0, shrinkB=0, zorder=3))


# ── 1. 메인 카드 이미지 : 진동 신호 + 정책별 총비용 비교 ──
def img_main():
    rng = np.random.default_rng(7)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.4, 4.9), dpi=200,
                                 gridspec_kw={"height_ratios": [1, 1.05], "hspace": 0.55})
    fig.patch.set_facecolor("white")

    t = np.linspace(0, 10, 4000)
    env = 0.25 + 0.055 * t ** 1.9
    sig = env * np.sin(2 * np.pi * 38 * t) * (1 + 0.5 * np.sin(2 * np.pi * 2.1 * t))
    sig += rng.normal(0, 0.10, t.size)
    imp = np.zeros_like(t)
    for k in np.arange(0.4, 10, 0.34):
        i = np.argmin(abs(t - k))
        imp[i:i + 12] += (0.25 + 0.16 * k) * np.exp(-np.linspace(0, 4, 12))
    sig += imp
    a1.plot(t, sig, lw=0.45, color=INK)
    a1.axvspan(7.6, 10, color="#FFC2C2", alpha=0.55, zorder=0)
    a1.text(8.8, sig.max() * 0.86, "결함 진행", fontsize=8.6, weight="bold",
            color=RED, ha="center")
    a1.set_title("베어링 진동 신호  ·  실측 run-to-failure 이력", fontsize=9.6,
                 weight="bold", color=INK, pad=5)
    a1.set_xlabel("운전 시간", fontsize=8.2)
    a1.set_yticks([]); a1.set_xticks([])
    for s in a1.spines.values():
        s.set_color("#BBBBBB")

    policies = ["고정\n임계값", "이산 MDP\nRL", "오프라인 RL\n(우리)"]
    costs = [100, 78, 54]
    colors = ["#CFCFCF", "#8FA3BC", INK]
    bars = a2.bar(policies, costs, color=colors, width=0.55, zorder=3)
    for b, c in zip(bars, costs):
        a2.text(b.get_x() + b.get_width() / 2, c + 4, str(c), ha="center",
                fontsize=9.6, weight="bold", color=INK)
    a2.set_title("세 정책의 총 비용 비교 개념도 (다운타임+고장위험)",
                 fontsize=9.6, weight="bold", color=INK, pad=5)
    a2.set_ylim(0, 118)
    a2.set_yticks([])
    for s in ["top", "right", "left"]:
        a2.spines[s].set_visible(False)
    a2.spines["bottom"].set_color("#BBBBBB")
    a2.tick_params(labelsize=8.6)

    fig.savefig("img_bearing.png", dpi=200, bbox_inches="tight", pad_inches=0.06,
                facecolor="white")
    print("saved img_bearing.png")


# ── 2. [보충1] 이미 있는 것 vs 우리 자리 ──
def img_gap2():
    fig, ax = plt.subplots(figsize=(6.2, 5.4), dpi=200)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.add_patch(FancyBboxPatch((1.5, 1.5), 97, 97,
                                boxstyle="round,pad=0,rounding_size=2.5",
                                fc="#FAFAFA", ec=INK, lw=2.2))
    ax.text(50, 92.5, "기존 CBM+RL은 무엇을 배우나", fontsize=12.0, weight="bold",
            color=INK, ha="center", va="center")

    box(ax, 8, 58, 84, 24, "#F1F1F1", "#999999", 1.6)
    ax.text(50, 76.5, "기존 CBM+RL", fontsize=10.8, weight="bold",
            color="#555555", ha="center", va="center")
    ax.text(50, 70.3, "사람이 설계한 이산 건강상태", fontsize=9.4,
            color="#555555", ha="center", va="center")
    ax.text(50, 64.3, "가정된 전이확률(MDP) 위에서 학습", fontsize=9.4,
            color="#555555", ha="center", va="center")

    arrow(ax, 50, 58.0, 50, 51.0)
    ax.text(58, 54.2, "우리는 여기를 바꾼다", fontsize=8.8, weight="bold",
            color=RED, ha="left", va="center")

    box(ax, 8, 20, 84, 24, "#FDEAE8", RED, 2.2)
    ax.text(50, 38.5, "우리 방식", fontsize=10.8, weight="bold",
            color=RED, ha="center", va="center")
    ax.text(50, 32.3, "실측 run-to-failure 궤적을", fontsize=9.6,
            color=RED, ha="center", va="center")
    ax.text(50, 26.3, "그대로 오프라인 RL 환경으로 사용", fontsize=9.6,
            weight="bold", color=RED, ha="center", va="center")

    ax.text(50, 7.5, "가정된 시나리오가 아니라, 실제 고장 이력 그대로에서 배운다",
            fontsize=8.6, color=MUTE, ha="center", va="center")

    fig.savefig("img_bearing_gap.png", dpi=200, bbox_inches="tight", pad_inches=0.03,
                facecolor="white")
    print("saved img_bearing_gap.png")


# ── 3. [보충2] 데이터 → 환경 → 정책 비교 파이프라인 ──
def img_pipeline2():
    fig, ax = plt.subplots(figsize=(6.0, 6.2), dpi=200)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.add_patch(FancyBboxPatch((1.2, 1.2), 97.6, 97.6,
                                boxstyle="round,pad=0,rounding_size=2.2",
                                fc="#FCFCFC", ec=INK, lw=2.4))

    box(ax, 9, 85.0, 82, 9.6, "#FFFFFF", INK)
    ax.text(50, 89.8, "IMS · FEMTO-ST 실측 데이터", fontsize=14.5, weight="bold",
            color=INK, ha="center", va="center")

    arrow(ax, 50, 84.4, 50, 74.6)
    ax.text(53.5, 80.6, "run-to-failure 이력을", fontsize=11.6, color=INK,
            ha="left", va="center")
    ax.text(53.5, 77.1, "그대로 환경으로 리플레이", fontsize=11.6, color=INK,
            ha="left", va="center")

    box(ax, 9, 63.0, 82, 11.2, "#EEF2F7", "#8FA3BC")
    ax.text(50, 70.4, "오프라인 RL 환경", fontsize=14.5, weight="bold",
            color=INK, ha="center", va="center")
    ax.text(50, 66.0, "state = RMS·kurtosis 시계열", fontsize=10.2,
            color=INK, ha="center", va="center")
    ax.text(50, 64.6, "action = 가동 유지 / 정비 실시", fontsize=10.2,
            color=INK, ha="center", va="center")

    arrow(ax, 50, 62.4, 50, 52.6)
    ax.text(53.5, 57.5, "Conservative Q-Learning", fontsize=11.6,
            weight="bold", color=INK, ha="left", va="center")

    box(ax, 13, 41.0, 74, 11.2, INK, INK)
    ax.text(50, 46.6, "우리 정비 정책", fontsize=16.0, weight="bold",
            color="white", ha="center", va="center")

    arrow(ax, 36, 40.4, 26, 32.4)
    arrow(ax, 64, 40.4, 74, 32.4)

    box(ax, 4, 20.0, 42, 11.8, "#FFFFFF", BLU)
    ax.text(25, 27.4, "고정 임계값", fontsize=12.6, weight="bold",
            color=BLU, ha="center", va="center")
    ax.text(25, 23.2, "정책", fontsize=13.0, weight="bold",
            color=INK, ha="center", va="center")

    box(ax, 54, 20.0, 42, 11.8, "#EEF2F7", "#8FA3BC")
    ax.text(75, 27.4, "이산 MDP RL", fontsize=12.6, weight="bold",
            color=BLU, ha="center", va="center")
    ax.text(75, 23.2, "정책", fontsize=13.0, weight="bold",
            color=INK, ha="center", va="center")

    arrow(ax, 25, 19.4, 38, 13.0)
    arrow(ax, 75, 19.4, 62, 13.0)

    box(ax, 11, 2.8, 78, 9.6, "#FFF4E0", GOLD, 2.4)
    ax.text(50, 7.6, "같은 베어링으로 총 비용 직접 비교", fontsize=13.4,
            weight="bold", color="#8A5F13", ha="center", va="center")

    fig.savefig("img_bearing_pipeline.png", dpi=200, bbox_inches="tight",
                pad_inches=0.02, facecolor="white")
    print("saved img_bearing_pipeline.png")


img_main()
img_gap2()
img_pipeline2()
