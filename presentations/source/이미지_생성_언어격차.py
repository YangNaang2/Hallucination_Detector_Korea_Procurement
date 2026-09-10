# -*- coding: utf-8 -*-
"""언어 지원 현황 — 한국어만 비어 있음"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

langs = [("영어", 1), ("독일어", 1), ("프랑스어", 1), ("스페인어", 1),
         ("이탈리아어", 1), ("폴란드어", 1), ("중국어", 1), ("한국어", 0)]

fig, ax = plt.subplots(figsize=(6.2, 5.0), dpi=200)
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
fig.patch.set_facecolor("white")
ax.add_patch(FancyBboxPatch((1.5, 1.5), 97, 97,
                            boxstyle="round,pad=0,rounding_size=2.5",
                            fc="#FAFAFA", ec="#111111", lw=2.2))

ax.text(50, 92, "환각 탐지기, 어느 언어까지 왔나", fontsize=12.5,
        weight="bold", color="#111111", ha="center", va="center")
ax.text(50, 85.5, "LettuceDetect 다국어판 지원 현황", fontsize=8.8,
        color="#666666", ha="center", va="center")

y = 77
for name, ok in langs:
    if ok:
        ax.add_patch(FancyBboxPatch((10, y - 3.6), 80, 7.2,
                                    boxstyle="round,pad=0,rounding_size=1.4",
                                    fc="#EAF3EC", ec="#CFE3D5", lw=1.2))
        ax.text(16, y, name, fontsize=10.5, color="#2E7D4F", va="center")
        ax.text(83, y, "지원", fontsize=9.6, color="#2E7D4F",
                weight="bold", ha="right", va="center")
        ax.text(67, y, "✓", fontsize=12, color="#2E7D4F", family="DejaVu Sans",
                weight="bold", ha="center", va="center")
    else:
        ax.add_patch(FancyBboxPatch((7, y - 5.0), 86, 10.0,
                                    boxstyle="round,pad=0,rounding_size=1.6",
                                    fc="#FDEAE8", ec="#B23A32", lw=2.4))
        ax.text(16, y, name, fontsize=13.5, color="#B23A32",
                weight="bold", va="center")
        ax.text(83, y, "없음", fontsize=11.5, color="#B23A32",
                weight="bold", ha="right", va="center")
        ax.text(66, y, "✗", fontsize=14, color="#B23A32", family="DejaVu Sans",
                weight="bold", ha="center", va="center")
    y -= 8.8

ax.plot([10, 90], [7.0, 7.0], lw=1.0, color="#DDDDDD")
ax.text(50, 4.0, "다국어 데이터셋 PsiloQA의 14개 언어에도 한국어는 없다",
        fontsize=8.6, color="#B23A32", weight="bold", ha="center", va="center")

fig.savefig("img_gap.png", dpi=200, bbox_inches="tight", pad_inches=0.03,
            facecolor="white")
print("ok")
