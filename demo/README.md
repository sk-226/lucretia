# Native app checks

Use a test vault or test editor profile so unrelated settings are easy to separate.

## VS Code and Cursor

Install `dist/vscode/lucretia-theme.vsix` through **Extensions: Install from VSIX**.
Confirm the extension is `sugu.lucretia-theme`, the version in `VERSION`, with all three
appearances. Repeat in each editor. Open the files in this folder and switch
among Light, Dark, and Paper. `check.ts` includes intentional errors.
`check.tex` needs a LaTeX grammar such as LaTeX Workshop to inspect its tokens.

Check the command palette, file picker, tabs, sidebar, search, selection,
completion, hover, diagnostics, scrollbar, and integrated terminal. Compare
bracket pairs with and without your current font's ligatures. A font's glyph
shaping can affect bracket coloring; do not change the theme based on one font
without checking another. Use a temporary Git edit to inspect added / removed
lines, gutter marks, and diff colors.

## Ghostty

Install all three files as described in the main README. Test an explicit
Paper theme, then Light, then Dark. Reload after changing the configuration.
Test the optional light / dark configuration by changing the system appearance.
Check cursor text, selected text, normal colors, and bright colors.

In zsh, print the sixteen background and foreground colors:

```sh
for i in {0..15}; do print -nP "%K{$i}  %k"; done; echo
for i in {0..15}; do print -nP "%F{$i}A%f "; done; echo
```

Compare the slots with the VS Code terminal. Existing Ghostty color overrides
must be removed from the test config before judging the theme.

## Obsidian

First test the standalone theme without Minimal or Style Settings. In
**Settings > Appearance > Base color scheme**, select **Light** and expect Paper,
then select **Dark** and expect Dark. Return the setting to **Light** before
testing Paper / Light switching and persistence. Open `check.md` in reading view
and Live Preview. Check headings, links, inline code, fenced code, highlights,
quotes, callouts, tables, checkboxes, search, the command palette, and the sidebar.

Enable Style Settings. The command palette must contain exactly one
**Style Settings: Toggle Lucretia Paper / Light** command. Run it to get Light,
then again to get Paper. Quit and restart Obsidian after choosing Light and confirm
the choice survives. Change the base color scheme to Dark and back to Light;
expect the previous light appearance.
While in Dark, run the toggle and confirm the display stays Dark, then return
to light mode and check the changed choice. Check a detached window as well;
class propagation into secondary windows is controlled by Obsidian and Style
Settings and needs native verification.

Check **Adapt to system** separately. On restart, expect Obsidian to follow the OS.
Its light / dark command and Minimal Theme Settings' equivalent only change the
current session in this mode. Return the base color scheme to **Light** and confirm
the saved Lucretia Paper / Light choice remains available.

Repeat with Minimal and only `lucretia-minimal.css` enabled. Disable the standalone
theme and any 0.2.x `lucretia-paper.css` snippet. Use Minimal's default schemes and
clear only prior color overrides. Layout and typography should remain Minimal's.
There must be no mixture of Paper and Light after a toggle. Test one normal
Minimal preset to identify any remaining override conflicts.

Repeat on the mobile device you use. Confirm the active config folder contains
the theme / snippet and Style Settings. Open the command palette through the
mobile UI and repeat the toggle, restart, and light / dark checks. Check the
mobile sidebar and dialogs. Browser viewport tests alone do not verify mobile
Obsidian behavior.

## Updating

Install the new VSIX over the prior extension. Replace the Ghostty theme files
and the Obsidian theme folder or snippet without replacing settings files.
Confirm the Obsidian light-appearance choice remains saved.
