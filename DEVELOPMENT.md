# Lucretia 開発メモ

このファイルは開発・検証用の作業メモです。
README は初めて見る人に「何のプロジェクトか」を伝える場所として短く保つため、
進捗、再生成手順、検証規約、作業時の注意はここに置きます。

## 基本方針

設計方針・要求仕様・評価基準はすべて `plan.md` にある。
作業を始める前に必ず `plan.md` を読み、決定事項は `plan.md` §9 に集約する。

## 現状（Phase 1–2 完了、Phase 3 ドラフト生成済み）

```
plan.md               設計計画（単一の正）。決定事項は §9 に集約
scripts/color.py      色変換・評価ライブラリ（依存なし）
                      sRGB<->OKLCH / ΔEok / WCAG 2.x / APCA-W3 / CVD (Machado 2009)
                      APCA は公式リファレンス 4 値と一致確認済み（python3 scripts/color.py）
scripts/build.py      パレット生成 + HTML 出力。設計パラメータ・ROLES は冒頭の定数に集約
palette.json          生成結果 + ロールマッピング（単一ソース。手編集せず build.py を直す）
out/swatches.html     確定 bg のプレビュー / base スケール / アクセント一覧 / コード階層デモ
out/contrast.html     コントラスト行列（WCAG + APCA）+ 淡色帯 50–200 の塗り/文字検証
out/cvd.html          P/D/T 型 (Machado 2009) シミュレーション + ペア ΔEok 行列
out/roles.html        ロール表 + 用途モック（スライド / Markdown / コードエディタ / ギャラリー実写）
out/overview.html     パレット一覧ツアー（palette / syntax / base / accents / extended / mappings）
                      + light/dark/paper 比較（エディタ / Markdown / plot / ギャラリー / スライド）
out/degrade.html      投影劣化シミュレーション（彩度低下 / ガンマ / 黒浮き）
out/paper.html        lucretia paper（長文読書プロファイル §6.5）: 確定 bg プレビュー + 読書モック
out/tokens.css        CSS variables（--lu-* パレット + data-theme/data-contrast ロール）
scripts/build_dist.py 配布物生成（palette.json → dist/）
scripts/plot_check.py chart-1..7 の matplotlib 検証プロット（要 numpy/matplotlib、手動実行）
dist/vscode/          VS Code テーマ拡張（Light / Dark / Paper + ターミナル ANSI 16）
dist/obsidian/        Obsidian CSS スニペット（読書用 lucretia-paper.css）
assets/photos/        ギャラリーモック用の実写 3 枚（保存済み）
assets/plots/         plot_check.py の生成 PNG（overview.html が参照。chart ロール変更時に再生成）
```

## 再生成

```sh
python3 scripts/color.py
python3 scripts/build.py
python3 scripts/build_dist.py
```

パレットの正は `scripts/build.py` のパラメータ。
`palette.json`、`out/`、`dist/` は生成物なので、色の手打ち修正はしない。

## エディタテーマの試用

VS Code / Cursor テーマの試用:

```sh
./scripts/install_editor_theme.sh
```

両方のエディタを再起動し、テーマ選択で "Lucretia Light" / "Lucretia Dark" /
"Lucretia Paper"（長文読書用）を選ぶ。

このスクリプトは同じ VSIX を VS Code と Cursor の両方に入れる。
片方だけ symlink にすると、Cursor の `.obsolete` キャッシュと拡張バージョンが衝突して
テーマが一覧から消えることがあるため。

Obsidian: `dist/obsidian/lucretia-paper.css` を vault の `.obsidian/snippets/` にコピーして有効化。
Obsidian 用は当面 lucretia paper のみを生成する。Minimal theme の配色トークンを上書きし、
レイアウト・タイポグラフィ・plugin 互換性は Minimal 側に任せる。
mobile が別 config/profile を使う vault では、その profile の snippets にも同じ CSS を入れ、
appearance 側で Minimal theme と `lucretia-paper` snippet を有効化する。

エディタ UI の確認手順は `demo/README.md` を参照する。

## 生成モデルの検証状況

Flexoki 実測から導いたパラメータ（hue / Cmax / L 補正）で生成した 600 系は
原典 Flexoki とほぼ一致（例: red #AF3028 vs #AF3029）。
生成モデル自体は Flexoki を再現できており、ここからパラメータを動かして
自分のテーマへ寄せていく段階。

## 次のタスク（plan.md §8）

**~~Phase 1 — bg / base の確定~~ 完了（2026-07）**:
bg = #FDFCF7、base = neutral（plan.md §9-7, 8）

**~~Phase 2 — アクセント検証~~ 完了（2026-07）**:
検証結果と規約は plan.md §9-9 に集約
（yellow 太字限定 / orange–green 隣接禁止 / 淡色帯 両用途合格）。
CVD・淡色帯の詳細は `out/cvd.html`, `out/contrast.html`。

**Phase 3 — ロールマッピング: ドラフト生成済み、要レビュー**

- `build.py` の `ROLES` 定数 → `palette.json` roles / `out/roles.html` / `out/tokens.css`
- APCA 実測に基づく確定: ダーク bg = black、シンタックスはライト 600 帯・ダーク 300 帯中心、
  keyword=magenta / number=purple（plan.md §9-10, 11）
- chart-1〜7（MATLAB 風 7 色、CVD 最適順。plan.md §9-12）と
  ハイライター hl-*（黒文字専用、plan.md §9-13）を追加
- photo-surface 確定: ライト = bg（§9-14）/ ダーク = base-950（§9-15、ダークギャラリー採用）
- `out/roles.html` のモック 4 種（スライド / Markdown / コード / ギャラリー）を目視確認

**lucretia paper（長文読書プロファイル、2026-07 追加）:
bg = P2 #F8F5EB 確定（plan.md §9-16）**

- 設計は plan.md §6.5。暖色 pbase + 書籍インク帯 tx（pbase-900、12.5:1 / Lc +94）
- VS Code "Lucretia Paper" / Obsidian `lucretia-paper.css` を数日実運用して
  インク帯の適否を確認（plan.md §9 未決-2）

**Phase 4 — 実地検証（要ユーザー）**

- ~~検証写真の保存~~ 済み → `out/roles.html` のギャラリーモックが実写表示
- ~~VS Code テーマ試作~~ `dist/vscode/` に生成済み → 実際にインストールして数日使う
- `out/degrade.html` で劣化スクリーニング → 実プロジェクタで 1 回以上確認（plan.md §5.3–5.4）
- サンプルスライドで実プレゼン、Markdown 実運用（`dist/obsidian/` スニペット）

**Phase 5**:
パッケージ化の残り（仕様ドキュメント、vsix 化、プレゼンテンプレの色定義）。
詳細は plan.md §8。

## 規約

- 全色 sRGB 内・OKLCH で管理（plan.md §5.4）
- パレットの正は `build.py` のパラメータ。hex の手打ち修正はしない（`dist/` も手編集しない）
- 変更のたびに `python3 scripts/color.py`（テスト）→ `python3 scripts/build.py` →
  `python3 scripts/build_dist.py` を実行
- Flexoki 由来・参考の説明を公開物に残す場合は、`THIRD_PARTY_NOTICES.md` の帰属と
  MIT License 通知が同梱または参照されることを確認する
