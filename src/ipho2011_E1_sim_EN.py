#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 IPhO 2011 (42nd, Bangkok)  Experimental Problem 1
 "Electrical Blackbox : Capacitive Displacement Sensor"
 ---------------------------------------------------------------------------
 가상 실험실 / Virtual laboratory
   기구 그림은 문제지 사진을 픽셀 단위로 계측한 뒤, 그 형태·치수·색 그대로
   tkinter 도형으로 다시 그린 2D 도면이다 (이미지 파일 없음).
   배선은 실제 실험처럼 리드선 끝을 클릭한 뒤 단자를 클릭해 연결한다.
   나무 블랙박스의 위 극판은 마우스로 직접 밀어 위치를 바꿀 수 있다.
   학생이 보는 것은 멀티미터 표시창(kHz) 과 극판의 mm 눈금뿐이다.
 의존성 : 파이썬 표준 라이브러리(tkinter, Tk 8.6) 뿐.
=============================================================================
"""
LANG = "EN"
import math
import random
import time
import tkinter as tk
from tkinter import ttk

# =========================================================================
#  0.  숨은 참값
# =========================================================================
EPS0    = 8.85e-12
K_DIEL  = 1.5
D_GAP   = 0.20e-3
W_TOOTH = 5.0e-3
B_TOOTH = 60.0e-3
PATTERN = 1
DC_STEP = K_DIEL * EPS0 * B_TOOTH * W_TOOTH / D_GAP
C_OFF   = 60.0e-12
ALPHA0  = 714e-9
C_STRAY = 17.9e-12
TRAVEL_MM = 60.0
DMM_HZ_FS = 19.99
BATT_GOOD = (9.05, 9.55)   # 새것에 가까운 건전지
BATT_WEAK = (6.60, 8.85)   # 다 쓴 건전지
BATT_V0 = 9.28


def new_battery(p_weak=0.30):
    """상자에서 아무거나 하나 꺼낸다.  다 쓴 것이 섞여 있다."""
    lo, hi = BATT_WEAK if random.random() < p_weak else BATT_GOOD
    return round(random.uniform(lo, hi), 2)
BATT_DRAIN = 0.0008

CAPS = [("33J", 34, 33.6e-12), ("68", 68, 67.4e-12),
        ("82J", 84, 83.8e-12), ("151", 150, 149.2e-12)]

S_KO = {
    "title": "IPhO 2011 실험 1 — 전기 블랙박스 : 정전용량식 변위 센서",
    "tab_asm": "1. 조립 · 배선", "tab_bench": "2. 실험대",
    "reset": "처음으로", "newbatt": "새 건전지",
    "note": "실험 노트", "note_add": "기록", "note_clear": "지우기",
    "batt": "9 V 건전지", "caps": "축전기",
    "slide": "위 극판", "dial": "다이얼",
    "t1": "TABLE 1   33J: 34±1   68: 68±1   82J: 84±1   151: 150±1  (pF)",
}
S_EN = {
    "title": "IPhO 2011 Experiment 1 — Electrical Blackbox: Capacitive Displacement Sensor",
    "tab_asm": "1. Assembly · Wiring", "tab_bench": "2. Bench",
    "reset": "Restart", "newbatt": "New battery",
    "note": "Notebook", "note_add": "Log", "note_clear": "Clear",
    "batt": "9 V battery", "caps": "Capacitors",
    "slide": "Upper plate", "dial": "Dial",
    "t1": "TABLE 1   33J: 34±1   68: 68±1   82J: 84±1   151: 150±1  (pF)",
}
S = S_KO if LANG == "KO" else S_EN

C_BG    = "#d6dadb"
C_TRAY  = "#c5cacb"
C_WIRE_R = "#a5251f"
C_WIRE_B = "#17191a"
C_GHOST = "#8b9096"
C_SEL   = "#ffb300"
BOARD_S = 1.00      # 보드 그림 배율
DMM_S   = 0.66      # 멀티미터 그림 배율
CARD_S  = 0.62      # 축전기 카드 배율
BODY_S  = 0.85      # 축전기 본체 배율

# --- 보드 사진(940x346) 안의 좌표 -----------------------------------------
BW, BH   = 1072, 394       # 보드 그림의 기준 크기 (사진 크롭과 같은 좌표계)
# 아래 좌표는 모두 문제지 사진(FIGURE 1 의 지시선 끝)을 실측한 값이다.
JR       = (167, 135)      # 발진기 빨강 바나나 잭   \
JB       = (165, 215)      # 발진기 검정 바나나 잭   / 두 개가 Frequency output
SCREW1   = (292,  81)      # Electrical connectors to the plates (위)   -- 판 아래에서
SCREW2   = (283, 312)      # Electrical connectors to the plates (아래)     극판으로 내려간다
                           #   문제지에서 여기에 무엇을 연결하는 일은 없다.
                           #   블랙박스는 이 나사를 지나 발진기에 이미 물려 있다.
LED      = (76, 177)
SWI      = (33, 281)       # Switch (밑판 왼쪽 아래의 작은 토글)
CLIP_OUT_R = (226, 168)    # 악어클립 리드선이 발진기 상자에서 나오는 곳
CLIP_OUT_B = (226, 206)
BATT_P   = (52, 40)        # 9 V 건전지의 (+) 스냅 단자
BATT_N   = (52, 66)        # 9 V 건전지의 (-) 스냅 단자
BINP     = (24, 116)       # 발진기의 건전지 입력 (+)
BINN     = (24, 142)       # 발진기의 건전지 입력 (-)

# MASTECH 다이얼의 실제 눈금 배열 (각도는 화면 좌표, 0 도 = 오른쪽)
DIAL = [("off",  -90, "OFF"),
        ("v1000", -52, "1000"), ("v200", -30, "200"), ("v20", -8, "20"),
        ("v2",    14, "2"),   ("a20m", 36, "20m"), ("a200m", 58, "200m"),
        ("hz",    82, "Hz"),  ("temp", 104, "\u00b0C"),
        ("c20u", 126, "20\u00b5"), ("c200n", 148, "200n"),
        ("r200k", 170, "200k"), ("r20k", 192, "20k"),
        ("r2k",  214, "2k"),  ("r200", 236, "200")]
DIAL_ORDER = [d[0] for d in DIAL]
DIAL_ANG = {d[0]: d[1] for d in DIAL}
SLIDER_XR = 825            # 위 극판의 오른쪽 끝 (눈금 0 mm 일 때)
SLIDER_Y  = 58
SLIDER_Y2 = 338
SLIDER_W  = 300            # 왼쪽은 뚜껑 밑으로 들어간다
PXMM      = 2.334
CLIP_HOME_R = (330, 258)   # Connectors to capacitor (빨강 악어클립)
CLIP_HOME_B = (412, 196)   # Connectors to capacitor (검정 악어클립)



# =========================================================================
#  1.  물리
# =========================================================================
def C_blackbox(x_mm):
    x = min(max(x_mm, 0.0), TRAVEL_MM - 1e-9)
    n = 1 + int(x // (2 * W_TOOTH * 1e3))
    ph = x % (2 * W_TOOTH * 1e3)
    tri = 1.0 - abs(ph - W_TOOTH * 1e3) / (W_TOOTH * 1e3)
    return C_OFF + n * DC_STEP * tri


V_OSC_MIN = 7.60           # 이 아래에서는 발진기가 아예 뜨지 않는다
V_OSC_OK  = 8.60           # 이 위에서만 규격대로 발진한다


def osc_state(batt_v, connected):
    """0 = 죽음, 1 = 불안정(전압 부족), 2 = 정상"""
    if not connected or batt_v < V_OSC_MIN:
        return 0
    return 2 if batt_v >= V_OSC_OK else 1


def frequency(C_total, batt_v):
    if C_total <= 0:
        return None
    a = ALPHA0
    if batt_v < V_OSC_OK:                       # 전압이 모자라면 느려진다
        a *= 1.0 - 0.16 * (V_OSC_OK - batt_v)
    return a / C_total


# =========================================================================
#  2b.  기구 2D 그림  (문제지 사진을 픽셀 단위로 재어 벡터로 다시 그린 것)
#       좌표는 모두 보드 사진 크롭(1072 x 394) 안의 픽셀 값이다.
# =========================================================================
C_WOOD    = "#7a5a46"      # 밑판 합판
C_WOOD_D  = "#4e392c"
C_LID     = "#6c4c33"      # 블랙박스 뚜껑
C_LID_D   = "#4a3221"
C_SLIDE   = "#8a6a52"      # 미끄러지는 위 극판
PXMM_ART  = 2.334          # 보드 그림에서 1 mm
C_TRACK   = "#5e483c"      # 드러나는 트랙
C_TAPE    = "#0a0a0a"
C_END     = "#6e4d3c"
C_BOX     = "#bec0bb"      # 발진기 케이스
C_BOX_D   = "#9ea09b"
C_JR      = "#9c211e"
C_JB      = "#333331"
C_SCALE   = "#dfe3e6"
C_SCREW   = "#c9ccce"
C_STICK   = "#f4f4f6"
C_BATT    = "#3a3a3e"
C_DMM_Y   = "#f2c231"
C_DMM_K   = "#333533"
C_LCD     = "#96a896"
C_CARD    = "#9cdfdd"


def grain(cv, x0, y0, x1, y1, col, step, sc, tag, slant=6):
    for x in range(int(x0), int(x1), step):
        cv.create_line(sc(x, y0)[0], sc(x, y0)[1],
                       sc(x + slant, y1)[0], sc(x + slant, y1)[1],
                       fill=col, tags=tag)


def art_slider(cv, P, s, slide_mm, tag):
    """미끄러지는 위 극판 (오른쪽 끝이 눈금의 지표)"""
    def rect(x0, y0, x1, y1, **kw):
        a, b = P(x0, y0), P(x1, y1)
        return cv.create_rectangle(a[0], a[1], b[0], b[1], tags=tag, **kw)
    xr = 825 + slide_mm * PXMM_ART
    xl = xr - 300.0                      # 왼쪽은 뚜껑 밑으로 들어간다
    rect(xl, 58, xr, 338, fill=C_SLIDE, outline="#4c3626", width=max(1, int(2 * s)))
    grain(cv, xl + 4, 62, xr - 4, 334, "#7b5c46", 22, P, tag, slant=2)
    a, b = P(xl, 58), P(xr, 68)                       # 위쪽 모서리 광택
    cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#9d7d63", outline="", tags=tag)
    a, b = P(xr - 9, 58), P(xr, 338)                  # 오른쪽 손잡이 모서리
    cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#9d7d63",
                        outline="#4c3626", width=max(1, int(s)), tags=tag)
    a, b = P(xr, 62), P(xr + 5, 342)                  # 그림자
    cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#3d2c22", outline="", tags=tag)
    a, b = P(xr, 340), P(xr, 350)                     # 눈금 지표선
    cv.create_line(a[0], a[1], b[0], b[1], fill="#c0202a", width=max(1, int(2 * s)), tags=tag)



def _art_indicators(cv, P, s, sw_on, led, tag):
    def ovl(x0, y0, x1, y1, **kw):
        a, b = P(x0, y0), P(x1, y1)
        return cv.create_oval(a[0], a[1], b[0], b[1], tags=tag, **kw)

    # LED
    ovl(70, 171, 82, 183, outline="#2c3a2c",
        fill=("#57ff57" if led == 2 else ("#2e7a33" if led == 1 else "#26331f")))
    # 전원 스위치
    sx, sy = SWI
    ang = math.radians(72 if sw_on else 108)          # 레버가 눕는 방향
    a, b = P(sx + 26 * math.cos(ang), sy + 26 * math.sin(ang)), P(sx, sy)
    cv.create_line(a[0], a[1], b[0], b[1], fill="#9aa0a6",
                   width=max(2, int(5 * s)), capstyle="round", tags=tag)
    cv.create_line(a[0], a[1], b[0], b[1], fill="#e2e6ea",
                   width=max(1, int(2 * s)), capstyle="round", tags=tag)
    ovl(sx - 8, sy - 6, sx + 8, sy + 6, fill="#c3c7cb", outline="#6f7376",
        width=max(1, int(1.5 * s)))
    for i in range(4):                                # 널링(요철)
        q = P(sx - 5 + i * 3.4, sy - 5), P(sx - 5 + i * 3.4, sy + 5)
        cv.create_line(q[0][0], q[0][1], q[1][0], q[1][1], fill="#8b9096", tags=tag)
    # 극판 단자 (은색 나사)


def _screws(cv, P, s, tag):
    def ovl(x0, y0, x1, y1, **kw):
        a, b = P(x0, y0), P(x1, y1)
        return cv.create_oval(a[0], a[1], b[0], b[1], tags=tag, **kw)
    for sx, sy in (SCREW1, SCREW2):
        ovl(sx - 9, sy - 9, sx + 9, sy + 9, fill=C_SCREW, outline="#6f7376",
            width=max(1, int(2 * s)))
        a, b = P(sx - 6, sy), P(sx + 6, sy)
        cv.create_line(a[0], a[1], b[0], b[1], fill="#6f7376", tags=tag)


def art_board(cv, ox, oy, s, slide_mm, sw_on, led, tag, part="all"):
    """보드를 위에서 본 2D 그림.  slide_mm = 위 극판의 위치."""
    def P(x, y):
        return (ox + x * s, oy + y * s)

    def rect(x0, y0, x1, y1, **kw):
        a, b = P(x0, y0), P(x1, y1)
        return cv.create_rectangle(a[0], a[1], b[0], b[1], tags=tag, **kw)

    def ovl(x0, y0, x1, y1, **kw):
        a, b = P(x0, y0), P(x1, y1)
        return cv.create_oval(a[0], a[1], b[0], b[1], tags=tag, **kw)

    if part == "ind":
        _art_indicators(cv, P, s, sw_on, led, tag)
        return P

    # ---- 밑판 -------------------------------------------------------
    rect(6, 6, 1062, 382, fill=C_WOOD, outline=C_WOOD_D, width=max(1, int(2 * s)))
    grain(cv, 10, 8, 1058, 380, "#6d4f3d", 44, P, tag)

    # ---- 트랙 (오목한 홈) ------------------------------------------
    rect(736, 52, 972, 342, fill=C_TRACK, outline="#463529", width=max(1, int(2 * s)))
    grain(cv, 740, 56, 970, 340, "#544035", 30, P, tag, slant=3)
    # 트랙 오른쪽에 붙은 검은 테이프 (고정)
    rect(890, 60, 970, 112, fill=C_TAPE, outline="")
    rect(890, 285, 970, 338, fill=C_TAPE, outline="")

    # ---- mm 눈금자 (트랙 아래, 밑판에 붙어 있다) ----------------------
    rect(736, 346, 982, 384, fill=C_SCALE, outline="#9aa0a4")
    for v in range(-38, 68):
        xx = 825 + v * PXMM_ART
        if not (740 <= xx <= 980):
            continue
        h = 17 if v % 10 == 0 else (12 if v % 5 == 0 else 7)
        a, b = P(xx, 348), P(xx, 348 + h)
        cv.create_line(a[0], a[1], b[0], b[1], fill="#1a1a1a",
                       width=max(1, int((2 if v % 10 == 0 else 1) * s)), tags=tag)
        if v % 10 == 0 and 0 <= v <= 60:
            q = P(xx, 374)
            cv.create_text(q[0], q[1], text=str(v), fill="#1a1a1a",
                           font=("Helvetica", max(5, int(9 * s))), tags=tag)

    if part == "bot":
        return P

    if part != "top":
        art_slider(cv, P, s, slide_mm, tag)
    if part == "slider":
        return P

    # ---- 블랙박스 뚜껑 -----------------------------------------------
    rect(300, 4, 736, 358, fill=C_LID, outline=C_LID_D, width=max(1, int(2 * s)))
    grain(cv, 304, 8, 732, 354, "#77543a", 38, P, tag)
    rect(462, 143, 600, 212, fill=C_STICK, outline="#d6d6d8")
    q = P(531, 163)
    cv.create_text(q[0], q[1], text="IPhO 42", fill="#c0166b",
                   font=("Helvetica", max(6, int(13 * s)), "bold"), tags=tag)
    q = P(531, 190)
    cv.create_text(q[0], q[1], text="Bangkok 2011", fill="#4a4a4a",
                   font=("Helvetica", max(5, int(8 * s))), tags=tag)

    # ---- 오른쪽 프레임 레일 + 끝 블록 --------------------------------
    rect(970, 46, 990, 348, fill="#59402f", outline="#3f2c1f", width=max(1, int(s)))
    rect(988, 2, 1062, 386, fill=C_END, outline=C_WOOD_D, width=max(1, int(2 * s)))
    grain(cv, 992, 6, 1058, 382, "#7a5745", 26, P, tag, slant=2)

    # ---- 발진기 상자 --------------------------------------------------
    rect(6, 264, 228, 276, fill=C_BOX_D, outline="")
    rect(4, 95, 226, 268, fill=C_BOX, outline="#93958f", width=max(1, int(2 * s)))
    rect(4, 95, 226, 107, fill="#d2d4cf", outline="")
    # 9 V 건전지
    rect(47, 26, 180, 93, fill=C_BATT, outline="#232326", width=max(1, int(2 * s)))
    rect(64, 36, 164, 78, fill="#ececed", outline="#b9b9ba")
    for i in range(9):
        xx = 68 + i * 10.4
        a, b = P(xx, 40), P(xx, 72)
        cv.create_line(a[0], a[1], b[0], b[1], fill="#1c1c1c",
                       width=max(1, int((2 if i % 3 else 1) * s)), tags=tag)
    q = P(114, 86)
    cv.create_text(q[0], q[1], text="9V", fill="#e4e4e6",
                   font=("Helvetica", max(6, int(10 * s)), "bold"), tags=tag)
    for tx, ty, col in ((BINP[0], BINP[1], "#a5251f"), (BINN[0], BINN[1], "#1a1a1a")):
        ovl(tx - 8, ty - 8, tx + 8, ty + 8, fill="#c9ccce",
            outline="#6f7376", width=max(1, int(2 * s)))
        ovl(tx - 4, ty - 4, tx + 4, ty + 4, fill=col, outline="")
    # 잭
    ovl(148, 116, 186, 154, fill=C_JR, outline="#6d201a", width=max(1, int(2 * s)))
    ovl(158, 126, 176, 144, fill="#3a1512", outline="")
    ovl(146, 196, 184, 234, fill=C_JB, outline="#1c1c1a", width=max(1, int(2 * s)))
    ovl(156, 206, 174, 224, fill="#131315", outline="")
    _screws(cv, P, s, tag)
    if part != "top":
        _art_indicators(cv, P, s, sw_on, led, tag)
    return P


def art_dmm(cv, ox, oy, s, dial, disp, unit, tag):
    """MASTECH 디지털 멀티미터.  기준 크기 264 x 441 px."""
    def P(x, y):
        return (ox + x * s, oy + y * s)

    def rr(x0, y0, x1, y1, r, **kw):
        a, b, c_, d = P(x0 + r, y0), P(x1 - r, y0), P(x1, y0 + r), P(x1, y1 - r)
        e, f, g, h = P(x1 - r, y1), P(x0 + r, y1), P(x0, y1 - r), P(x0, y0 + r)
        cv.create_polygon(a[0], a[1], b[0], b[1], c_[0], c_[1], d[0], d[1],
                          e[0], e[1], f[0], f[1], g[0], g[1], h[0], h[1],
                          smooth=True, tags=tag, **kw)

    rr(2, 4, 262, 437, 20, fill=C_DMM_Y, outline="#c79a1c", width=max(1, int(2 * s)))
    rr(18, 20, 246, 400, 12, fill=C_DMM_K, outline="#1d1f1d", width=max(1, int(2 * s)))
    rr(46, 36, 218, 112, 6, fill=C_LCD, outline="#5d6b5d", width=max(1, int(2 * s)))
    q = P(212, 76)
    cv.create_text(q[0], q[1], text=disp, anchor="e", fill="#161d16",
                   font=("Courier New", max(8, int(30 * s)), "bold"), tags=tag)
    q = P(212, 102)
    cv.create_text(q[0], q[1], text=unit, anchor="e", fill="#161d16",
                   font=("Helvetica", max(5, int(10 * s)), "bold"), tags=tag)
    a, b = P(28, 126), P(60, 144)
    cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#cc2b22", outline="#7d1a15", tags=tag)
    q = P(152, 122)
    cv.create_text(q[0], q[1], text="AUTO POWER OFF", fill="#4aa3e0",
                   font=("Helvetica", max(4, int(9 * s)), "bold"), tags=tag)
    # 다이얼
    cx, cy, R = 128.0, 246.0, 48.0
    for nm, deg, lbl in DIAL:                              # 실제 눈금 배열
        t = math.radians(deg)
        a = P(cx + (R + 11) * math.cos(t), cy + (R + 11) * math.sin(t))
        cv.create_oval(a[0] - 1.8 * s, a[1] - 1.8 * s, a[0] + 1.8 * s, a[1] + 1.8 * s,
                       fill="#e8e8e8", outline="", tags=tag)
        col = "#ff9a3c" if nm in ("hz", "off") else "#d8d8d8"
        q = P(cx + (R + 23) * math.cos(t), cy + (R + 23) * math.sin(t))
        cv.create_text(q[0], q[1], text=lbl, fill=col,
                       font=("Helvetica", max(4, int(8 * s)), "bold"), tags=tag)
    a, b = P(cx - R - 6, cy - R - 6), P(cx + R + 6, cy + R + 6)
    cv.create_oval(a[0], a[1], b[0], b[1], fill="#232522", outline="#4a4d4a", tags=tag)
    a, b = P(cx - R, cy - R), P(cx + R, cy + R)
    cv.create_oval(a[0], a[1], b[0], b[1], fill="#2b2d2b", outline="#111", tags=tag)
    for i in range(10):                                    # 손잡이의 홈
        t = math.radians(i * 36)
        a = P(cx + R * 0.62 * math.cos(t), cy + R * 0.62 * math.sin(t))
        b = P(cx + R * 0.94 * math.cos(t), cy + R * 0.94 * math.sin(t))
        cv.create_line(a[0], a[1], b[0], b[1], fill="#3d403d", tags=tag)
    ang = math.radians(DIAL_ANG.get(dial, -90))
    a, b = P(cx, cy), P(cx + R * 0.86 * math.cos(ang), cy + R * 0.86 * math.sin(ang))
    cv.create_line(a[0], a[1], b[0], b[1], fill="#f2f2f2", width=max(2, int(5 * s)), tags=tag)
    # 잭
    for jx, name in ((44, "10A"), (98, "mA"), (156, "COM"), (212, "V\u03a9Hz")):
        a, b = P(jx - 15, 316), P(jx + 15, 346)
        cv.create_oval(a[0], a[1], b[0], b[1], fill="#7a1f1f", outline="#c8c8c8",
                       width=max(1, int(2 * s)), tags=tag)
        a, b = P(jx - 8, 323), P(jx + 8, 339)
        cv.create_oval(a[0], a[1], b[0], b[1], fill="#1a1a1a", outline="", tags=tag)
        q = P(jx, 358)
        cv.create_text(q[0], q[1], text=name, fill="#e8e8e8",
                       font=("Helvetica", max(4, int(9 * s)), "bold"), tags=tag)
    a, b = P(26, 376), P(126, 396)
    cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#13447c", outline="", tags=tag)
    q = P(76, 386)
    cv.create_text(q[0], q[1], text="MASTECH", fill="#ffffff",
                   font=("Helvetica", max(5, int(11 * s)), "bold"), tags=tag)
    a, b = P(214, 252), P(238, 298)
    cv.create_rectangle(a[0], a[1], b[0], b[1], fill="#2f7d3a", outline="#1d4f25", tags=tag)


def art_cap_card(cv, cx, cy, s, code, taken, tag):
    """부품 상자에 있는 녹색 카드.  본체를 꺼내가면 자리가 빈다."""
    W, H = 118.0, 150.0

    def P(x, y):
        return (cx + (x - W / 2) * s, cy + (y - H / 2) * s)

    a, b = P(2, 2), P(116, 148)
    cv.create_rectangle(a[0], a[1], b[0], b[1], fill=C_CARD, outline="#5aa8a6",
                        width=max(1, int(2 * s)), tags=tag)
    q = P(59, 26)
    cv.create_text(q[0], q[1], text=code, fill="#1b3f8b",
                   font=("Helvetica", max(6, int(24 * s)), "bold"), tags=tag)
    if taken:
        a, b = P(38, 78), P(80, 118)
        cv.create_oval(a[0], a[1], b[0], b[1], fill="", outline="#7fbfbd",
                       dash=(3, 2), tags=tag)
    else:
        art_cap_body(cv, cx, cy + 24 * s, s * 1.05, code, tag)


def art_cap_body(cv, cx, cy, s, code, tag, leads=True):
    """세라믹 원판 축전기 본체.  원판에 용량 코드가 작게 인쇄되어 있다."""
    W, H = 80.0, 90.0

    def P(x, y):
        return (cx + (x - W / 2) * s, cy + (y - H / 2) * s)

    if leads:
        for x0, x1 in ((34, 6), (46, 74)):
            a, m, b = P(x0, 46), P((x0 + x1) / 2, 68), P(x1, 88)
            cv.create_line(a[0], a[1], m[0], m[1], b[0], b[1], fill="#9aa5aa",
                           width=max(1, int(3 * s)), smooth=True, tags=tag)
    a, b = P(16, 12), P(64, 54)
    cv.create_oval(a[0], a[1], b[0], b[1], fill="#8b7a4e", outline="#5f5433",
                   width=max(1, int(1.5 * s)), tags=tag)
    a, b = P(22, 17), P(44, 31)
    cv.create_oval(a[0], a[1], b[0], b[1], fill="#a2905f", outline="", tags=tag)
    q = P(40, 34)
    cv.create_text(q[0], q[1], text=code, fill="#241d0e",
                   font=("Helvetica", max(4, int(13 * s)), "bold"), tags=tag)


# =========================================================================
#  2.  실험 상태 (두 탭이 공유)
# =========================================================================
class Scene:
    def __init__(self):
        self.reset()

    def reset(self):
        self.sw_on = False
        self.dial = "off"                       # off / dcv / hz
        self.probe = {"r": None, "b": None}     # None | "JR" | "JB"
        # 물리지 않은 리드선 끝이 놓인 자리 (캔버스 좌표)
        self.free_probe = {"r": None, "b": None}
        self.solver = None                      # 결선 해석기 (WorkTab 이 넣어 준다)
        self.slide = 0.0
        # 건전지 스냅 리드선 :  None | "BINP" | "BINN"
        self.batt = {"p": None, "n": None}
        self.free_batt = {"p": None, "n": None}
        self.caps = {}                          # i -> [x, y]  실험대에 꺼내 놓은 축전기
        self.clip_pos = {"r": None, "b": None}  # 악어클립 집게가 놓인 자리
        self.stack = {}                         # i -> 다리를 함께 묶은 축전기
        self.batt_v = new_battery()
        self.jit = 0.0

    @property
    def batt_in(self):
        return self.batt["p"] == "BINP" and self.batt["n"] == "BINN"

    # -- 회로 ---------------------------------------------------------
    def meter_ok(self):
        return {self.probe["r"], self.probe["b"]} == {"JR", "JB"}

    def load_C(self):
        """발진기의 축전기 자리에 실제로 무엇이 붙어 있는지.
           집게가 아무 다리도 물고 있지 않으면 블랙박스가 붙어 있다."""
        return self.solver() if self.solver else None

    def osc(self):
        return osc_state(self.batt_v, self.batt_in) if self.sw_on else 0

    def display(self):
        d = self.dial
        if d == "off":
            return ""
        if d.startswith("v"):                    # 직류 전압
            fs = {"v1000": 1000.0, "v200": 200.0, "v20": 20.0, "v2": 2.0}[d]
            v = self.batt_v if {self.probe["r"], self.probe["b"]} == {"BATP", "BATN"} else 0.0
            if v > fs:
                return "1  "
            dec = 2 if fs <= 20 else (1 if fs <= 200 else 0)
            return "%.*f" % (dec, v)
        if d.startswith("r"):                    # 저항 : 열려 있으면 넘침
            return "1  "
        if d in ("temp", "c20u", "c200n") or d.startswith("a"):
            return "0.00"
        # --- 주파수 ---
        if not self.meter_ok():
            return "0.00"
        st = self.osc()
        if st == 0:
            return "0.00"
        C = self.load_C()
        if C is None or C <= 0:
            return "1  "
        f = frequency(C + C_STRAY, self.batt_v) / 1000.0 + self.jit
        return "1  " if f > DMM_HZ_FS else "%.2f" % f

    def unit(self):
        d = self.dial
        if d == "off":
            return ""
        if d.startswith("v"):
            return "V"
        if d.startswith("r"):
            return "\u03a9"
        if d.startswith("a"):
            return "mA"
        if d.startswith("c"):
            return "nF"
        if d == "temp":
            return "\u00b0C"
        return "kHz"

    def ready(self):
        return self.osc() == 2 and self.dial == "hz" and self.meter_ok()


# =========================================================================
#  3.  보드·계기 그리기 (두 탭 공용)
# =========================================================================
class Board:
    """보드 사진 + 움직이는 위 극판 + 배선을 그린다."""

    def __init__(self, cv, ox, oy, sc):
        self.cv, self.ox, self.oy, self.sc = cv, ox, oy, sc

    def X(self, a):
        return self.ox + a * self.sc

    def Y(self, a):
        return self.oy + a * self.sc

    def term_xy(self, name):
        return {"JR": JR, "JB": JB, "BINP": BINP, "BINN": BINN}[name]

    def draw_static(self, S_, dmm_at):
        cv = self.cv
        art_board(cv, self.ox, self.oy, self.sc, S_.slide, S_.sw_on,
                  S_.osc(), "st1", part="bot")
        art_board(cv, self.ox, self.oy, self.sc, S_.slide, S_.sw_on,
                  S_.osc(), "st2", part="top")
        if dmm_at:
            art_dmm(cv, dmm_at[0], dmm_at[1], DMM_S, S_.dial, "", "", "st2")

    def draw(self, sc_state, sel=None, dmm_at=None):
        cv, S_ = self.cv, sc_state

        def P(x, y):
            return (self.ox + x * self.sc, self.oy + y * self.sc)
        art_slider(cv, P, self.sc, S_.slide, "dy")
        cv.tag_raise("st2")
        art_board(cv, self.ox, self.oy, self.sc, S_.slide, S_.sw_on,
                  S_.osc(), "dy", part="ind")
        if dmm_at:
            mx, my = dmm_at
            cv.create_text(mx + 212 * DMM_S, my + 76 * DMM_S, text=S_.display(),
                           anchor="e", fill="#161d16", tags="dy",
                           font=("Courier New", max(8, int(30 * DMM_S)), "bold"))
            cv.create_text(mx + 212 * DMM_S, my + 102 * DMM_S, text=S_.unit(),
                           anchor="e", fill="#161d16", tags="dy",
                           font=("Helvetica", max(5, int(10 * DMM_S)), "bold"))

        # --- 악어클립 리드선 (발진기 -> 시료) --------------------------
        for k, col, src in (("p", "#a5251f", BATT_P), ("n", "#1a1a1a", BATT_N)):
            px, py = self.batt_end(k)
            sx, sy = self.X(src[0]), self.Y(src[1])
            cv.create_line(sx, sy, (sx + px) / 2, (sy + py) / 2 - 26, px, py,
                           fill=col, width=4, smooth=True, tags="dy")
            cv.create_oval(px - 5, py - 5, px + 5, py + 5, fill=col,
                           outline="#e0e0e0", width=2, tags="dy")
        for k, col, src in (("r", C_WIRE_R, CLIP_OUT_R), ("b", C_WIRE_B, CLIP_OUT_B)):
            px, py = self.clip_end(k)
            sx, sy = self.X(src[0]), self.Y(src[1])
            cv.create_line(sx, sy, (sx + px) / 2 - 20, (sy + py) / 2 + 34, px, py,
                           fill=col, width=5, smooth=True, tags="dy")
            self.clip_head(px, py, col, sel == ("clip", k))

        # --- 멀티미터 --------------------------------------------------
        if dmm_at:
            mx, my = dmm_at
            for k, col, jx in (("b", C_WIRE_B, mx + 156 * DMM_S),
                               ("r", C_WIRE_R, mx + 212 * DMM_S)):
                y0 = my + 346 * DMM_S
                px, py = self.probe_end(k)
                cv.create_line(jx, y0, jx, y0 + 34, (jx + px) / 2, py + 70, px, py,
                               fill=col, width=4, smooth=True, tags="dy")
                self.probe_head(px, py, col, sel == ("probe", k))
        return

    clip_end = None
    probe_end = None
    batt_end = None


    def clip_head(self, x, y, col, hot):
        cv = self.cv
        cv.create_polygon(x - 15, y - 7, x + 8, y - 2, x - 15, y + 3,
                          fill=col, outline="#111", tags="dy")
        cv.create_polygon(x - 15, y + 9, x + 8, y + 4, x - 15, y - 1,
                          fill=col, outline="#111", tags="dy")

    def probe_head(self, x, y, col, hot):
        cv = self.cv
        cv.create_line(x, y, x - 18, y + 14, fill=col, width=6, capstyle="round", tags="dy")
        cv.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#d8d8d8", outline="#555", tags="dy")

    def ghost(self, x, y, w, h):
        self.cv.create_rectangle(self.X(x) - w / 2, self.Y(y) - h / 2,
                                 self.X(x) + w / 2, self.Y(y) + h / 2,
                                 outline=C_GHOST, dash=(6, 4), width=2, tags="bd")

    # -- 클릭 판정 ------------------------------------------------------
    def hit_term(self, ex, ey):
        for n in ("JR", "JB", "BINP", "BINN"):
            p = self.term_xy(n)
            if math.hypot(ex - self.X(p[0]), ey - self.Y(p[1])) < 15:
                return n
        return None

    def hit_switch(self, ex, ey):
        return (abs(ex - self.X(SWI[0])) < 18 * self.sc
                and -12 * self.sc < ey - self.Y(SWI[1]) < 30 * self.sc)

    def hit_dial(self, ex, ey, dmm_at):
        if not dmm_at:
            return None
        kx, ky = dmm_at[0] + 128 * DMM_S, dmm_at[1] + 232 * DMM_S
        d = math.hypot(ex - kx, ey - ky)
        if d > 80 * DMM_S:
            return None
        a = math.degrees(math.atan2(ey - ky, ex - kx))
        best, bd = "off", 1e9
        for nm, deg, _ in DIAL:
            dd = abs((a - deg + 180) % 360 - 180)
            if dd < bd:
                bd, best = dd, nm
        return best

    def hit_slider(self, ex, ey, slide):
        xr = self.X(SLIDER_XR + slide * PXMM)
        return xr - SLIDER_W * self.sc < ex < xr + 6 and \
            self.Y(SLIDER_Y) < ey < self.Y(SLIDER_Y2)

    def slide_from(self, ex, off):
        return min(TRAVEL_MM, max(0.0, round(((ex - off) - self.ox) / self.sc
                                             - SLIDER_X0, 1) / PXMM))


# =========================================================================
#  4.  탭
# =========================================================================
class WorkTab(ttk.Frame):
    W, H = 1340, 760

    def __init__(self, master, app, bench=True):
        super().__init__(master)
        self.app, self.bench = app, True
        self.cv = tk.Canvas(self, width=self.W, height=self.H, bg=C_BG,
                            highlightthickness=0)
        self.cv.pack(side="left", fill="both", expand=True)
        self.board = Board(self.cv, 16, 14, BOARD_S)
        self.board.clip_end = self.clip_end
        self.app.sc.solver = self.solve
        self.board.probe_end = self.probe_end
        self.board.batt_end = self.batt_end
        self.sel = None
        self.drag = None
        self.dmm_at = (1132, 44)
        self.build_panel()
        self.cv.bind("<MouseWheel>", self.wheel)
        self.cv.bind("<Button-4>", lambda e: self.wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self.wheel(e, -1))
        self.cv.bind("<ButtonPress-1>", self.press)
        self.cv.bind("<B1-Motion>", self.motion)
        self.cv.bind("<ButtonRelease-1>", self.release)
        self._job = None
        self.bind("<Destroy>", self._stop)
        self.tick()

    # ------------------------------------------------------------------
    def build_panel(self):
        rp = ttk.Frame(self, padding=8)
        rp.pack(side="right", fill="y")
        ttk.Button(rp, text=S["newbatt"], command=self.new_batt).pack(fill="x", pady=2)
        ttk.Button(rp, text=S["reset"], command=self.reset).pack(fill="x", pady=2)

    def new_batt(self):
        self.app.sc.batt_v = new_battery(0.15)

    def reset(self):
        self.app.sc.reset()
        self.sel = None

    # ---- 레일(축전기 병렬 연결대) -------------------------------------
    TOUCH = 20.0                    # 이 거리 안이면 도체가 서로 닿은 것으로 본다

    def root(self, i):
        sc = self.app.sc
        seen = set()
        while i in sc.stack and i not in seen:
            seen.add(i)
            i = sc.stack[i]
        return i

    def lead_xy(self, i, which):
        x, y = self.app.sc.caps[self.root(i)]
        return (x + (-34 if which == "A" else 34) * BODY_S, y + 43 * BODY_S)

    def batt_end(self, k):
        sc = self.app.sc
        if self.drag and self.drag[0] == "batt" and self.drag[1] == k:
            return (self.drag[2], self.drag[3])
        if sc.batt[k]:
            p = self.board.term_xy(sc.batt[k])
            return (self.board.X(p[0]), self.board.Y(p[1]))
        if sc.free_batt[k]:
            return sc.free_batt[k]
        h = (208, 16) if k == "p" else (252, 16)
        return (self.board.X(h[0]), self.board.Y(h[1]))

    def probe_end(self, k):
        sc = self.app.sc
        if self.drag and self.drag[0] == "probe" and self.drag[1] == k:
            return (self.drag[2], self.drag[3])
        if sc.probe[k] in ("BATP", "BATN"):
            return self.batt_end("p" if sc.probe[k] == "BATP" else "n")
        if sc.probe[k]:
            p = self.board.term_xy(sc.probe[k])
            return (self.board.X(p[0]), self.board.Y(p[1]))
        if sc.free_probe[k]:
            return sc.free_probe[k]
        jx = self.dmm_at[0] + (156 if k == "b" else 212) * DMM_S
        return (jx - 34 if k == "b" else jx + 30,
                self.dmm_at[1] + 412 * DMM_S)

    def targets_for(self, kind):
        """끌어다 놓을 수 있는 자리 : [(x, y, 이름), ...]"""
        b = self.board
        out = []
        if kind == "probe":
            for n in ("JR", "JB"):
                p = b.term_xy(n)
                out.append((b.X(p[0]), b.Y(p[1]), n))
            for k, n in (("p", "BATP"), ("n", "BATN")):
                x, y = self.batt_end(k)
                out.append((x, y, n))
        elif kind == "batt":
            for n in ("BINP", "BINN"):
                p = b.term_xy(n)
                out.append((b.X(p[0]), b.Y(p[1]), n))
        else:
            for i in self.app.sc.caps:
                for w_ in ("A", "B"):
                    lx, ly = self.lead_xy(i, w_)
                    out.append((lx, ly, "c%s%d" % (w_, i)))
        return out

    def snap(self, kind, x, y):
        best, bd = None, 1e9
        for tx, ty, n in self.targets_for(kind):
            d = math.hypot(x - tx, y - ty)
            if d < 22 and d < bd:
                bd, best = d, n
        return best

    def clip_end(self, k):
        sc = self.app.sc
        if self.drag and self.drag[0] == "clip" and self.drag[1] == k:
            return (self.drag[2], self.drag[3])
        if sc.clip_pos[k]:
            return tuple(sc.clip_pos[k])
        h = CLIP_HOME_R if k == "r" else CLIP_HOME_B
        return (self.board.X(h[0]), self.board.Y(h[1]))

    # ---- 결선 해석 : 가까이 닿은 도체끼리 이어 붙인다 -----------------
    def solve(self):
        sc = self.app.sc
        pts = {"R": self.clip_end("r"), "B": self.clip_end("b")}
        for i in sc.caps:
            pts["cA%d" % i] = self.lead_xy(i, "A")
            pts["cB%d" % i] = self.lead_xy(i, "B")
        par = {}

        def find(a):
            par.setdefault(a, a)
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a

        def uni(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                par[ra] = rb
        keys = list(pts)
        for ii in range(len(keys)):
            for jj in range(ii + 1, len(keys)):
                ka, kb = keys[ii], keys[jj]
                if ka in ("R", "B") and kb in ("R", "B"):
                    continue                     # 두 집게가 직접 닿는 일은 없다
                (ax, ay), (bx, by) = pts[ka], pts[kb]
                if (ax - bx) ** 2 + (ay - by) ** 2 < self.TOUCH ** 2:
                    uni(ka, kb)
        gr, gb = find("R"), find("B")
        held = any(find("cA%d" % i) in (gr, gb) or find("cB%d" % i) in (gr, gb)
                   for i in sc.caps)
        if not held:                             # 아무것도 물지 않았다 -> 블랙박스
            return C_blackbox(sc.slide)
        if gr == gb:
            return None
        tot = 0.0
        for i in sc.caps:
            if {find("cA%d" % i), find("cB%d" % i)} == {gr, gb}:
                tot += CAPS[i][2]
        return tot if tot > 0 else None

    def joints(self):
        """서로 닿아 있는 도체 지점 목록 (땜납 자국처럼 표시한다)"""
        sc = self.app.sc
        pts = [self.clip_end("r"), self.clip_end("b")]
        for i in sc.caps:
            pts.append(self.lead_xy(i, "A"))
            pts.append(self.lead_xy(i, "B"))
        out = []
        for ii in range(len(pts)):
            for jj in range(ii + 1, len(pts)):
                if ii < 2 and jj < 2:
                    continue
                (ax, ay), (bx, by) = pts[ii], pts[jj]
                if (ax - bx) ** 2 + (ay - by) ** 2 < self.TOUCH ** 2:
                    out.append(((ax + bx) / 2, (ay + by) / 2))
        return out

    def tray_xy(self, i):
        return (110 + i * 100, 700)

    # ------------------------------------------------------------------
    def redraw(self, full=True):
        cv, sc = self.cv, self.app.sc
        if full:
            cv.delete("all")
            cv.create_rectangle(0, 0, self.W, self.H, fill=C_BG, outline="",
                                tags="st1")
            cv.create_rectangle(0, 624, 1080, self.H, fill=C_TRAY, outline="",
                                tags="st1")
            cv.create_line(0, 624, 1080, 624, fill="#a9afb0", width=2, tags="st1")
            cv.create_text(12, 630, text=S["t1"], anchor="nw", fill="#333",
                           font=("Helvetica", 9), tags="st1")
            self.board.draw_static(sc, self.dmm_at)
        else:
            cv.delete("dy")
        self.board.draw(sc, self.sel, self.dmm_at)

        # --- 실험대에 꺼내 놓은 축전기 --------------------------------
        for i, (x, y) in sc.caps.items():
            if self.drag and self.drag[0] == "card" and self.drag[1] == i:
                continue
            for w_ in ("A", "B"):               # 다리를 공유 지점까지 구부린다
                lx, ly = self.lead_xy(i, w_)
                sx = x + (-6 if w_ == "A" else 6) * BODY_S
                cv.create_line(sx, y + 20 * BODY_S,
                               (sx + lx) / 2, y + 40 * BODY_S, lx, ly,
                               fill="#9aa5aa", width=3, smooth=True, tags="dy")
            art_cap_body(cv, x, y, BODY_S, CAPS[i][0], "dy", leads=False)
        for i in sc.caps:
            for w_ in ("A", "B"):
                lx, ly = self.lead_xy(i, w_)
                cv.create_oval(lx - 4, ly - 4, lx + 4, ly + 4,
                               fill="#c9ccce", outline="#6f7376", tags="dy")
        for jx, jy in self.joints():             # 서로 닿은 자리
            cv.create_oval(jx - 6, jy - 6, jx + 6, jy + 6,
                           fill="#d8b24a", outline="#8a6b1f", tags="dy")

        # --- 부품 상자 ------------------------------------------------
        for i in range(4):
            x, y = self.tray_xy(i)
            art_cap_card(cv, x, y, CARD_S, CAPS[i][0], i in sc.caps, "dy")
        if self.drag and self.drag[0] == "card":
            art_cap_body(cv, self.drag[2], self.drag[3], BODY_S,
                         CAPS[self.drag[1]][0], "dy")
        if self.drag and self.drag[0] in ("probe", "clip", "batt"):
            for tx, ty, n in self.targets_for(self.drag[0]):
                cv.create_oval(tx - 13, ty - 13, tx + 13, ty + 13,
                               outline=C_SEL, width=2, dash=(3, 2), tags="dy")


    def press(self, e):
        self._press(e)
        if self.app.sc.ready():
            self.app.unlock_bench()
        self.redraw()

    def _press(self, e):
        sc = self.app.sc
        b = self.board
        # 1) 리드선 끝을 잡는다 (잡는 순간 물려 있던 곳에서 떨어진다)
        for k in ("r", "b"):
            px, py = self.probe_end(k)
            if math.hypot(e.x - px, e.y - py) < 17:
                sc.probe[k] = None
                self.drag = ["probe", k, e.x, e.y]
                return
        for k in ("r", "b"):
            px, py = self.clip_end(k)
            if math.hypot(e.x - px, e.y - py) < 17:
                self.drag = ["clip", k, e.x, e.y]
                return
        for k in ("p", "n"):
            px, py = self.batt_end(k)
            if math.hypot(e.x - px, e.y - py) < 15:
                sc.batt[k] = None
                self.drag = ["batt", k, e.x, e.y]
                return
        # 2) 스위치 / 다이얼
        if b.hit_switch(e.x, e.y):
            sc.sw_on = not sc.sw_on
            return
        d = b.hit_dial(e.x, e.y, self.dmm_at)
        if d:
            sc.dial = d
            return
        # 3) 위 극판 끌기
        if b.hit_slider(e.x, e.y, sc.slide):
            self.drag = ["slide", e.x - b.X(SLIDER_XR + sc.slide * PXMM)]
            return
        # 4) 축전기 집기 (실험대 위 -> 그대로,  상자 -> 꺼내기)
        for i, (x, y) in list(sc.caps.items()):
            if abs(e.x - x) < 34 * BODY_S and abs(e.y - y) < 48 * BODY_S:
                self.drag = ["card", i, e.x, e.y]
                return
        for i in range(4):
            if i in sc.caps:
                continue
            x, y = self.tray_xy(i)
            bx, by = x, y + 24 * CARD_S
            if abs(e.x - bx) < 40 * CARD_S and abs(e.y - by) < 48 * CARD_S:
                sc.caps[i] = [e.x, e.y]
                self.drag = ["card", i, e.x, e.y]
                return

    def wheel(self, e, d=None):
        """다이얼 위에서 휠을 굴리면 한 칸씩 돌아간다 (실제 제품처럼)."""
        if d is None:
            d = 1 if getattr(e, "delta", 0) > 0 else -1
        mx, my = self.dmm_at
        kx, ky = mx + 128 * DMM_S, my + 242 * DMM_S
        if math.hypot(e.x - kx, e.y - ky) > 92 * DMM_S:
            return
        sc = self.app.sc
        i = DIAL_ORDER.index(sc.dial) if sc.dial in DIAL_ORDER else 0
        sc.dial = DIAL_ORDER[(i - d) % len(DIAL_ORDER)]
        self.redraw()

    def _attach(self, d, k, tgt):
        other = "b" if k == "r" else "r"
        if d[other] == tgt:
            d[other] = None
        d[k] = tgt

    def _probe_xy(self, k):
        sc = self.app.sc
        if sc.probe[k] in ("BATP", "BATN"):
            return self.batt_end("p" if sc.probe[k] == "BATP" else "n")
        if sc.probe[k]:
            p = self.board.term_xy(sc.probe[k])
            return (self.board.X(p[0]), self.board.Y(p[1]))
        jx = self.dmm_at[0] + (156 if k == "b" else 212) * DMM_S
        return (jx - 30 if k == "b" else jx + 26,
                self.dmm_at[1] + 400 * DMM_S)

    def motion(self, e):
        if not self.drag:
            return
        now = time.perf_counter()
        if now - getattr(self, "_last_mt", 0.0) < 0.022:
            return
        self._last_mt = now
        sc = self.app.sc
        kind = self.drag[0]
        if kind == "slide":
            sc.slide = min(TRAVEL_MM, max(0.0,
                round((e.x - self.drag[1] - self.board.ox) / self.board.sc
                      - SLIDER_XR, 1) / PXMM))
        elif kind == "card":
            self.drag[2], self.drag[3] = e.x, e.y
            sc.caps[self.drag[1]] = [e.x, e.y]
        else:                                   # probe / clip / batt
            self.drag[2], self.drag[3] = e.x, e.y
        self.redraw(full=False)

    def release(self, e):
        d, self.drag = self.drag, None
        if not d:
            return
        sc = self.app.sc
        kind = d[0]
        if kind == "card":
            i = d[1]
            sc.stack.pop(i, None)
            for j in list(sc.stack):
                if sc.stack[j] == i:
                    sc.stack.pop(j)
            if e.y > 624 and e.x < 1080:            # 상자에 도로 넣기
                sc.caps.pop(i, None)
            else:
                y = max(60, min(self.H - 80, e.y))
                sc.caps[i] = [e.x, y]
                # 다른 축전기 곁에 놓으면 다리를 함께 묶어 병렬이 된다
                best = None
                for j in sc.caps:
                    if j == i:
                        continue
                    r = self.root(j)
                    rx, ry = sc.caps[r]
                    if abs(e.x - rx) < 74 and abs(y - ry) < 96:
                        best = r
                        break
                if best is not None:
                    lvl = 1 + sum(1 for j in sc.stack if self.root(j) == best)
                    sc.stack[i] = best
                    sc.caps[i] = [sc.caps[best][0], sc.caps[best][1] - 46 * lvl]
        elif kind == "clip":
            k = d[1]
            tgt = self.snap("clip", e.x, e.y)
            if tgt:                                # 다리 위에 정확히 얹는다
                i = int(tgt[2:])
                sc.clip_pos[k] = list(self.lead_xy(i, tgt[1]))
            else:
                sc.clip_pos[k] = [e.x, e.y]
        elif kind in ("probe", "batt"):
            k = d[1]
            tgt = self.snap(kind, e.x, e.y)
            store = {"probe": sc.probe, "batt": sc.batt}[kind]
            free = {"probe": sc.free_probe, "batt": sc.free_batt}[kind]
            other = {"r": "b", "b": "r", "p": "n", "n": "p"}[k]
            if tgt:
                if store[other] == tgt:
                    store[other] = None
                    free[other] = None
                store[k] = tgt
                free[k] = None
            else:
                store[k] = None
                free[k] = (e.x, e.y)
        self.redraw()

    def _stop(self, *_):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def tick(self):
        if not self.winfo_exists():
            return
        sc = self.app.sc
        if sc.sw_on and sc.batt_in:
            sc.batt_v = max(7.5, sc.batt_v - BATT_DRAIN * 0.2 / 60.0)
        sc.jit = random.choice([0.0, 0.0, 0.0, 0.004, -0.004])
        state = (sc.display(), sc.osc(), sc.dial)
        if state != getattr(self, "_last_state", None):
            self._last_state = state
            self.redraw()
        self._job = self.after(220, self.tick)


# =========================================================================
#  5.  앱
# =========================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(S["title"])
        self.geometry("1620x830")
        try:
            ttk.Style().theme_use("clam")
        except Exception:
            pass
        self.sc = Scene()
        self.lab = WorkTab(self, self)
        self.lab.pack(fill="both", expand=True)
        self.asm = self.bench = self.lab

    def unlock_bench(self):
        pass


if __name__ == "__main__":
    App().mainloop()
