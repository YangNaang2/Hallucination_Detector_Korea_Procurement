# -*- coding: utf-8 -*-
"""학습 데이터 → 모델 → 두 갈래 평가 → 격차.
   슬라이드 카드(약 3인치) 안에서 읽혀야 하므로 요소를 줄이고 글자를 키웠다."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

INK, MUTE, RED, GRN, BLU = "#111111", "#6B6B6B", "#B23A32", "#2E7D4F", "#42618A"

fig, ax = plt.subplots(figsize=(6.0, 6.2), dpi=200)
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
fig.patch.set_facecolor("white")
ax.add_patch(FancyBboxPatch((1.2, 1.2), 97.6, 97.6,
                            boxstyle="round,pad=0,rounding_size=2.2",
                            fc="#FCFCFC", ec=INK, lw=2.4))


def box(x, y, w, h, fc, ec, lw=2.0, r=1.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=%s" % r,
                                fc=fc, ec=ec, lw=lw, zorder=2))


def arrow(x0, y0, x1, y1, color=INK, lw=2.2):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>",
                                 mutation_scale=16, lw=lw, color=color,
                                 shrinkA=0, shrinkB=0, zorder=3))


# ① 영어 원본
box(9, 85.0, 82, 9.6, "#FFFFFF", INK)
ax.text(50, 89.8, "영어 RAGTruth  17,790건", fontsize=16.0, weight="bold",
        color=INK, ha="center", va="center")

arrow(50, 84.4, 50, 74.6)
ax.text(53.5, 81.6, "<HAL> 태그째 번역", fontsize=13.0, weight="bold",
        color=INK, ha="left", va="center")
ax.text(53.5, 77.4, "100% 보존 확인", fontsize=12.0, weight="bold",
        color=GRN, ha="left", va="center")

# ② 한국어 데이터
box(9, 63.0, 82, 11.2, "#EEF2F7", "#8FA3BC")
ax.text(50, 70.4, "한국어 RAGTruth", fontsize=16.0, weight="bold",
        color=INK, ha="center", va="center")
ax.text(50, 66.0, "학습 15,090  ·  평가 2,700", fontsize=12.5,
        color=INK, ha="center", va="center")

arrow(50, 62.4, 50, 52.6)

# ③ 모델
box(13, 41.0, 74, 11.2, INK, INK)
ax.text(50, 46.6, "한국어 환각 탐지 모델", fontsize=16.5, weight="bold",
        color="white", ha="center", va="center")

# 두 갈래 평가
arrow(36, 40.4, 26, 32.4)
arrow(64, 40.4, 74, 32.4)

box(4, 20.0, 42, 11.8, "#FFFFFF", BLU)
ax.text(25, 27.4, "평가 ①", fontsize=13.0, weight="bold", color=BLU,
        ha="center", va="center")
ax.text(25, 23.2, "번역 테스트셋", fontsize=13.5, weight="bold", color=INK,
        ha="center", va="center")

box(54, 20.0, 42, 11.8, "#FDEAE8", RED)
ax.text(75, 27.4, "평가 ②", fontsize=13.0, weight="bold", color=RED,
        ha="center", va="center")
ax.text(75, 23.2, "진짜 학사요람", fontsize=13.5, weight="bold", color=RED,
        ha="center", va="center")

arrow(25, 19.4, 38, 13.0)
arrow(75, 19.4, 62, 13.0)

# ④ 격차
box(11, 2.8, 78, 9.6, "#FFF4E0", "#C8912F", 2.4)
ax.text(50, 7.6, "격차  =  ①  ―  ②", fontsize=17.0, weight="bold",
        color="#8A5F13", ha="center", va="center")

fig.savefig("img_pipeline.png", dpi=200, bbox_inches="tight", pad_inches=0.02,
            facecolor="white")
print("saved img_pipeline.png")
