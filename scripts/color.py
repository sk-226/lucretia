"""色変換・評価指標ライブラリ (plan.md §5, Phase 0)

依存なし (標準ライブラリのみ)。実装:
- sRGB <-> Oklab / OKLCH (Björn Ottosson の公式係数)
- ΔEok (Oklab ユークリッド距離)
- WCAG 2.x コントラスト比
- APCA-W3 0.0.98G-4g 相当の Lc 値
- sRGB ガモット判定と chroma クランプ

`python3 color.py` で自己テスト実行。
"""
import math

# ---------- sRGB ----------

def srgb_to_linear(c8):
    c = c8 / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb01(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    return f"#{r:02X}{g:02X}{b:02X}"


# ---------- Oklab / OKLCH ----------

def rgb_to_oklab(r, g, b):
    r, g, b = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def oklab_to_linear_rgb(L, a, b):
    """クランプなしの線形RGB (ガモット判定に使う)"""
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def hex_to_oklch(h):
    L, a, b = rgb_to_oklab(*hex_to_rgb(h))
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def oklch_in_gamut(L, C, H, eps=1e-4):
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    return all(-eps <= v <= 1 + eps for v in oklab_to_linear_rgb(L, a, b))


def oklch_to_hex(L, C, H):
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    rgb = oklab_to_linear_rgb(L, a, b)
    return rgb_to_hex(*(round(max(0., min(1., linear_to_srgb01(max(0., min(1., v))))) * 255) for v in rgb))


def clamp_chroma(L, C, H):
    """C を sRGB ガモット内に収まる最大値 (<= C) まで二分探索で下げる"""
    if oklch_in_gamut(L, C, H):
        return C
    lo, hi = 0.0, C
    for _ in range(40):
        mid = (lo + hi) / 2
        if oklch_in_gamut(L, mid, H):
            lo = mid
        else:
            hi = mid
    return lo


def deltaE_ok(h1, h2):
    L1, a1, b1 = rgb_to_oklab(*hex_to_rgb(h1))
    L2, a2, b2 = rgb_to_oklab(*hex_to_rgb(h2))
    return math.sqrt((L1 - L2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2)


# ---------- WCAG 2.x ----------

def rel_lum(h):
    r, g, b = (srgb_to_linear(c) for c in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag(fg, bg):
    l1, l2 = rel_lum(fg), rel_lum(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


# ---------- APCA-W3 (0.0.98G-4g) ----------
_SA = dict(mainTRC=2.4, sRco=0.2126729, sGco=0.7151522, sBco=0.0721750,
           normBG=0.56, normTXT=0.57, revTXT=0.62, revBG=0.65,
           blkThrs=0.022, blkClmp=1.414, scale=1.14,
           loBoWoffset=0.027, loWoBoffset=0.027, loClip=0.1, deltaYmin=0.0005)


def _apca_y(h):
    r, g, b = hex_to_rgb(h)
    return (_SA['sRco'] * (r / 255) ** _SA['mainTRC']
            + _SA['sGco'] * (g / 255) ** _SA['mainTRC']
            + _SA['sBco'] * (b / 255) ** _SA['mainTRC'])


def _soft_clamp(y):
    return y if y >= _SA['blkThrs'] else y + (_SA['blkThrs'] - y) ** _SA['blkClmp']


def apca_lc(txt, bg):
    """APCA Lc 値。txt が bg より暗ければ正 (BoW)、明るければ負 (WoB)。"""
    ytx, ybg = _soft_clamp(_apca_y(txt)), _soft_clamp(_apca_y(bg))
    if abs(ybg - ytx) < _SA['deltaYmin']:
        return 0.0
    if ybg > ytx:  # dark text on light bg
        sapc = (ybg ** _SA['normBG'] - ytx ** _SA['normTXT']) * _SA['scale']
        out = 0.0 if sapc < _SA['loClip'] else sapc - _SA['loBoWoffset']
    else:          # light text on dark bg
        sapc = (ybg ** _SA['revBG'] - ytx ** _SA['revTXT']) * _SA['scale']
        out = 0.0 if sapc > -_SA['loClip'] else sapc + _SA['loWoBoffset']
    return out * 100


# ---------- CVD シミュレーション (Machado et al. 2009, severity 1.0) ----------
# 線形 RGB に適用する 3x3 行列。colorspacious / DaltonLens が採用する標準値
_CVD_MATRICES = {
    'protan': ((0.152286, 1.052583, -0.204868),
               (0.114503, 0.786281, 0.099216),
               (-0.003882, -0.048116, 1.051998)),
    'deutan': ((0.367322, 0.860646, -0.227968),
               (0.280085, 0.672501, 0.047413),
               (-0.011820, 0.042940, 0.968881)),
    'tritan': ((1.255528, -0.076749, -0.178779),
               (-0.078411, 0.930809, 0.147602),
               (0.004733, 0.691367, 0.303900)),
}


def cvd_hex(h, kind):
    """hex 色を P型/D型/T型 (2色覚, severity 1.0) の見えにシミュレートした hex を返す"""
    m = _CVD_MATRICES[kind]
    lin = [srgb_to_linear(c) for c in hex_to_rgb(h)]
    out = []
    for row in m:
        v = sum(a * b for a, b in zip(row, lin))
        out.append(round(max(0., min(1., linear_to_srgb01(max(0., min(1., v))))) * 255))
    return rgb_to_hex(*out)


# ---------- 自己テスト ----------
if __name__ == '__main__':
    ok = True

    # OKLCH 往復
    for h in ('#FFFCF0', '#205EA6', '#100F0F', '#AD8301'):
        h2 = oklch_to_hex(*hex_to_oklch(h))
        d = deltaE_ok(h, h2)
        if d > 1e-3:
            print(f'[FAIL] roundtrip {h} -> {h2} (dE={d:.5f})'); ok = False

    # WCAG 既知値: #767676 on #FFFFFF ≈ 4.54:1
    w = wcag('#767676', '#FFFFFF')
    if abs(w - 4.54) > 0.01:
        print(f'[FAIL] WCAG #767676/#fff = {w:.3f} (expected 4.54)'); ok = False

    # APCA 公式リファレンス値 (apca-w3 README, 0.0.98G-4g)
    refs = [('#888888', '#FFFFFF', 63.056469930209424),
            ('#FFFFFF', '#888888', -68.54146436644962),
            ('#000000', '#AAAAAA', 58.146262578561334),
            ('#AAAAAA', '#000000', -56.24113336839742)]
    for txt, bg, exp in refs:
        got = apca_lc(txt, bg)
        if abs(got - exp) > 0.1:
            print(f'[FAIL] APCA {txt} on {bg}: got {got:.4f}, expected {exp:.4f}'); ok = False
        else:
            print(f'[ok] APCA {txt} on {bg}: {got:.4f} (ref {exp:.4f})')

    # ガモットクランプ: 派手な色は必ず in-gamut に落ちる
    c = clamp_chroma(0.53, 0.4, 145)
    assert oklch_in_gamut(0.53, c, 145)

    # CVD: 無彩色はほぼ不変 (行の和 ≈ 1)、P/D 型では赤と緑の距離が大きく縮む
    for kind in ('protan', 'deutan', 'tritan'):
        d = deltaE_ok('#808080', cvd_hex('#808080', kind))
        if d > 0.02:
            print(f'[FAIL] CVD {kind}: gray shifted dE={d:.4f}'); ok = False
    d_orig = deltaE_ok('#AF3028', '#66800B')  # Flexoki red-600 vs green-600
    for kind in ('protan', 'deutan'):
        d_sim = deltaE_ok(cvd_hex('#AF3028', kind), cvd_hex('#66800B', kind))
        # protan は L 差が残るため縮小は緩やか、deutan は大きく潰れる
        if d_sim > 0.75 * d_orig:
            print(f'[FAIL] CVD {kind}: red/green distance not reduced '
                  f'({d_sim:.3f} vs {d_orig:.3f})'); ok = False
        else:
            print(f'[ok] CVD {kind}: red-600/green-600 dE {d_orig:.3f} -> {d_sim:.3f}')

    print('ALL TESTS PASSED' if ok else 'TESTS FAILED')
