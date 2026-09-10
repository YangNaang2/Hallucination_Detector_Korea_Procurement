# -*- coding: utf-8 -*-
"""C4 템플릿용 아이콘 4종 + 아이디어 이미지 4종 생성"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (Circle, Rectangle, FancyBboxPatch, Ellipse,
                                Polygon, Wedge, FancyArrow)

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

K = "#111111"


# ────────────────────────────── 아이콘 ──────────────────────────────
def icon_canvas():
    fig, ax = plt.subplots(figsize=(2, 2), dpi=200)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_aspect("equal"); ax.axis("off")
    fig.patch.set_alpha(0)
    return fig, ax


def save(fig, name):
    fig.savefig(name, transparent=True, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def icon_bulb():                                   # 아이디어
    fig, ax = icon_canvas()
    ax.add_patch(Circle((50, 58), 21, fill=False, lw=3.4, ec=K))
    ax.add_patch(Rectangle((41, 24), 18, 12, fill=False, lw=3.4, ec=K))
    ax.plot([44, 56], [30, 30], lw=3.0, color=K)
    ax.plot([46, 54], [22, 22], lw=3.0, color=K)
    for a in (35, 90, 145):
        r = np.deg2rad(a)
        ax.plot([50 + 27 * np.cos(r), 50 + 35 * np.cos(r)],
                [58 + 27 * np.sin(r), 58 + 35 * np.sin(r)], lw=3.0, color=K)
    save(fig, "ic_idea.png")


def icon_doc():                                    # 추진배경
    fig, ax = icon_canvas()
    ax.add_patch(FancyBboxPatch((20, 30), 44, 52, boxstyle="round,pad=0,rounding_size=4",
                                fill=False, lw=3.4, ec=K))
    for y in (70, 61, 52):
        ax.plot([29, 55], [y, y], lw=2.8, color=K)
    ax.add_patch(Circle((64, 38), 16, fc="white", ec=K, lw=3.4))
    ax.plot([75, 86], [27, 16], lw=4.0, color=K, solid_capstyle="round")
    save(fig, "ic_bg.png")


def icon_gear():                                   # 주요기능
    fig, ax = icon_canvas()
    for a in range(0, 360, 45):
        r = np.deg2rad(a)
        ax.add_patch(Rectangle((50 + 30 * np.cos(r) - 5, 50 + 30 * np.sin(r) - 5),
                               10, 10, angle=a, rotation_point="center",
                               fc=K, ec=K))
    ax.add_patch(Circle((50, 50), 30, fill=False, lw=3.6, ec=K))
    ax.add_patch(Circle((50, 50), 12, fill=False, lw=3.4, ec=K))
    save(fig, "ic_func.png")


def icon_target():                                 # 기대효과
    fig, ax = icon_canvas()
    for r, lw in ((32, 3.6), (21, 3.2), (10, 3.0)):
        ax.add_patch(Circle((48, 50), r, fill=False, lw=lw, ec=K))
    ax.add_patch(Circle((48, 50), 3.6, fc=K, ec=K))
    ax.add_patch(FancyArrow(74, 76, -20, -20, width=1.6, head_width=8,
                            head_length=9, length_includes_head=True, fc=K, ec=K))
    save(fig, "ic_effect.png")


# ─────────────────────── 1. 환각 판별 목업 ───────────────────────
def img_halluc():
    fig, ax = plt.subplots(figsize=(6.4, 4.9), dpi=200)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.add_patch(FancyBboxPatch((1.5, 1.5), 97, 97, boxstyle="round,pad=0,rounding_size=2.5",
                                fc="#FAFAFA", ec="#111111", lw=2.2))

    ax.text(6, 91, "Q.  청년창업 지원사업, 제가 신청할 수 있나요?",
            fontsize=10.5, weight="bold", color="#111111", va="center")
    ax.plot([6, 94], [86, 86], lw=1.0, color="#CCCCCC")

    rows = [
        ("만 39세 이하 청년이면 신청할 수 있습니다.",      "#B7E4C7", "지지", "#1B7A3E", None),
        ("예비창업자도 대상에 포함됩니다.",                "#FFE59E", "정보 부족", "#8A6A00", None),
        ("지원금은 최대 1억 원까지 받을 수 있습니다.",      "#FFC2C2", "반박", "#B02020", (20.4, 30.2)),
    ]
    y = 76
    for text, bg, tag, tagc, span in rows:
        ax.add_patch(FancyBboxPatch((6, y - 4.6), 63, 8.4,
                                    boxstyle="round,pad=0,rounding_size=1.6",
                                    fc=bg, ec="none"))
        ax.text(7.8, y - 0.4, text, fontsize=9.2, color="#111111", va="center")
        ax.add_patch(FancyBboxPatch((72, y - 3.4), 20, 6.0,
                                    boxstyle="round,pad=0,rounding_size=1.4",
                                    fc="white", ec=tagc, lw=1.6))
        ax.text(82, y - 0.4, tag, fontsize=8.4, color=tagc,
                weight="bold", ha="center", va="center")
        if span:                                   # 틀린 구간만 밑줄
            ax.plot([span[0], span[1]], [y - 3.3, y - 3.3], lw=2.8, color="#B02020")
        y -= 13.5

    ax.plot([6, 94], [33, 33], lw=1.0, color="#CCCCCC")
    ax.text(6, 28, "근거 문서  ·  2026년 청년창업 지원사업 공고",
            fontsize=8.6, weight="bold", color="#555555", va="center")
    ax.add_patch(FancyBboxPatch((6, 6), 88, 17,
                                boxstyle="round,pad=0,rounding_size=1.6",
                                fc="white", ec="#DDDDDD", lw=1.4))
    ax.text(8.5, 18.4, "신청자격 : 공고일 기준 만 39세 이하인 자",
            fontsize=8.8, color="#111111", va="center")
    ax.add_patch(FancyBboxPatch((8.0, 10.0), 40, 5.4,
                                boxstyle="round,pad=0,rounding_size=1.2",
                                fc="#FFD9D9", ec="none"))
    ax.text(8.5, 12.7, "지원금 : 사업화자금 최대 5천만 원",
            fontsize=8.8, weight="bold", color="#B02020", va="center")

    fig.savefig("img_halluc.png", dpi=200, bbox_inches="tight", pad_inches=0.03,
                facecolor="white")
    plt.close(fig)


# ─────────────────────── 2. 베어링 RUL ───────────────────────
def img_bearing():
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
    a1.plot(t, sig, lw=0.45, color="#111111")
    a1.axvspan(7.6, 10, color="#FFC2C2", alpha=0.55, zorder=0)
    a1.text(8.8, sig.max() * 0.86, "결함 진행", fontsize=8.6, weight="bold",
            color="#B02020", ha="center")
    a1.set_title("베어링 진동 신호  ·  시간에 따른 열화", fontsize=9.6,
                 weight="bold", color="#111111", pad=5)
    a1.set_xlabel("운전 시간", fontsize=8.2)
    a1.set_yticks([]); a1.set_xticks([])
    for s in a1.spines.values():
        s.set_color("#BBBBBB")

    c = np.linspace(0, 100, 220)
    true_rul = np.clip(100 - c, 0, None)
    pred = true_rul + rng.normal(0, 3.4, c.size) * (0.35 + 0.9 * c / 100)
    pred = np.clip(pred, 0, None)
    a2.plot(c, true_rul, lw=2.4, color="#111111", label="실제 잔여수명")
    a2.plot(c, pred, lw=1.7, color="#B02020", ls="--", label="예측 잔여수명")
    a2.fill_between(c, pred - 7, pred + 7, color="#B02020", alpha=0.13)
    a2.axhline(15, lw=1.3, color="#1B7A3E", ls=":")
    a2.text(2, 19, "교체 임계값", fontsize=8.0, color="#1B7A3E", weight="bold")
    a2.set_title("잔여수명(RUL) 예측", fontsize=9.6, weight="bold",
                 color="#111111", pad=5)
    a2.set_xlabel("경과 사이클 (%)", fontsize=8.2)
    a2.set_ylabel("잔여수명", fontsize=8.2)
    a2.tick_params(labelsize=7.4)
    a2.legend(fontsize=7.6, frameon=False, loc="upper right")
    for s in a2.spines.values():
        s.set_color("#BBBBBB")

    fig.savefig("img_bearing.png", dpi=200, bbox_inches="tight", pad_inches=0.06,
                facecolor="white")
    plt.close(fig)


# ─────────────────────── 3. 공간 쾌적도 ───────────────────────
def img_space():
    rng = np.random.default_rng(3)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.4, 3.5), dpi=200,
                                 gridspec_kw={"wspace": 0.30})
    fig.patch.set_facecolor("white")

    f, tt = 128, 260
    S = rng.normal(0, 1, (f, tt)) * 0.35
    ff = np.arange(f)[:, None]
    S += 2.6 * np.exp(-((ff - 10) ** 2) / 60)                       # 도로 저주파
    for k in range(0, tt, 46):                                       # 층간 충격음
        S[:, k:k + 6] += 3.1 * np.exp(-((ff - 42) ** 2) / 900)
    S += 1.1 * np.exp(-((ff - 78) ** 2) / 300) * (0.5 + 0.5 * np.sin(np.arange(tt) / 9))
    a1.imshow(np.flipud(S), aspect="auto", cmap="magma",
              extent=[0, 12, 0, 8], vmin=-0.5, vmax=3.2)
    a1.set_title("실내 소음 스펙트로그램", fontsize=9.4, weight="bold", pad=5)
    a1.set_xlabel("시간 (s)", fontsize=8.0)
    a1.set_ylabel("주파수 (kHz)", fontsize=8.0)
    a1.tick_params(labelsize=7.2)

    gx, gy = np.meshgrid(np.linspace(0, 1, 200), np.linspace(0, 1, 200))
    L = (1.35 * np.exp(-(((gx - 0.13) ** 2) / 0.05 + ((gy - 0.62) ** 2) / 0.14))
         + 0.55 * np.exp(-(((gx - 0.82) ** 2) / 0.10 + ((gy - 0.30) ** 2) / 0.10))
         + 0.12)
    im = a2.imshow(L, cmap="inferno", origin="lower", extent=[0, 1, 0, 1], aspect="auto")
    a2.add_patch(Rectangle((0.02, 0.42), 0.055, 0.42, fc="none", ec="white", lw=2.0))
    a2.text(0.10, 0.90, "창", fontsize=8.4, color="white", weight="bold")
    a2.add_patch(Rectangle((0.55, 0.10), 0.33, 0.22, fc="none", ec="white",
                           lw=1.6, ls="--"))
    a2.text(0.715, 0.045, "저조도 구역", fontsize=8.0, color="white",
            weight="bold", ha="center")
    a2.set_title("채광·조도 분포", fontsize=9.4, weight="bold", pad=5)
    a2.set_xticks([]); a2.set_yticks([])
    cb = fig.colorbar(im, ax=a2, fraction=0.045, pad=0.03)
    cb.ax.tick_params(labelsize=6.6)

    fig.savefig("img_space.png", dpi=200, bbox_inches="tight", pad_inches=0.06,
                facecolor="white")
    plt.close(fig)


# ─────────────────────── 4. 알약 식별 ───────────────────────
def img_pill():
    fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=200)
    ax.set_xlim(0, 100); ax.set_ylim(0, 72); ax.axis("off")
    ax.set_aspect("equal")
    fig.patch.set_facecolor("white")
    ax.add_patch(FancyBboxPatch((1, 1), 98, 70, boxstyle="round,pad=0,rounding_size=2",
                                fc="#EFEFEF", ec="#111111", lw=2.0))

    pills = [
        (22, 50, 9.5, 5.4, 0,  "#FFFFFF", "타이레놀 500", "#1B7A3E", "0.97"),
        (52, 54, 6.4, 6.4, 0,  "#FFE9A8", "아스피린 100", "#1B7A3E", "0.94"),
        (77, 48, 8.6, 5.0, 22, "#F2C9C9", "와파린 2mg",   "#B02020", "0.91"),
        (34, 27, 7.2, 4.4, -14, "#CBE3F7", "메트포르민",   "#1B7A3E", "0.89"),
        (66, 27, 6.0, 6.0, 0,  "#E4D6F5", "리피토 10mg",  "#1B7A3E", "0.93"),
    ]
    for cx, cy, w, h, ang, fc, name, boxc, conf in pills:
        ax.add_patch(Ellipse((cx, cy), w * 2, h * 2, angle=ang,
                             fc=fc, ec="#8A8A8A", lw=1.2))
        ax.plot([cx - w * 0.55, cx + w * 0.55], [cy, cy], lw=1.0, color="#9A9A9A")
        bw, bh = w * 2 + 5, h * 2 + 5
        ax.add_patch(Rectangle((cx - bw / 2, cy - bh / 2), bw, bh,
                               fill=False, ec=boxc, lw=2.0))
        lw_ = max(bw, 24.5)
        ax.add_patch(Rectangle((cx - bw / 2, cy + bh / 2), lw_, 3.8,
                               fc=boxc, ec="none"))
        ax.text(cx - bw / 2 + 0.9, cy + bh / 2 + 1.9, f"{name}   {conf}",
                fontsize=5.5, color="white", weight="bold", va="center")

    ax.add_patch(FancyBboxPatch((5, 4), 90, 8.6,
                                boxstyle="round,pad=0,rounding_size=1.6",
                                fc="#FFE3E3", ec="#B02020", lw=1.8))
    ax.text(8, 8.3, "병용금기 감지",
            fontsize=8.6, weight="bold", color="#B02020", va="center")
    ax.text(26, 8.3, "아스피린 + 와파린  →  출혈 위험 증가 (DUR 병용금기)",
            fontsize=8.4, color="#111111", va="center")

    fig.savefig("img_pill.png", dpi=200, bbox_inches="tight", pad_inches=0.03,
                facecolor="white")
    plt.close(fig)


for f in (icon_bulb, icon_doc, icon_gear, icon_target,
          img_halluc, img_bearing, img_space, img_pill):
    f()
    print("ok:", f.__name__)
