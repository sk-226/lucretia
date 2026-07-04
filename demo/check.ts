// Lucretia theme check — check.ts
//
// チェック項目:
//   ① 変数・引数・プロパティが無彩色 (tx) のまま = semanticHighlighting が効いている
//   ② カーソルを model に置く → 読み出し箇所は青系、代入行は magenta 系の下地
//      (wordHighlight / wordHighlightStrong)
//   ③ 文字列をダブルクリック選択 → 同じ文字列に薄い下地 (selectionHighlight)
//   ④ 未定義関数の赤波線 = editorError、右端 overview ruler のマークも確認
//   ⑤ 括弧にカーソル → bracketMatch。入れ子は 6 色サイクル
//   ⑥ Cmd+F「確認」→ findMatch。確認。

{{{{{{}}}}}} // 連続括弧 6 段: 濃青→明橙→薄紫→黄土→深紅紫→青緑 で開き、正確に逆順で閉じる

const model = createModel("lucretia", 0.93);

export function render(input: string, depth: number): string {
  return input.repeat(model.depth);
}

const tree = f1(f2[f3({ k: f5[f6(model)] })]); // 括弧 6 色: blue→orange→purple→yellow→magenta→cyan

const wrong: number = "type error"; // 赤波線 (editorError) の確認

/** @deprecated 取り消し線描画の確認用 */
function legacy() {}
legacy();

// ↓ この行はわざと壊してあるので必ずファイル末尾に置く
//   (パースエラーが後続の行の赤波線として波及するため)
const bad = fn(model)); // 最後の ) が unexpectedBracket の赤になる
