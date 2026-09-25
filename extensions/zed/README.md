# Lucretia for Zed

Light, Dark, and Paper themes, generated from Lucretia's shared palette.

## Install a local theme

Copy `themes/lucretia.json` into `~/.config/zed/themes/` on macOS or Linux.
On Windows, use `%USERPROFILE%\AppData\Roaming\Zed\themes\`.
Create the directory if it does not exist. A custom Zed config directory needs
its own `themes/` subdirectory.

Restart Zed, run **theme selector: toggle** from the command palette, and choose
**Lucretia Light**, **Lucretia Dark**, or **Lucretia Paper**. The JSON contains
all three appearances. No build tools or language servers are required to install it.

For system appearance switching, add this entry to your existing settings; do not
replace the rest of your settings file:

```json
{
  "theme": {
    "mode": "system",
    "light": "Lucretia Paper",
    "dark": "Lucretia Dark"
  }
}
```

Use `Lucretia Light` instead of `Lucretia Paper` for the lighter page.
To update, replace `lucretia.json` and restart Zed.

## Development extension

Alternatively, use **zed: install dev extension** and select the directory
containing this README and `extension.toml` (`extensions/zed` in the source repository).
Do not select the repository root. Use either the local JSON or the development
extension, not both: they register the same theme names.

This directory is the Zed extension root. It is a data-only theme extension: it
does not install languages, change settings, or run code in the editor. Keep the
version in `extension.toml` equal to the repository's `VERSION`.

## Publishing

The Lucretia repository can stay a monorepo. In `zed-industries/extensions`, the
submodule can point at this repository and use `path = "extensions/zed"`.

`LICENSE` is the project's MIT license, linked from the repository root.
`THIRD_PARTY_NOTICES.md` records the Flexoki attribution and license.

## Highlighting

Variables, parameters, and properties use the editor text color. Functions and
types use blue; keywords use magenta, strings green, and constants purple.
Comments are italic. Markdown headings and strong emphasis are bold; emphasis
is italic. UI, Git, diagnostic, selection, and terminal colors use the same
palette as the other Lucretia ports, including all 16 normal/bright ANSI colors.
Zed's extra dim ANSI slots blend normal colors one-third toward the background.

Zed's Tree-sitter captures and optional language-server semantic token rules
are not VS Code TextMate scopes. The theme styles captures but cannot change
which source ranges a language grammar or server supplies. Declaration-only
coloring and nested markup therefore depend on the installed language support.
The v0.2.0 theme schema does not expose syntax underline or strikethrough fields,
nor a dedicated six-color bracket-pair setting; those VS Code settings are not
silently emitted as unsupported Zed keys. Brackets use the neutral punctuation
color, with a matching-bracket background.

Existing `theme_overrides` and explicit semantic-token rules can override these
styles. This theme does not enable semantic tokens or change your font settings.
Use a font with an italic face to check the intended comment appearance.

## References

- [Zed themes and local installation](https://zed.dev/docs/themes)
- [Theme extension schema](https://zed.dev/schema/themes/v0.2.0.json)
- [Syntax captures](https://zed.dev/docs/extensions/languages#syntax-highlighting)
- [Semantic token rules](https://zed.dev/docs/semantic-tokens)
- [Source](https://github.com/sk-226/lucretia)

Inspired by Flexoki. See `THIRD_PARTY_NOTICES.md`.
