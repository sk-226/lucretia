# テーマ動作確認手順

`check.tex` / `check.ts` / `check.md` を開くとエディタ内の色は一通り確認できる
(各ファイル冒頭のコメント参照)。以下はエディタ UI 側のチェック。

## 準備

1. ウィンドウ再読み込み: `Cmd+Shift+P` → `Developer: Reload Window`
2. テーマ切替: `Cmd+K Cmd+T` → Lucretia Paper / Light / Dark
3. VSCode と Cursor の両方で同じ手順を繰り返す

## UI チェックリスト

| 項目 | 手順 | 期待される見え方 |
|---|---|---|
| タブ | check.* を 3 つ開く | アクティブタブ上端に blue のボーダー、非アクティブは bg-2 |
| コマンドパレット | `Cmd+P` / `Cmd+Shift+P` | パネル = bg-2、フォーカス行 = 選択色 (blue-150/850) |
| Explorer の Git 色 | この demo/ が未コミットの間 | ファイル名が緑 + U (untracked) |
| Git gutter | demo/ をコミット → check.ts を編集 | 追加=緑バー、変更=青バー、削除=赤三角 |
| diff | Source Control で変更ファイルを開く | 追加行=緑の透過、削除行=赤の透過 |
| 検索ウィジェット | `Cmd+F` | ウィジェット = bg-2 + ui-3 ボーダー、入力欄はテーマ色 |
| サジェスト | check.ts で `model.` と打つ | 補完リストの選択行 = 選択色 |
| ホバー | check.ts の関数名にマウスオーバー | bg-2 + ui-3 ボーダー |
| overview ruler | check.ts を開く | 右端にエラー(赤)・検索(黄)のマーク |
| スクロールバー | 長いファイルでスクロール | 半透明グレーのスライダー |
| ターミナル ANSI | 下のコマンドを実行 | 16 色スウォッチ |

ターミナル ANSI 確認 (zsh):

```sh
for i in {0..15}; do print -nP "%K{$i}  %k"; done; echo
for i in {0..15}; do print -nP "%F{$i}A%f "; done; echo
```

## 注意

- 太字・斜体はエディタフォントに bold / italic フェイスがあることが前提
- `check.tex` のシンタックスは LaTeX Workshop 拡張が必要
- **`editor.fontLigatures: true` は括弧色付けを壊す**: リガチャフォント
  (JetBrains Mono, UDEV Gothic NFLG 等) が連続括弧を合字化すると
  1 グリフ = 1 色になり「2 文字ずつ同色」に見える。対策は
  `"editor.fontLigatures": false`、または非リガチャ版フォント
  (UDEV Gothic **NF** など) を使う

## テーマ更新の反映方法 (エディタ別)

- **VS Code / Cursor 共通**: リポジトリ直下で次を実行する:
  ```sh
  ./scripts/install_editor_theme.sh
  ```
  同じ VSIX を両方へ入れる。Cursor だけ dist へのシンボリックリンクにすると、
  VS Code とは更新モデルがずれ、Cursor の `.obsolete` キャッシュに残った version と
  衝突してテーマが一覧から消えることがある。
- 更新後は両方のエディタを再起動 (Cmd+Q) する。単なるウィンドウ再読み込みでは、
  拡張一覧キャッシュが古いまま残る場合がある。
