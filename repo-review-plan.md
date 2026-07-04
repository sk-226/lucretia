# リポジトリレビュー修正計画

レビュー日: 2026-07-04  
対象: リポジトリ全体。ただし、現在 `scripts/build.py` に入っている `paper` 関連の未コミット実験は今回いったん対象外にする。

## レビュー要約

このリポジトリは、`scripts/build.py` を生成元として `palette.json` と `out/` を作り、`scripts/build_dist.py` で `palette.json` から `dist/` を作る小さなカラーテーマ生成プロジェクトである。README に書かれている「生成物は手編集しない」という契約自体は明確。

大きな問題は色変換アルゴリズムそのものではない。`scripts/color.py` の自己テストは通り、JSON も妥当で、一時コピー上では生成スクリプトも正常終了した。主な修正対象は、生成物の同期漏れを防ぐ仕組み、一時ファイル管理、ドキュメントと実装の現在地の同期、生成処理の堅牢性である。

## 今回の対象外

- `paper` プロファイルの設計・実装・生成物追加。
- `paper` 関連の `plan.md §6.5` 整備。
- `out/paper.html` や paper 用 CSS/Obsidian/VS Code 展開。

## レビュー中に確認したこと

- `python3 scripts/color.py` は成功。
- 一時コピー上で `python3 scripts/build.py` と `python3 scripts/build_dist.py` は成功。
- 一時コピー上で `python3 -m py_compile scripts/color.py scripts/build.py scripts/build_dist.py` は成功。
- `palette.json` と VS Code テーマ JSON は `python3 -m json.tool` でパース成功。

## Findings

### P1. 生成物の同期漏れを検出するチェックがない

根拠:
- README は `python3 scripts/build.py && python3 scripts/build_dist.py` を再生成手順としている。
- 生成元、確認用 HTML、CSS variables、配布用 VS Code/Obsidian 成果物がすべて Git 管理されている。
- しかし、生成物が現在の生成元と一致しているかを自動確認するコマンドがない。

なぜ直すべきか:
- このプロジェクトは確認用 HTML や配布用テーマ JSON も意図的にコミットする設計である。チェックがないと、生成元だけ変わって成果物が古い状態で残る。
- 色テーマでは `palette.json`, `out/tokens.css`, `dist/vscode/*`, `dist/obsidian/*` のどれか一つだけ古い状態でも利用者の見え方がずれる。

Goal:
- 生成物の stale 状態をコミット前に検出できるようにする。

Tasks:
- [ ] `scripts/check_generated.py` または `Makefile` ターゲットを追加する。
- [ ] チェック内で `scripts/build.py` と `scripts/build_dist.py` を実行し、最後に `git diff --exit-code` で差分を検出する。
- [ ] ネットワーク不要・標準ライブラリのみで動く形にする。
- [ ] README にチェック手順を追加する。

Acceptance criteria:
- クリーンな checkout ではチェックが通る。
- 生成定数だけ変えて再生成しない場合はチェックが失敗する。
- ネットワークアクセスを必要としない。

## Goal 2. リポジトリの一時ファイル管理を整理する

根拠:
- `scripts/__pycache__/color.cpython-314.pyc` が Git 管理下にある。
- ローカルに `.DS_Store` が存在する。
- リポジトリに `.gitignore` がない。

なぜ直すべきか:
- Python bytecode や macOS メタデータは、テスト実行や Finder 操作だけで変わりうる。
- 生成物の差分をレビューしたいリポジトリで、bytecode のような実装と無関係の差分が混ざると判断コストが上がる。

Goal:
- ソース、意図した生成成果物、意図したサンプルアセットだけが Git 管理される状態にする。

Tasks:
- [ ] `.gitignore` を追加し、`.DS_Store`, `__pycache__/`, `*.py[cod]`, 一般的な editor 一時ファイルを無視する。
- [ ] `scripts/__pycache__/color.cpython-314.pyc` を Git 管理から外す。
- [ ] `assets/photos/photo-*.jpg` を fixtures として持つのか決める。持つなら README に意図を書く。持たないなら ignore してグラデーション fallback 前提にする。

Acceptance criteria:
- Python スクリプトを実行しても bytecode の tracked diff が出ない。
- 通常のテスト・再生成後、意図した生成物以外で `git status --short` が汚れない。

## Goal 3. ドキュメントを現在の実装状態に合わせる

根拠:
- `plan.md:261-268` は `coloraide` や `colorspacious` などの計画上の依存を残しているが、現実の実装は依存なしの Python スクリプトになっている。
- `palette.json` の meta は Phase 3 ロールや photo-surface を仮決め扱いしているが、`plan.md:303-306` では chart/highlighter/photo-surface が決定済みとして記録されている。
- README は Phase 3/4 の状態を説明しているが、「検証済み」「ドラフト」「実地確認待ち」の境界が生成 meta と完全には一致していない。

なぜ直すべきか:
- このプロジェクトでは `plan.md` が設計の単一ソースになっている。古い計画・決定済み事項・実験中事項が混ざると、次に何を信じて直せばよいか分かりにくくなる。

Goal:
- `plan.md`, `README.md`, 生成 meta が同じ現在地を示すようにする。

Tasks:
- [ ] `plan.md §7` を依存なし Python 実装に合わせて更新する。外部ツール一覧を残すなら「参考/当初計画」と明記する。
- [ ] `scripts/build.py` の `palette.json` meta 生成文を、決定済み・未決の実態に合わせる。
- [ ] `plan.md §9 未決` に現在の未決事項を追加する。
- [ ] README は短く保ち、詳細な設計理由は `plan.md` に寄せる。

Acceptance criteria:
- 読者が README と `plan.md` だけで、完了フェーズ・決定済みロール・生成される成果物を判断できる。

## Goal 4. 配布物生成のスモークチェックを追加する

根拠:
- `scripts/build_dist.py` は `palette.json` から VS Code テーマと Obsidian CSS を生成する。
- 現状は「ファイルを書けたか」以上の検証がなく、テーマ JSON の参照パス、最低限の color key、Obsidian の主要 CSS 変数が揃っているかを自動では見ていない。

なぜ直すべきか:
- `dist/` は実際にユーザーがエディタへ入れる成果物なので、生成成功だけでは不十分。
- 生成元のロール名変更やキー変更が、配布物では静かに欠落として表れる可能性がある。

Goal:
- 配布物が最低限インストール可能・参照可能な形で生成されていることをローカルで確認する。

Tasks:
- [ ] VS Code `package.json` の theme path が実在することを確認するチェックを追加する。
- [ ] Light/Dark theme JSON が `name`, `type`, `colors`, `tokenColors` を持つことを確認する。
- [ ] 主要 color key と ANSI 16 色が欠けていないことを確認する。
- [ ] Obsidian CSS に `--background-primary`, `--text-normal`, `--link-color`, `--text-highlight-bg`, `hl-*` が出ていることを確認する。
- [ ] このチェックを Goal 1 の generated-artifact drift check に統合するか、別コマンドとして README に載せる。

Acceptance criteria:
- `dist/vscode/package.json` から辿れる theme file がすべて存在する。
- VS Code theme JSON と Obsidian CSS の最低限のキー欠落を検出できる。
- チェックは標準ライブラリのみで実行できる。

## Goal 5. 生成処理のエンコーディングと差分の見やすさを改善する

根拠:
- `scripts/build.py` と `scripts/build_dist.py` は `open(...)` に `encoding` を指定していない。
- 生成 HTML はほぼ 1 行で、再生成時の `out/roles.html` 差分が実質的に全体差分になりやすい。

なぜ直すべきか:
- 生成 CSS/HTML とドキュメントには日本語が含まれる。明示的な UTF-8 指定がないと、環境依存の失敗を招きやすい。
- 生成物をコミットする方針なら、生成物の差分が局所的にレビューできることは保守性に直結する。

Goal:
- 生成物をより決定的でレビューしやすくする。

Tasks:
- [ ] テキスト読み書きすべてに `encoding="utf-8"` を指定する。
- [ ] 生成 JSON/HTML/CSS に末尾改行を付ける。
- [ ] HTML 生成はセクションごとに `\n` で結合し、再生成差分が局所化されるようにする。
- [ ] HTML がさらに大きくなるまでは、重いテンプレート依存は増やさない。

Acceptance criteria:
- UTF-8 環境で再生成結果が安定する。
- 生成物の差分がレビュー可能な粒度になる。

## Suggested Execution Order

1. Goal 2 で一時ファイル管理を先に整理する。
2. Goal 1 の drift check を追加して、以後の作業で同期漏れを検出できるようにする。
3. Goal 4 の配布物スモークチェックを追加する。
4. Goal 3 でドキュメントと meta を同期する。
5. Goal 5 で生成処理の堅牢性とレビューしやすさを改善する。

## Final Verification Checklist

- [ ] `python3 scripts/color.py`
- [ ] `python3 scripts/build.py`
- [ ] `python3 scripts/build_dist.py`
- [ ] 追加後の生成物 drift check
- [ ] 追加後の配布物 smoke check
- [ ] `python3 -m json.tool palette.json`
- [ ] `python3 -m json.tool dist/vscode/themes/lucretia-light-color-theme.json`
- [ ] `python3 -m json.tool dist/vscode/themes/lucretia-dark-color-theme.json`
- [ ] `out/roles.html`, `out/contrast.html`, `out/cvd.html`, `out/degrade.html` を開いて確認
