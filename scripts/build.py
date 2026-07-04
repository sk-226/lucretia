"""パレット生成 + 検証用 HTML 出力

出力:
- palette.json      : 全色 (OKLCH パラメータ + hex) + ロールマッピング。単一ソース
- out/swatches.html : 確定 bg プレビュー / スケール一覧 / コード階層デモ
- out/contrast.html : コントラスト行列 (WCAG + APCA) + 淡色帯 50–200 の両用途検証
- out/cvd.html      : P/D/T 型シミュレーション + ペア ΔEok 行列
- out/roles.html    : ロール表 + 用途モック (スライド / Markdown / ギャラリー)
- out/degrade.html  : 投影劣化シミュレーション (彩度低下 / ガンマ / 黒浮き)
- out/tokens.css    : CSS variables (palette.json から生成)

パラメータは全てこのファイル冒頭の定数。ここを触って再実行すれば全成果物が更新される。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from color import (oklch_to_hex, hex_to_oklch, clamp_chroma, deltaE_ok,
                   wcag, apca_lc, cvd_hex, hex_to_rgb, rgb_to_hex)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'out')

# ============================================================
# 設計パラメータ (plan.md §4.3)。Flexoki 実測から導いた初期値
# ============================================================
STEPS = [50, 100, 150, 200, 300, 400, 500, 600, 700, 800, 850, 900, 950]

# 共通 L カーブ (step -> L)
L_BASE = {50: .96, 100: .92, 150: .88, 200: .84, 300: .76, 400: .66,
          500: .59, 600: .53, 700: .46, 800: .39, 850: .35, 900: .30, 950: .24}

# C カーブ係数 (Cmax に掛ける)。中央で最大、端でも 0 にしない (インク感)
C_FACTOR = {50: .25, 100: .35, 150: .45, 200: .55, 300: .75, 400: .95,
            500: 1.0, 600: 1.0, 700: .92, 800: .80, 850: .72, 900: .62, 950: .50}

# 色ごとの L 補正の効き方 (中央で 1、端で弱める)
L_DELTA_W = {50: .15, 100: .30, 150: .45, 200: .60, 300: .85, 400: 1.0,
             500: 1.0, 600: 1.0, 700: .85, 800: .65, 850: .55, 900: .45, 950: .30}

# hue / 最大彩度 / L 補正 (600 での Flexoki 実測 - 共通カーブ 0.53 の差分が初期値)
ACCENTS = {
    #        H,    Cmax,  Ldelta
    'red':     (28,  .165, -.026),
    'orange':  (47,  .152, +.037),
    'yellow':  (87,  .135, +.103),
    'green':   (122, .134, +.029),
    'cyan':    (187, .100, +.024),
    'blue':    (252, .132, -.048),
    'purple':  (294, .145, -.076),
    'magenta': (350, .161, -.035),
}

# base スケール (plan.md §4.2) — Phase 1 で neutral に確定 (2026-07: warm 案は廃止)
BASE = dict(H=97, C_light=.002, C_dark=.002)

# 背景 (plan.md §4.1) — Phase 1 で案 A に確定 (B/C 案は廃止)
BG = (0.990, 0.006, 95)
BG2_OFFSET = (-0.025, +0.002)  # bg-2 = (L+dL, C+dC)

WHITE = '#FFFFFF'
BLACK_L, BLACK_C = 0.17, 0.002

# ------------------------------------------------------------
# lucretia paper (plan.md §6.5): 長文読書用の温かみプロファイル。
# 紙の快適さ = 低輝度・暖色スペクトルの近似として bg の L を下げ C を上げる。
# プレゼン・ギャラリー用途は対象外 (写真中立性の制約がないので暖色 base を使う)
# ------------------------------------------------------------
# 背景 — P2 (生成り) に確定 (2026-07, plan.md §9-16。P1/P3 案は廃止)
PAPER_BG = (0.970, 0.014, 92)
# 暖色 base (paper 専用)。neutral base は暖色 bg 上で青白く浮くため
PAPER_BASE = dict(H=92, C_light=.014, C_dark=.006)


# ============================================================
# 生成
# ============================================================

def gen_accent(name):
    H, cmax, ld = ACCENTS[name]
    out = {}
    for s in STEPS:
        L = min(0.97, max(0.08, L_BASE[s] + ld * L_DELTA_W[s]))
        C = clamp_chroma(L, cmax * C_FACTOR[s], H)
        out[s] = dict(hex=oklch_to_hex(L, C, H), oklch=[round(L, 4), round(C, 4), H])
    return out


# ハイライター (Obsidian 等のマーカー線用)。tint 150 (L .88, C 0.45*Cmax) より
# 高彩度・高明度にして「蛍光マーカー」の見えにする。黒文字 (tx / tx 太字) 専用。
# L=0.93: 黒文字で全色 |Lc| >= 90 (本文級) を満たす下限 (0.92 以下だと red/magenta が未達)
HL_L, HL_CFACTOR = 0.93, 0.85


def gen_highlight():
    out = {}
    for n, (H, cmax, _) in ACCENTS.items():
        C = clamp_chroma(HL_L, cmax * HL_CFACTOR, H)
        out[n] = dict(hex=oklch_to_hex(HL_L, C, H), oklch=[HL_L, round(C, 4), H])
    return out


def gen_base(cfg=BASE):
    out = {}
    for s in STEPS:
        L = L_BASE[s]
        t = (L - L_BASE[950]) / (L_BASE[50] - L_BASE[950])  # 1=明, 0=暗
        C = cfg['C_dark'] + (cfg['C_light'] - cfg['C_dark']) * t
        C = clamp_chroma(L, C, cfg['H'])
        out[s] = dict(hex=oklch_to_hex(L, C, cfg['H']),
                      oklch=[round(L, 4), round(C, 4), cfg['H']])
    return out


# ============================================================
# ロールマッピング (plan.md §6, Phase 3)。値は「参照名」で書き、hex は解決して出力
#   参照名: 'white' 'black' 'bg' 'bg2' / 'base-600' / 'blue-600' など
# ============================================================
ROLES = {
    # 共通 UI (ライト)
    'light': dict(
        bg='bg', bg_2='bg2', card='white',
        ui='base-100', ui_2='base-150', ui_3='base-200',
        link='blue-600', link_hover='blue-800', visited='purple-600',
        focus_ring='blue-400',
        # white は「際立たせる」用途 (カード等) 専用で、地としては使わない (plan.md §9-14)
        photo_surface='bg',
    ),
    # テキスト 2 プロファイル (plan.md §4.2)
    'light_high': dict(tx='black', tx_2='base-700', tx_3='base-500'),
    'light_quiet': dict(tx='base-800', tx_2='base-600', tx_3='base-400'),
    # ダーク (コーディング / ギャラリー暗背景。plan.md §6.3, §6.4)
    # bg は black: base-950 だと tx=base-100 が Lc -88.5 で本文目標 90 に届かない (APCA 実測)
    'dark': dict(
        bg='black', bg_2='base-950',
        ui='base-900', ui_2='base-850', ui_3='base-800',
        tx='base-100', tx_2='base-300', tx_3='base-500',
        link='blue-300', link_hover='blue-200', visited='purple-300',
        focus_ring='blue-300',
        photo_surface='base-950',       # 確定 (plan.md §9-15)。黒より一段浮かせた C≈0 面
    ),
    # シンタックス (plan.md §6.3 sparse highlighting)
    # keyword=magenta: definition=blue と purple は CVD D型で ΔEok 0.027 と近すぎる
    # (out/cvd.html)。plan §6.3 の「キーワード=magenta or purple / 数値=purple」の範囲内
    'syntax_light': dict(
        variable='black', definition='blue-600', keyword='magenta-600',
        string='green-600', number='purple-600',
        operator='base-500', comment='base-400',
    ),
    # ダークは 300 帯中心: 400 帯は black 上で Lc -31〜-49 と暗すぎる (APCA 実測)。
    # string のみ 400 (green-300 は Lc -65 で Tier2 より目立ってしまうため)
    'syntax_dark': dict(
        variable='base-100', definition='blue-300', keyword='magenta-300',
        string='green-400', number='purple-300',
        operator='base-300', comment='base-500',
    ),
    # プレゼン (plan.md §6.1)。テキストは light_high を継承
    'presentation': dict(
        emphasis_1='blue-600', emphasis_2='red-600',
        sub_1='green-600', sub_2='orange-600',
        sub_3='yellow-600',             # 規約: 太字・大サイズ限定 (plan.md §4.3)
        note_fill='red-100', note_text='red-800',
        info_fill='blue-100', info_text='blue-800',
        # chart 1-7: MATLAB の 7 色構成に倣い、L 段差 (300-600 帯混在) で CVD 耐性を確保。
        # 貪欲法で「先頭から k 色使ったときの P/D/T 込み最悪ペア ΔEok」を最大化した順。
        # 全ペア最悪 0.042 (旧 400 帯 5 色構成は 0.018 だった)。それでも色だけに頼らず
        # マーカー形状・線種を併用する (plan.md §1, §9-9)
        chart_1='blue-400', chart_2='orange-600', chart_3='purple-600',
        chart_4='red-300', chart_5='yellow-500', chart_6='cyan-600',
        chart_7='green-500',
    ),
    # Markdown エディタ (plan.md §6.2)
    'markdown': dict(
        heading='black', body='black', link='blue-600',
        code_inline_bg='base-50', code_block_bg='bg2',
        quote_text='base-700', quote_border='base-150', hr='base-150',
    ),
    # ギャラリー Extended (plan.md §6.4)。scrim は build 時に alpha 階段を展開
    'gallery': dict(caption='base-600', meta='base-400'),
    # ハイライター (マーカー線)。規約: base の文字 (tx / tx 太字) の下にのみ引く。
    # 有彩色文字・リンクの上には使わない (色×色で意味が濁るため)
    'highlight': {n: f'hl-{n}' for n in ACCENTS},
    # lucretia paper (plan.md §6.5): 長文読書プロファイル。
    # tx = pbase-900 (P2 上 12.5:1 / Lc+94): 高コントラスト基準は満たしつつ
    # black (17.6:1) のハレーションを避ける「書籍インク」帯。white は使わない
    'paper': dict(
        bg='paper-bg', bg_2='paper-bg2',
        ui='pbase-100', ui_2='pbase-150', ui_3='pbase-200',
        tx='pbase-900', tx_2='pbase-700', tx_3='pbase-500',
        link='blue-600', link_hover='blue-800', visited='purple-600',
        focus_ring='blue-400',
    ),
    # シンタックスは syntax_light と同じ hue/step 割当 (P2 上でも同水準の
    # コントラストを確認済み)。無彩色トークンのみ暖色 pbase / インクに置換
    'syntax_paper': dict(
        variable='pbase-900', definition='blue-600', keyword='magenta-600',
        string='green-600', number='purple-600',
        operator='pbase-500', comment='pbase-400',
    ),
    # Markdown (読書ビュー)。見出しだけ本文より一段沈めて無彩色で階層を出す
    'markdown_paper': dict(
        heading='pbase-950', body='pbase-900', link='blue-600',
        code_inline_bg='pbase-100', code_block_bg='paper-bg2',
        quote_text='pbase-700', quote_border='pbase-200', hr='pbase-150',
    ),
}
SCRIM_ALPHAS = (5, 10, 20, 40, 60, 80)  # % (plan.md §6.4 overlay-scrim)


def resolve_ref(pal, ref):
    if ref in ('white', 'black'):
        return pal['special'][ref]
    if ref in ('bg', 'bg2'):
        return pal['bg'][ref]
    if ref in ('paper-bg', 'paper-bg2'):
        return pal['paper'][ref.replace('paper-', '')]
    if ref.startswith('hl-'):
        return pal['highlight'][ref[3:]]['hex']
    name, step = ref.rsplit('-', 1)
    if name == 'base':
        scale = pal['base']
    elif name == 'pbase':
        scale = pal['paper']['base']
    else:
        scale = pal['accents'][name]
    return scale[int(step)]['hex']


def build_roles(pal):
    out = {}
    for group, roles in ROLES.items():
        out[group] = {k.replace('_', '-'): dict(ref=v, hex=resolve_ref(pal, v))
                      for k, v in roles.items()}
    out['gallery']['scrim'] = dict(
        black={a: f'rgba(16,15,14,{a / 100})' for a in SCRIM_ALPHAS},
        white={a: f'rgba(255,255,255,{a / 100})' for a in SCRIM_ALPHAS})
    return out


def build_palette():
    pal = dict(meta=dict(source='build.py',
                         note='Phase 1 決定済み (bg=案A, base=neutral)。'
                              'Phase 3 ロールはドラフト (photo-surface 等は仮決め)'))
    pal['special'] = dict(white=WHITE,
                          black=oklch_to_hex(BLACK_L, BLACK_C, 97))
    L, C, H = BG
    bg = oklch_to_hex(L, C, H)
    bg2 = oklch_to_hex(L + BG2_OFFSET[0], C + BG2_OFFSET[1], H)
    pal['bg'] = dict(bg=bg, bg2=bg2, oklch=[L, C, H],
                     dE_white=round(deltaE_ok(bg, WHITE), 4),
                     dE_paper=round(deltaE_ok(bg, '#FFFCF0'), 4))
    # lucretia paper (plan.md §6.5)
    pL, pC, pH = PAPER_BG
    pbg = oklch_to_hex(pL, pC, pH)
    pal['paper'] = dict(
        bg=pbg, bg2=oklch_to_hex(pL + BG2_OFFSET[0], pC + BG2_OFFSET[1], pH),
        oklch=[pL, pC, pH],
        dE_bg=round(deltaE_ok(pbg, bg), 4),
        dE_white=round(deltaE_ok(pbg, WHITE), 4),
        base=gen_base(PAPER_BASE))
    pal['base'] = gen_base()
    pal['accents'] = {n: gen_accent(n) for n in ACCENTS}
    pal['highlight'] = gen_highlight()
    pal['roles'] = build_roles(pal)
    return pal


# ============================================================
# HTML 共通
# ============================================================
CSS = """
body{font-family:-apple-system,'Helvetica Neue',sans-serif;margin:0;padding:24px;
     background:#F2F2F2;color:#222;font-size:14px}
h1{font-size:20px}h2{font-size:16px;margin-top:32px}h3{font-size:14px}
.small{color:#666;font-size:12px}
table{border-collapse:collapse;background:#fff}
td,th{border:1px solid #DDD;padding:4px 8px;font-size:12px;text-align:center}
.chip{display:inline-block;width:64px;padding:14px 0 4px;margin:1px;border-radius:4px;
      text-align:center;font-size:10px;vertical-align:top}
.card{display:inline-block;vertical-align:top;margin:8px;padding:20px;border-radius:8px;
      width:300px;border:1px solid #DDD}
.wbox{background:#FFFFFF;border-radius:6px;padding:10px;margin:10px 0;
      box-shadow:0 1px 3px rgba(0,0,0,.06)}
pre{border-radius:8px;padding:14px;font-size:12.5px;line-height:1.6;
    font-family:ui-monospace,'SF Mono',Menlo,monospace}
.p2{background:#E8F5E9}.p1{background:#FFFDE7}.p0{background:#FFF3E0}.pf{background:#FFEBEE}
"""


def text_color_for(hexbg):
    return '#111' if hex_to_oklch(hexbg)[0] > 0.62 else '#FFF'


def chip(hexv, label):
    return (f'<div class="chip" style="background:{hexv};color:{text_color_for(hexv)}">'
            f'{label}<br>{hexv}</div>')


# ============================================================
# swatches.html
# ============================================================

def html_swatches(pal):
    h = [f'<!doctype html><meta charset="utf-8"><title>swatches</title><style>{CSS}</style>']
    h.append('<h1>カラーテーマ スウォッチ（初期生成）</h1>'
             '<p class="small">plan.md §4 の初期パラメータによる自動生成。'
             'Phase 1–2 でこのページを見ながら build.py の定数を調整する。</p>')

    # --- bg (Phase 1 で案 A に確定) ---
    h.append('<h2>1. 背景（Phase 1 確定: 旧案 A）— white カード・本文・アクセント・淡色塗り</h2>')
    blk = pal['special']['black']
    b6, r6 = pal['accents']['blue'][600]['hex'], pal['accents']['red'][600]['hex']
    g6 = pal['accents']['green'][600]['hex']
    tx2 = pal['base'][600]['hex']

    # 淡色塗りボックス (plan.md §6.1: 塗り 50/100 + 同系統 800 の文字)
    TINT_HUES = ('blue', 'red', 'yellow', 'orange', 'green')

    def tint_rows():
        rows = []
        for n in TINT_HUES:
            c50 = pal['accents'][n][50]['hex']
            c100 = pal['accents'][n][100]['hex']
            c800 = pal['accents'][n][800]['hex']
            rows.append(
                f'<div style="display:flex;gap:4px;margin:3px 0;font-size:11px">'
                f'<div style="flex:1;background:{c50};color:{c800};border-radius:4px;'
                f'padding:3px 6px">{n}-50 {c50}</div>'
                f'<div style="flex:1;background:{c100};color:{c800};border-radius:4px;'
                f'padding:3px 6px">{n}-100 {c100}</div></div>')
        return ''.join(rows)

    for k, d in (('bg', pal['bg']),):
        h.append(
            f'<div class="card" style="background:{d["bg"]}">'
            f'<b style="color:{blk}">{k}</b> <span class="small">{d["bg"]} '
            f'(ΔE white {d["dE_white"]}, paper {d["dE_paper"]})</span>'
            f'<div class="wbox"><span style="color:{blk}">white カード上の本文。</span> '
            f'<span style="color:{b6}">強調</span> / <span style="color:{r6}">警告</span></div>'
            f'<p style="color:{blk};margin:6px 0">bg 直上の本文テキスト。'
            f'<span style="color:{tx2}">サブテキスト（灰）。</span> '
            f'<b style="color:{g6}">サブカラー緑。</b></p>'
            f'<div style="background:{d["bg2"]};border-radius:6px;padding:8px;color:{blk}">'
            f'bg-2 のパネル {d["bg2"]}</div>'
            f'<div style="margin-top:8px">{tint_rows()}</div>'
            f'</div>')
    # 参考: Flexoki paper
    h.append(f'<div class="card" style="background:#FFFCF0">'
             f'<b style="color:{blk}">参考: Flexoki paper</b> <span class="small">#FFFCF0</span>'
             f'<div class="wbox"><span style="color:{blk}">white カード上の本文。</span></div>'
             f'<p style="color:{blk}">bg 直上の本文テキスト。</p>'
             f'<div style="margin-top:8px">{tint_rows()}</div></div>')

    # --- base スケール (Phase 1 で neutral に確定) ---
    h.append('<h2>2. base スケール（Phase 1 確定: neutral）</h2><div>')
    h.append(chip(pal['special']['white'], 'white'))
    for s in STEPS:
        h.append(chip(pal['base'][s]['hex'], f'base-{s}'))
    h.append(chip(pal['special']['black'], 'black'))
    h.append('</div>')

    # --- アクセント一覧 ---
    h.append('<h2>3. アクセント 8 色 × 13 段階</h2>')
    for name in ACCENTS:
        h.append(f'<h3>{name}</h3><div>')
        for s in STEPS:
            h.append(chip(pal['accents'][name][s]['hex'], f'{s}'))
        h.append('</div>')

    # --- ハイライター ---
    h.append('<h2>3b. ハイライター (hl-*, 黒文字専用マーカー)</h2><div>')
    for name in ACCENTS:
        h.append(chip(pal['highlight'][name]['hex'], f'hl-{name}'))
    h.append('</div>')

    # --- コード階層デモ (plan.md §6.3) ---
    h.append('<h2>4. コード階層デモ（§6.3 sparse highlighting）</h2>'
             '<p class="small">Tier1 変数=tx（無彩色） / Tier2 定義=blue・キーワード=magenta / '
             'Tier3 文字列=green・数値=purple / Tier4 コメント=tx-3</p>')

    def code_sample(bg, tx, tx2, tx3, kw, fn, st, num):
        return (f'<pre style="background:{bg};color:{tx}">'
                f'<span style="color:{tx3}"># 残差ノルムの履歴を計算する</span>\n'
                f'<span style="color:{kw}">def</span> <span style="color:{fn}">residual_history</span>(A, b, xs):\n'
                f'    norms = []\n'
                f'    <span style="color:{kw}">for</span> x <span style="color:{kw}">in</span> xs:\n'
                f'        r = b <span style="color:{tx2}">-</span> A <span style="color:{tx2}">@</span> x\n'
                f'        norms.append(np.linalg.norm(r) <span style="color:{tx2}">/</span> '
                f'np.linalg.norm(b))\n'
                f'    <span style="color:{kw}">return</span> norms  '
                f'<span style="color:{tx3}"># 相対残差 &lt; </span>'
                f'<span style="color:{num}">1e-12</span> <span style="color:{tx3}">で収束</span>\n'
                f'    <span style="color:{st}">"restarted BiCGSTAB"</span></pre>')

    # ロール定義 (ROLES syntax_*) から描画し、roles.html / palette.json と常に同期させる
    sd = {k: v['hex'] for k, v in pal['roles']['syntax_dark'].items()}
    sl = {k: v['hex'] for k, v in pal['roles']['syntax_light'].items()}
    dk = {k: v['hex'] for k, v in pal['roles']['dark'].items()}
    h.append('<h3>ダーク（syntax_dark ロール / bg = black）</h3>')
    h.append(code_sample(dk['bg'], sd['variable'], sd['operator'], sd['comment'],
                         sd['keyword'], sd['definition'], sd['string'], sd['number']))
    h.append('<h3>ライト（syntax_light ロール / bg = bg）</h3>')
    h.append(code_sample(pal['bg']['bg'], sl['variable'], sl['operator'], sl['comment'],
                         sl['keyword'], sl['definition'], sl['string'], sl['number']))
    return ''.join(h)


# ============================================================
# contrast.html
# ============================================================

def rate(w, lc):
    """plan.md §3.4 / §5.1 の目標での判定"""
    a = abs(lc)
    if w >= 7 and a >= 90:
        return 'p2', '◎ 高'
    if w >= 4.5 and a >= 75:
        return 'p1', '○ 低(quiet)可'
    if w >= 3 and a >= 60:
        return 'p0', '△ 大/太のみ'
    return 'pf', '✕'


def matrix(title, fgs, bgs, note=''):
    h = [f'<h2>{title}</h2>']
    if note:
        h.append(f'<p class="small">{note}</p>')
    h.append('<table><tr><th>fg \\ bg</th>')
    for bn, bh in bgs:
        h.append(f'<th>{bn}<br>{bh}</th>')
    h.append('</tr>')
    for fn, fh in fgs:
        h.append(f'<tr><th style="background:{fh};color:{text_color_for(fh)}">{fn}<br>{fh}</th>')
        for bn, bh in bgs:
            w, lc = wcag(fh, bh), apca_lc(fh, bh)
            cls, lab = rate(w, lc)
            h.append(f'<td class="{cls}">{w:.2f}:1<br>Lc {lc:+.0f}<br>{lab}</td>')
        h.append('</tr>')
    h.append('</table>')
    return ''.join(h)


def html_contrast(pal):
    ac, bs = pal['accents'], pal['base']
    blk, wht = pal['special']['black'], pal['special']['white']
    h = [f'<!doctype html><meta charset="utf-8"><title>contrast</title><style>{CSS}</style>',
         '<h1>コントラスト行列（WCAG 2.x + APCA Lc）</h1>',
         '<p class="small">判定は plan.md の目標: ◎=高コントラスト本文可 (≥7:1 & |Lc|≥90) / '
         '○=quiet 本文可 (≥4.5 & ≥75) / △=大・太字のみ (≥3 & ≥60) / ✕=装飾のみ</p>']

    light_bgs = [('bg', pal['bg']['bg']), ('bg-2', pal['bg']['bg2']), ('white', wht)]
    light_fgs = ([('black', blk)]
                 + [(f'base-{s}', bs[s]['hex']) for s in (800, 700, 600)]
                 + [('tx-navy (blue-900)', ac['blue'][900]['hex'])]
                 + [(f'{n}-600', ac[n][600]['hex']) for n in ACCENTS])
    h.append(matrix('ライトテーマ', light_fgs, light_bgs))

    dark_bgs = [('base-950', bs[950]['hex']), ('black', blk)]
    dark_fgs = ([('white', wht)]
                + [(f'base-{s}', bs[s]['hex']) for s in (100, 200, 300)]
                + [(f'{n}-400', ac[n][400]['hex']) for n in ACCENTS]
                + [(f'{n}-300', ac[n][300]['hex']) for n in ('blue', 'green')])
    h.append(matrix('ダークテーマ', dark_fgs, dark_bgs,
                    'APCA は負値 (明るい文字 on 暗背景)。WCAG 2.x はダークで過大評価に注意 (plan.md §5.1)'))

    tint_bgs = [(f'{n}-100', ac[n][100]['hex']) for n in ('red', 'blue', 'green', 'yellow')]
    tint_fgs = ([('black', blk)]
                + [(f'{n}-800', ac[n][800]['hex']) for n in ('red', 'blue', 'green', 'yellow')])
    h.append(matrix('淡色塗り (100) 上の文字', tint_fgs, tint_bgs,
                    '同系統 800 を淡色 100 の上に置く運用 (plan.md §6.1) の妥当性チェック'))

    # --- 淡色帯 (50-200) 塗り判別: ΔEok vs bg (plan.md §4.4) ---
    h.append('<h2>淡色帯 (50–200) の「塗り」判別性: ΔEok vs 背景</h2>'
             '<p class="small">bg の上に枠線なしで置いたとき塗りと分かるか。'
             '目安 ΔEok ≥ 0.02 (plan.md §4.4)。投影では消えうる前提で枠線 or L 差併用 (§5.4)</p>')
    h.append('<table><tr><th>色 \\ 塗り</th>')
    for s in (50, 100, 150, 200):
        h.append(f'<th>{s}</th>')
    h.append('</tr>')
    bgh = pal['bg']['bg']
    for n in ACCENTS:
        h.append(f'<tr><th>{n} (vs bg)</th>')
        for s in (50, 100, 150, 200):
            hx = ac[n][s]['hex']
            d = deltaE_ok(hx, bgh)
            cls = 'p2' if d >= 0.02 else 'pf'
            mark = '○' if d >= 0.02 else '✕'
            h.append(f'<td class="{cls}" style="background:{hx}">'
                     f'{hx}<br>ΔE {d:.3f} {mark}</td>')
        h.append('</tr>')
    h.append('</table>')

    # --- ハイライター上の黒文字 (規約: base 文字専用) ---
    hl_bgs = [(f'hl-{n}', pal['highlight'][n]['hex']) for n in ACCENTS]
    h.append(matrix('ハイライター (hl-*) 上の黒文字', [('black', blk)], hl_bgs,
                    'マーカー線は tx (black) とその太字の下にのみ引く規約。'
                    '本文級 ◎ (≥7:1 & |Lc|≥90) が必須'))

    # --- 淡色帯の「文字」用途: 同系統の濃色背景上で APCA 検証 (plan.md §4.4) ---
    h.append('<h2>淡色帯 (50–200) の「文字」用途: 同系統濃色 (700–950) 上の APCA</h2>'
             '<p class="small">quiet 本文級 |Lc| ≥ 75 で○。'
             '「red-100 は red-800 以深の上でのみ文字可」の形の用途表 (plan.md §4.4)</p>')
    for n in ACCENTS:
        fgs = [(f'{n}-{s}', ac[n][s]['hex']) for s in (50, 100, 150, 200)]
        bgs = [(f'{n}-{s}', ac[n][s]['hex']) for s in (700, 800, 850, 900, 950)]
        h.append(matrix(f'{n}', fgs, bgs))
    return ''.join(h)


# ============================================================
# cvd.html (plan.md §5.1 CVD シミュレーション)
# ============================================================
CVD_KINDS = [('原色 (シミュレーションなし)', None), ('P型 (protanopia)', 'protan'),
             ('D型 (deuteranopia)', 'deutan'), ('T型 (tritanopia)', 'tritan')]

# カテゴリカルな取り違えリスクの目安 (ΔEok)。経験的な閾値であり最終判断は目視
CVD_DE_BAD, CVD_DE_WARN = 0.04, 0.08


def html_cvd(pal):
    ac = pal['accents']
    h = [f'<!doctype html><meta charset="utf-8"><title>cvd</title><style>{CSS}</style>',
         '<h1>CVD シミュレーション (Machado 2009, severity 1.0)</h1>',
         '<p class="small">plan.md §5.1: 強調 (red/blue)・サブ (green/orange/yellow) が'
         '色相のみに依存しない設計かの確認。ΔEok ペア距離: '
         f'✕ &lt; {CVD_DE_BAD} (取り違えリスク大) / △ &lt; {CVD_DE_WARN} / ○ それ以上。'
         'あくまで目安で、最終判断はスウォッチ目視 + 実運用 (色だけに意味を載せない原則 §1)</p>']

    for step, usage in ((600, 'ライトの強調・シンタックス帯'),
                        (400, '図形・グラフ帯 / ダークのシンタックス帯 (plan.md §6.1, §6.3)')):
        h.append(f'<h2>step {step} — {usage}</h2>')
        for label, kind in CVD_KINDS:
            h.append(f'<h3>{label}</h3><div>')
            for n in ACCENTS:
                hx = ac[n][step]['hex']
                sim = cvd_hex(hx, kind) if kind else hx
                h.append(chip(sim, n))
            h.append('</div>')
            # ペア距離行列
            sims = {n: (cvd_hex(ac[n][step]['hex'], kind) if kind else ac[n][step]['hex'])
                    for n in ACCENTS}
            names = list(ACCENTS)
            h.append('<table><tr><th>ΔEok</th>')
            for n in names:
                h.append(f'<th>{n}</th>')
            h.append('</tr>')
            worst = []
            for i, n1 in enumerate(names):
                h.append(f'<tr><th>{n1}</th>')
                for j, n2 in enumerate(names):
                    if j <= i:
                        h.append('<td></td>')
                        continue
                    d = deltaE_ok(sims[n1], sims[n2])
                    cls = 'pf' if d < CVD_DE_BAD else ('p0' if d < CVD_DE_WARN else 'p2')
                    if d < CVD_DE_WARN:
                        worst.append((d, n1, n2))
                    h.append(f'<td class="{cls}">{d:.3f}</td>')
                h.append('</tr>')
            h.append('</table>')
            if worst:
                worst.sort()
                h.append('<p class="small">要注意ペア: '
                         + ', '.join(f'{a}–{b} ({d:.3f})' for d, a, b in worst) + '</p>')
    return ''.join(h)


# ============================================================
# roles.html (plan.md §6 のマッピング表 + 用途モック)
# ============================================================

def html_roles(pal):
    R = {g: {k: v['hex'] for k, v in d.items() if k != 'scrim'}
         for g, d in pal['roles'].items()}
    li, hi, qu = R['light'], R['light_high'], R['light_quiet']
    da, pr, md, sl = R['dark'], R['presentation'], R['markdown'], R['syntax_light']
    h = [f'<!doctype html><meta charset="utf-8"><title>roles</title><style>{CSS}</style>',
         '<h1>ロールマッピング (Phase 3 ドラフト)</h1>',
         '<p class="small">plan.md §6。photo-surface / ダークギャラリーは仮決め (§9 未決)。'
         '正は build.py の ROLES 定数 → palette.json roles</p>']

    # --- ロール表 ---
    for group, roles in pal['roles'].items():
        h.append(f'<h2>{group}</h2><table><tr><th>ロール</th><th>参照</th><th>hex</th><th>見本</th></tr>')
        for k, v in roles.items():
            if k == 'scrim':
                continue
            h.append(f'<tr><td>{k}</td><td>{v["ref"]}</td><td>{v["hex"]}</td>'
                     f'<td style="background:{v["hex"]}">&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>')
        h.append('</table>')

    # --- プレゼンモック ---
    h.append('<h2>モック 1: スライド (light_high + presentation)</h2>')
    h.append(
        f'<div style="width:640px;aspect-ratio:16/9;background:{li["bg"]};border:1px solid #DDD;'
        f'border-radius:8px;padding:28px;box-sizing:border-box">'
        f'<div style="font-size:22px;font-weight:700;color:{hi["tx"]}">'
        f'Krylov 部分空間法の収束性</div>'
        f'<div style="font-size:12px;color:{hi["tx-2"]};margin:4px 0 14px">'
        f'第 3 回 数値線形代数セミナー</div>'
        f'<div style="font-size:14px;color:{hi["tx"]}">前処理行列 M の選択が'
        f'<b style="color:{pr["emphasis-1"]}">収束速度を支配</b>する。'
        f'条件数が大きい場合は<b style="color:{pr["emphasis-2"]}">破綻に注意</b>。</div>'
        f'<div style="background:{pr["note-fill"]};color:{pr["note-text"]};border-radius:6px;'
        f'padding:8px 12px;margin:12px 0;font-size:13px">注意: 丸め誤差により直交性が失われる</div>'
        f'<div style="background:{pr["info-fill"]};color:{pr["info-text"]};border-radius:6px;'
        f'padding:8px 12px;font-size:13px">補足: 再直交化で回復できる (コスト増)</div>'
        f'<div style="display:flex;gap:6px;align-items:center;margin-top:12px">'
        f'<span style="font-size:11px;color:{hi["tx-2"]}">chart 1–7:</span>'
        + ''.join(f'<span style="display:inline-block;width:34px;height:8px;border-radius:2px;'
                  f'background:{pr[f"chart-{i}"]}" title="chart-{i}"></span>'
                  for i in range(1, 8))
        + '</div>'
        f'<div style="margin-top:10px;font-size:11px;color:{hi["tx-3"]}">'
        f'2026-07-04 / lucretia theme draft</div></div>')

    # --- Markdown モック ---
    h.append('<h2>モック 2: Markdown エディタ (light_high + markdown)</h2>')
    h.append(
        f'<div style="width:560px;background:{li["bg"]};border:1px solid #DDD;border-radius:8px;'
        f'padding:20px 24px;color:{md["body"]};font-size:14px;line-height:1.7">'
        f'<div style="font-size:19px;font-weight:700;color:{md["heading"]};'
        f'border-bottom:1px solid {md["hr"]};padding-bottom:6px">収束判定の実装メモ</div>'
        f'<p>相対残差は <code style="background:{md["code-inline-bg"]};border-radius:3px;'
        f'padding:1px 5px">norm(r) / norm(b)</code> で計算する。'
        f'詳細は <a style="color:{md["link"]}">Saad (2003)</a> を参照。</p>'
        f'<p>ハイライター: '
        f'<mark style="background:{R["highlight"]["yellow"]};padding:0 2px">既定は黄</mark>、'
        f'<mark style="background:{R["highlight"]["green"]};padding:0 2px">補助に緑</mark>、'
        f'<mark style="background:{R["highlight"]["blue"]};padding:0 2px">'
        f'<b>太字にも引ける</b></mark>、'
        f'<mark style="background:{R["highlight"]["red"]};padding:0 2px">注意は赤</mark>。'
        f'黒文字専用 (規約)。</p>'
        f'<div style="border-left:3px solid {md["quote-border"]};color:{md["quote-text"]};'
        f'padding-left:12px;margin:10px 0">停止基準は問題のスケールに依存してはならない。</div>'
        f'<pre style="background:{md["code-block-bg"]};color:{sl["variable"]};margin:0">'
        f'<span style="color:{sl["keyword"]}">if</span> res <span style="color:{sl["operator"]}">&lt;</span> '
        f'<span style="color:{sl["number"]}">1e-12</span>:\n'
        f'    <span style="color:{sl["keyword"]}">return</span> '
        f'<span style="color:{sl["string"]}">"converged"</span></pre></div>')

    # --- コードエディタモック (VS Code 風) ---
    h.append('<h2>モック 3: コードエディタ (syntax_light / syntax_dark + dist/vscode 相当)</h2>'
             '<p class="small">§6.3 sparse highlighting: 変数・呼び出しは無彩色 (Tier 1)、'
             '彩色は キーワード=magenta / 定義=blue / 文字列=green / 数値=purple のみ。'
             '下段はターミナル ANSI (normal / bright)</p>')

    def editor_mock(kind):
        light = kind == 'light'
        ui = {**R['light'], **R['light_high']} if light else R['dark']
        syn = R['syntax_light'] if light else R['syntax_dark']
        ebg = pal['bg']['bg'] if light else ui['bg']
        ebg2 = pal['bg']['bg2'] if light else ui['bg-2']
        sel = pal['accents']['blue'][150 if light else 850]['hex']
        tx, tx2, tx3 = ui['tx'], ui['tx-2'], ui['tx-3']
        K = lambda t: f'<span style="color:{syn["keyword"]}">{t}</span>'
        F = lambda t: f'<span style="color:{syn["definition"]}">{t}</span>'
        S = lambda t: f'<span style="color:{syn["string"]}">{t}</span>'
        N = lambda t: f'<span style="color:{syn["number"]}">{t}</span>'
        O = lambda t: f'<span style="color:{syn["operator"]}">{t}</span>'
        C = lambda t: f'<span style="color:{syn["comment"]};font-style:italic">{t}</span>'
        # 全シンタックスロールが登場するサンプル:
        #   変数=tx / 定義(class,def)=blue / キーワード=magenta / 文字列・docstring=green
        #   数値・True/None=purple / 演算子=operator / コメント=comment
        lines = [
            f'{K("import")} numpy {K("as")} np',
            '',
            C('# 前処理付き反復解法。収束履歴を持つ (Tier 4: コメント)'),
            f'{K("class")} {F("IterativeSolver")}:',
            f'    {S("&quot;&quot;&quot;Krylov 系ソルバの基底クラス&quot;&quot;&quot;")}',
            f'    {K("def")} {F("__init__")}(self, A, M{O("=")}{N("None")}, '
            f'tol{O("=")}{N("1e-10")}, maxiter{O("=")}{N("500")}):',
            f'        self.A, self.M {O("=")} A, M',
            f'        self.tol, self.maxiter {O("=")} tol, maxiter',
            f'        self.converged {O("=")} {N("False")}',
            f'        self.name {O("=")} {S("&quot;PCG&quot;")}',
            '',
            f'    {K("def")} {F("solve")}(self, b, x0{O("=")}{N("None")}):',
            f'        x {O("=")} x0 {K("if")} x0 {K("is")} {K("not")} {N("None")} '
            f'{K("else")} np.zeros_like(b)',
            f'        r {O("=")} b {O("-")} self.A {O("@")} x',
            f'        {K("for")} k {K("in")} {F("range")}(self.maxiter):',
            f'            x, r {O("=")} self.step(x, r, omega{O("=")}{N("0.5")})',
            f'            {K("if")} <span style="background:{sel}">np.linalg.norm(r)</span> '
            f'{O("&lt;")} self.tol {O("*")} np.linalg.norm(b):',
            f'                self.converged {O("=")} {N("True")}',
            f'                {K("return")} x, k  ' + C('# 相対残差で収束判定'),
            f'        {K("raise")} {F("RuntimeError")}({S("f&quot;diverged: iter={{k}}&quot;")})',
        ]
        hl_line = 15  # 0-origin: self.step の行をカレント行に
        rows = []
        for i, ln in enumerate(lines):
            lnc = tx2 if i == hl_line else tx3
            lbg = f'background:{ebg2};' if i == hl_line else ''
            rows.append(
                f'<div style="display:flex;{lbg}">'
                f'<span style="width:34px;text-align:right;padding-right:12px;'
                f'color:{lnc};user-select:none;flex-shrink:0">{i + 1}</span>'
                f'<span style="color:{tx};white-space:pre">{ln or " "}</span></div>')
        # ターミナル ANSI 帯
        band_n, band_b = (600, 400) if light else (300, 200)
        ansi_chips = ''
        for band, lab in ((band_n, 'normal'), (band_b, 'bright')):
            ansi_chips += (f'<div style="display:flex;gap:4px;align-items:center;margin-top:4px">'
                           f'<span style="color:{tx3};font-size:10px;width:44px">{lab}</span>'
                           + ''.join(f'<span style="display:inline-block;width:30px;height:12px;'
                                     f'border-radius:2px;background:'
                                     f'{pal["accents"][c][band]["hex"]}"></span>'
                                     for c in ('red', 'green', 'yellow', 'blue',
                                               'magenta', 'cyan'))
                           + '</div>')
        name = f'Lucretia {"Light" if light else "Dark"}'
        return (
            f'<div style="display:inline-block;vertical-align:top;margin:8px;width:560px;'
            f'border:1px solid #CCC;border-radius:8px;overflow:hidden;'
            f'font-family:ui-monospace,\'SF Mono\',Menlo,monospace;font-size:12px">'
            # タブバー
            f'<div style="display:flex;background:{ebg2};font-size:11px">'
            f'<span style="background:{ebg};color:{tx};padding:6px 14px">pcg.py</span>'
            f'<span style="color:{tx2};padding:6px 14px">solver_test.py</span></div>'
            # エディタ本体
            f'<div style="background:{ebg};padding:10px 0;line-height:1.65">{"".join(rows)}</div>'
            # ターミナル
            f'<div style="background:{ebg};border-top:1px solid {ui["ui-3"]};padding:8px 12px">'
            f'<span style="color:{tx3};font-size:10px">TERMINAL (ANSI)</span>{ansi_chips}</div>'
            # ステータスバー
            f'<div style="background:{ebg2};color:{tx2};font-size:10px;'
            f'padding:4px 12px">{name} — Python · UTF-8 · Ln 16, Col 13</div>'
            f'</div>')

    h.append(editor_mock('light'))
    h.append(editor_mock('dark'))

    # --- ギャラリーモック ---
    h.append('<h2>モック 4: ギャラリー (photo-surface + scrim)</h2>'
             '<p class="small">実写画像は assets/photos/photo-{1,2,3}.jpg から読む'
             '（無ければグラデーションにフォールバック）。1=明るい昼景 / 2=暗部主体 / '
             '3=色数の多い街 のワーストケース 3 種 (plan.md §6.4)</p>')
    # CSS 多重背景: 画像が無ければ後ろのグラデーションが見える
    photos = [
        ('../assets/photos/photo-1.jpg',
         'linear-gradient(135deg,#7A8A99 0%,#C9B8A0 55%,#E8DCC8 100%)',
         '明るい昼景 — scrim black 60%'),
        ('../assets/photos/photo-2.jpg',
         'linear-gradient(160deg,#0A0A0A 0%,#2E2E2E 60%,#6E6E6E 100%)',
         '暗部主体 (B&W) — scrim black 60%'),
        ('../assets/photos/photo-3.jpg',
         'linear-gradient(160deg,#2E3B33 0%,#8A3B2E 60%,#B98F55 100%)',
         '色数の多い街 — scrim black 60%'),
    ]
    sc = pal['roles']['gallery']['scrim']
    ga = R['gallery']
    ps_l = pal['roles']['light']['photo-surface']['ref']
    ps_d = pal['roles']['dark']['photo-surface']['ref']
    for label, surface, txc in ((f'ライト (photo-surface = {ps_l})', li['photo-surface'], hi),
                                (f'ダーク (photo-surface = {ps_d})', da['photo-surface'],
                                 {'tx': da['tx'], 'tx-2': da['tx-2'], 'tx-3': da['tx-3']})):
        h.append(
            f'<div class="card" style="background:{surface};width:360px">'
            f'<div style="color:{txc["tx"]};font-weight:600;margin-bottom:8px">{label}</div>')
        for i, (src, fallback, cap) in enumerate(photos):
            h.append(
                f'<div style="background:url(\'{src}\') center/cover,{fallback};'
                f'height:150px;border-radius:4px;position:relative;margin-top:{8 if i else 0}px">'
                f'<div style="position:absolute;bottom:0;left:0;right:0;background:{sc["black"][60]};'
                f'color:#FFF;font-size:11px;padding:5px 8px;border-radius:0 0 4px 4px">{cap}</div>'
                f'<div style="position:absolute;top:6px;left:6px;background:{sc["black"][40]};'
                f'color:#FFF;font-size:11px;padding:2px 8px;border-radius:3px">scrim 40%</div>'
                f'</div>'
                f'<div style="color:{ga["caption"]};font-size:12px;margin:4px 0 0">キャプション (caption)</div>'
                f'<div style="color:{ga["meta"]};font-size:11px">f/8 · 1/250s · ISO 100 (meta)</div>')
        h.append('</div>')
    return ''.join(h)


# ============================================================
# paper.html (plan.md §6.5 lucretia paper: bg 候補比較 + 読書モック + コントラスト)
# ============================================================

def html_paper(pal):
    P = pal['paper']
    pb = {s: v['hex'] for s, v in P['base'].items()}
    R = {g: {k: v['hex'] for k, v in pal['roles'][g].items()}
         for g in ('paper', 'syntax_paper', 'markdown_paper', 'highlight')}
    pa, syn, md = R['paper'], R['syntax_paper'], R['markdown_paper']
    h = [f'<!doctype html><meta charset="utf-8"><title>paper</title><style>{CSS}</style>',
         '<h1>lucretia paper — 長文読書プロファイル (plan.md §6.5)</h1>',
         '<p class="small">目的: 紙で読む快適さ (低輝度・暖色・非ギラつき) のデジタル近似。'
         'プレゼン・ギャラリーは対象外。bg = P2 (生成り) に確定 (plan.md §9-16)</p>']

    # --- 1. 確定 bg のプレビュー (参考: 現行 bg / Flexoki paper と並置) ---
    h.append('<h2>1. 確定 bg (P2) — 同一の読書サンプルで参考色と並置</h2>')
    long_p = ('反復法の収束は前処理行列の品質に支配される。理論上の収束次数が同じでも、'
              '固有値分布の裾が重い問題では実効的な反復回数が桁で変わることがある。'
              'したがって実装では、残差ノルムの推移を必ず記録し、停滞 (stagnation) を'
              '検出したら再スタートまたは前処理の再構成を行う。')
    o = P['oklch']
    refs = [('paper-bg (確定 P2)', P['bg'], f'({o[0]}, {o[1]}, {o[2]}°)'),
            ('現行 bg', pal['bg']['bg'], '(0.990, 0.006, 95°)'),
            ('Flexoki paper', '#FFFCF0', '(0.990, 0.016, 95°)')]
    for name, bgh, oklch in refs:
        mark = ' ★' if bgh == P['bg'] else ''
        h.append(
            f'<div class="card" style="background:{bgh};width:340px">'
            f'<b style="color:{pa["tx"]}">{name}{mark}</b> '
            f'<span class="small">{bgh} {oklch} — ΔE white '
            f'{deltaE_ok(bgh, WHITE):.3f}</span>'
            f'<p style="color:{pa["tx"]};font-size:13.5px;line-height:1.9;margin:8px 0">'
            f'{long_p}</p>'
            f'<p style="color:{pa["tx-2"]};font-size:12px;margin:4px 0">サブテキスト: '
            f'Saad (2003) 6.4 節、<a style="color:{pa["link"]}">リンクの見え</a>、'
            f'<code style="background:{md["code-inline-bg"]};border-radius:3px;'
            f'padding:1px 5px;color:{pa["tx"]}">norm(r)/norm(b)</code></p>'
            f'<div style="background:{md["code-block-bg"]};border-radius:5px;padding:6px 10px;'
            f'font-size:11.5px;color:{pa["tx-2"]}">bg-2 相当の面 (コードブロック地)</div>'
            f'</div>')

    # --- 2. 暖色 base スケール ---
    h.append('<h2>2. pbase スケール (暖色 H=92。neutral base は暖色 bg 上で青白く浮く)</h2><div>')
    for s in STEPS:
        h.append(chip(pb[s], f'pbase-{s}'))
    h.append('</div><div style="margin-top:6px">比較: neutral base')
    for s in (500, 700, 900):
        h.append(chip(pal['base'][s]['hex'], f'base-{s}'))
    h.append('</div>')

    # --- 3. コントラスト行列 ---
    pfgs = ([('tx (pbase-900)', pa['tx']), ('tx-2 (pbase-700)', pa['tx-2']),
             ('tx-3 (pbase-500)', pa['tx-3']), ('black (参考)', pal['special']['black'])]
            + [(f'{n}-600', pal['accents'][n][600]['hex']) for n in ACCENTS])
    pbgs = [('paper-bg', P['bg']), ('paper-bg2', P['bg2'])]
    h.append(matrix('3. paper ロールのコントラスト', pfgs, pbgs,
                    'tx は「書籍インク」帯: ◎ (≥7:1 & |Lc|≥90) を満たしつつ black の'
                    'ハレーションを避ける。シンタックス 600 帯は現行ライトと同水準'))

    # --- 4. Markdown 読書モック ---
    h.append('<h2>4. 読書モック (markdown_paper + ハイライター)</h2>')
    h.append(
        f'<div style="width:600px;background:{P["bg"]};border:1px solid #DDD;border-radius:8px;'
        f'padding:26px 30px;color:{md["body"]};font-size:14.5px;line-height:1.95">'
        f'<div style="font-size:20px;font-weight:700;color:{md["heading"]};'
        f'border-bottom:1px solid {md["hr"]};padding-bottom:8px">Krylov 部分空間法 — 読書ノート</div>'
        f'<p>{long_p}</p>'
        f'<p><mark style="background:{R["highlight"]["yellow"]};padding:0 2px;color:{md["body"]}">'
        f'停止基準は問題のスケールに依存してはならない</mark>。これは相対残差 '
        f'<code style="background:{md["code-inline-bg"]};border-radius:3px;padding:1px 5px">'
        f'norm(r) / norm(b)</code> を使う理由でもある。詳細は '
        f'<a style="color:{md["link"]}">Saad (2003)</a> を参照。</p>'
        f'<div style="border-left:3px solid {md["quote-border"]};color:{md["quote-text"]};'
        f'padding-left:14px;margin:12px 0">丸め誤差により直交性が失われる場合、'
        f'再直交化で回復できるがコストは増える。</div>'
        f'<pre style="background:{md["code-block-bg"]};color:{syn["variable"]};margin:0">'
        f'<span style="color:{syn["keyword"]}">if</span> res '
        f'<span style="color:{syn["operator"]}">&lt;</span> '
        f'<span style="color:{syn["number"]}">1e-12</span>:\n'
        f'    <span style="color:{syn["keyword"]}">return</span> '
        f'<span style="color:{syn["string"]}">"converged"</span>  '
        f'<span style="color:{syn["comment"]};font-style:italic"># 相対残差で判定</span></pre>'
        f'</div>')
    return ''.join(h)


# ============================================================
# tokens.css (plan.md §7: palette.json から CSS variables を生成)
# ============================================================

def gen_tokens_css(pal):
    ln = ['/* lucretia color theme — generated by scripts/build.py. 手編集しない */',
          ':root {',
          f'  --lu-white: {pal["special"]["white"]};',
          f'  --lu-black: {pal["special"]["black"]};',
          f'  --lu-bg: {pal["bg"]["bg"]};',
          f'  --lu-bg-2: {pal["bg"]["bg2"]};',
          f'  --lu-paper-bg: {pal["paper"]["bg"]};',
          f'  --lu-paper-bg-2: {pal["paper"]["bg2"]};']
    for s in STEPS:
        ln.append(f'  --lu-base-{s}: {pal["base"][s]["hex"]};')
    for s in STEPS:
        ln.append(f'  --lu-pbase-{s}: {pal["paper"]["base"][s]["hex"]};')
    for n in ACCENTS:
        for s in STEPS:
            ln.append(f'  --lu-{n}-{s}: {pal["accents"][n][s]["hex"]};')
    for n in ACCENTS:
        ln.append(f'  --lu-hl-{n}: {pal["highlight"][n]["hex"]};')
    for kind, steps in pal['roles']['gallery']['scrim'].items():
        for a, v in steps.items():
            ln.append(f'  --lu-scrim-{kind}-{a}: {v};')
    ln.append('}')

    def block(sel, groups):
        ln.append(f'{sel} {{')
        for g in groups:
            for k, v in pal['roles'][g].items():
                if k == 'scrim':
                    continue
                ln.append(f'  --{k}: {v["hex"]};')
        ln.append('}')

    block('[data-theme="light"]', ('light', 'light_high'))
    block('[data-theme="light"][data-contrast="quiet"]', ('light_quiet',))
    block('[data-theme="dark"]', ('dark',))
    block('[data-theme="paper"]', ('paper',))
    return '\n'.join(ln) + '\n'


# ============================================================
# degrade.html (plan.md §5.4 劣化シミュレーション)
# ============================================================
DEGRADE_MODES = [
    ('original', '原色', None),
    ('desat', '彩度 -20% (色ずれプロジェクタ)', 'desat'),
    ('gamma', 'ガンマ 1.25 (中間調が沈む)', 'gamma'),
    ('lifted', '黒浮き + レンジ圧縮 (安価な投影)', 'lifted'),
]


def degrade(hx, mode):
    if mode == 'desat':
        L, C, H = hex_to_oklch(hx)
        return oklch_to_hex(L, C * 0.8, H)
    if mode == 'gamma':
        return rgb_to_hex(*(round(255 * (c / 255) ** 1.25) for c in hex_to_rgb(hx)))
    if mode == 'lifted':
        return rgb_to_hex(*(round(255 * (0.12 + 0.78 * c / 255)) for c in hex_to_rgb(hx)))
    return hx


def html_degrade(pal):
    hi = {k: v['hex'] for k, v in pal['roles']['light_high'].items()}
    pr = {k: v['hex'] for k, v in pal['roles']['presentation'].items()}
    h = [f'<!doctype html><meta charset="utf-8"><title>degrade</title><style>{CSS}</style>',
         '<h1>劣化シミュレーション (plan.md §5.4)</h1>',
         '<p class="small">投影・安価モニタで起きる劣化の簡易スクリーニング。'
         '実プロジェクタでの確認の代替ではない。淡色塗りが消えないか・'
         'サブテキストが読めるかを比較する</p>']
    for key, label, mode in DEGRADE_MODES:
        d = lambda x: degrade(x, mode)
        bg = d(pal['bg']['bg'])
        h.append(
            f'<div class="card" style="background:{bg}">'
            f'<b style="color:{d(hi["tx"])}">{label}</b>'
            f'<p style="color:{d(hi["tx"])};margin:6px 0;font-size:13px">本文テキスト。'
            f'<span style="color:{d(hi["tx-2"])}">サブテキスト。</span>'
            f'<span style="color:{d(hi["tx-3"])}">faint。</span></p>'
            f'<p style="margin:6px 0;font-size:13px">'
            f'<b style="color:{d(pr["emphasis-1"])}">強調青</b> / '
            f'<b style="color:{d(pr["emphasis-2"])}">強調赤</b> / '
            f'<span style="color:{d(pr["sub-1"])}">緑</span> / '
            f'<b style="color:{d(pr["sub-3"])}">黄 (太字限定)</b></p>'
            f'<div style="background:{d(pr["note-fill"])};color:{d(pr["note-text"])};'
            f'border-radius:5px;padding:6px 10px;font-size:12px;margin:6px 0">red-100 の注意ボックス</div>'
            f'<div style="background:{d(pr["info-fill"])};color:{d(pr["info-text"])};'
            f'border-radius:5px;padding:6px 10px;font-size:12px">blue-100 の補足ボックス</div>'
            f'<div style="display:flex;gap:4px;margin-top:8px">'
            + ''.join(f'<div style="flex:1;height:22px;border-radius:3px;'
                      f'background:{d(pal["accents"][n][50]["hex"])}"></div>'
                      for n in ('blue', 'red', 'yellow', 'orange', 'green'))
            + '</div><div class="small" style="margin-top:2px">50 帯の塗り (枠線なし)</div>'
            f'</div>')
    return ''.join(h)


# ============================================================
if __name__ == '__main__':
    pal = build_palette()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(ROOT, 'palette.json'), 'w') as f:
        json.dump(pal, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'swatches.html'), 'w') as f:
        f.write(html_swatches(pal))
    with open(os.path.join(OUT, 'contrast.html'), 'w') as f:
        f.write(html_contrast(pal))
    with open(os.path.join(OUT, 'cvd.html'), 'w') as f:
        f.write(html_cvd(pal))
    with open(os.path.join(OUT, 'roles.html'), 'w') as f:
        f.write(html_roles(pal))
    with open(os.path.join(OUT, 'degrade.html'), 'w') as f:
        f.write(html_degrade(pal))
    with open(os.path.join(OUT, 'paper.html'), 'w') as f:
        f.write(html_paper(pal))
    with open(os.path.join(OUT, 'tokens.css'), 'w') as f:
        f.write(gen_tokens_css(pal))

    # コンソールに要約
    print('generated: palette.json, out/{swatches,contrast,cvd,roles,degrade,paper}.html, '
          'out/tokens.css')
    d = pal['bg']
    print(f"\n-- bg (確定) --\n  {d['bg']} (bg2 {d['bg2']}, "
          f"dE_white {d['dE_white']}, dE_paper {d['dE_paper']})")
    p = pal['paper']
    print(f"\n-- paper bg (確定 P2) --\n  {p['bg']} (bg2 {p['bg2']}, "
          f"dE_bg {p['dE_bg']}, dE_white {p['dE_white']})")
    for role in ('tx', 'tx-2', 'tx-3'):
        hx = pal['roles']['paper'][role]['hex']
        print(f"  {role:5s} {hx}  {wcag(hx, p['bg']):5.2f}:1  Lc {apca_lc(hx, p['bg']):+6.1f}")
    print('\n-- 600 step on bg: WCAG / APCA --')
    bgh = pal['bg']['bg']
    for n in ACCENTS:
        hx = pal['accents'][n][600]['hex']
        print(f"  {n:8s} {hx}  {wcag(hx, bgh):5.2f}:1  Lc {apca_lc(hx, bgh):+6.1f}")

    print('\n-- CVD: 最接近ペア上位 3 (ΔEok, step 400 / 600) --')
    for step in (400, 600):
        for kind in ('protan', 'deutan', 'tritan'):
            sims = {n: cvd_hex(pal['accents'][n][step]['hex'], kind) for n in ACCENTS}
            names = list(ACCENTS)
            pairs = sorted((deltaE_ok(sims[a], sims[b]), a, b)
                           for i, a in enumerate(names) for b in names[i + 1:])
            print(f"  {step} {kind:7s}: "
                  + ', '.join(f'{a}-{b} {d:.3f}' for d, a, b in pairs[:3]))
