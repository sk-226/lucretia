// Lucretia theme check - check.ts
//
// Checks:
//   1. Variables, parameters, and properties stay neutral via semantic tokens.
//   2. Placing the cursor on model shows read/write word highlights.
//   3. Selecting a string shows selectionHighlight on matching strings.
//   4. The type error shows editorError and an overview-ruler marker.
//   5. Bracket matching works, and nested pairs use the six-color cycle.
//   6. Cmd+F on "check" shows findMatch and findMatchHighlight.

{{{{{{}}}}}} // Six bracket levels open blue -> orange -> purple -> yellow -> magenta -> cyan.

const model = createModel("lucretia", 0.93);

export function render(input: string, depth: number): string {
  return input.repeat(model.depth);
}

const tree = f1(f2[f3({ k: f5[f6(model)] })]); // Six bracket colors: blue -> orange -> purple -> yellow -> magenta -> cyan.

const wrong: number = "type error"; // Intentional editorError squiggle.

/** @deprecated Confirms deprecated-symbol strikethrough. */
function legacy() {}
legacy();

// Keep this intentionally broken line last so the parse error does not leak
// into later checks.
const bad = fn(model)); // The final ) should use unexpectedBracket red.
