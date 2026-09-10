# Lucretia

A color theme for code and notes, in Light, Dark, and Paper.

| Appearance | Background | Text |
| --- | --- | --- |
| Light | `#FDFCF7` | `#100F0E` |
| Dark | `#100F0E` | `#E5E4E3` |
| Paper | `#F8F5EB` | `#2F2E2A` |

[Color codes and CSS usage](dist/palette/README.md) · [Design notes](DESIGN.md)

## Preview

Download the repository and open `docs/index.html`. Choose Light, Dark, or Paper,
and click a color to copy its code. No build or server is needed.
The page contains browser previews, not app screenshots.

## Install

The files in `dist/` are ready to use. You do not need Python, Node.js, or Git.
On a GitHub file page, use **Download raw file** to save a file, or download the
whole repository with **Code > Download ZIP**.

### VS Code and Cursor

Download [lucretia-theme.vsix](dist/vscode/lucretia-theme.vsix).
In the editor you use, open the command palette and run **Extensions: Install from VSIX**.
Select the file, then run **Preferences: Color Theme** and choose **Lucretia Light**,
**Lucretia Dark**, or **Lucretia Paper**. The same VSIX works in both editors.

To update, download and install the new VSIX. Reload the editor when prompted.

### Ghostty

Download [Light](dist/ghostty/Lucretia%20Light),
[Dark](dist/ghostty/Lucretia%20Dark), or [Paper](dist/ghostty/Lucretia%20Paper).
Copy the files, keeping their names, into `~/.config/ghostty/themes/`.
If you set `XDG_CONFIG_HOME`, use `$XDG_CONFIG_HOME/ghostty/themes/` instead.

Add this line to your Ghostty config:

```ini
theme = Lucretia Paper
```

Or install both Paper and Dark and follow the system appearance:

```ini
theme = light:Lucretia Paper,dark:Lucretia Dark
```

Reload Ghostty's configuration or restart it. Existing explicit color options in
your config override the theme, so remove those only when you want Lucretia's colors.
To update, replace the theme files and reload the configuration.

### Obsidian

Choose one of the following methods. Do not enable both at once.
If upgrading from 0.2.x, disable the `lucretia-paper.css` snippet before enabling
either method.

**Lucretia theme.** Download [Lucretia.zip](dist/obsidian/Lucretia.zip), extract it,
and put the `Lucretia` folder in your vault's `.obsidian/themes/` directory.
The result must include `.obsidian/themes/Lucretia/theme.css` and `manifest.json`.
In **Settings > Appearance**, select **Lucretia**. Minimal is not required.

**Minimal overlay.** Keep Minimal selected as your theme. Download
[lucretia-minimal.css](dist/obsidian/lucretia-minimal.css), put it in
`.obsidian/snippets/`, and enable it under **Appearance > CSS snippets**.
Lucretia replaces the colors; Minimal still controls layout and typography.
Start with Minimal's default color scheme. Existing custom color settings or
other color snippets can override it;
reset those color overrides rather than resetting all of your Minimal settings.

Both methods use Paper in light mode and Dark in dark mode.
For **Paper / Light switching**, install and enable the community plugin
[Style Settings](https://github.com/community-archive/obsidian-style-settings).
Open the command palette and run **Style Settings: Toggle Lucretia Paper / Light**.
Run it again to return to Paper. You can assign a hotkey to this command.

Style Settings saves the choice. Dark mode remains Dark; returning to light mode
restores the previous Paper / Light choice. The command does not change Obsidian's
light / dark setting. Without the plugin, light mode uses Paper.

To keep your appearance after restarting, set **Settings > Appearance > Base color
scheme** to **Light** or **Dark**. With **Adapt to system**, Obsidian follows the OS
at startup; its light / dark toggle only changes the current session. Minimal
Theme Settings' light / dark command behaves the same way. The saved Lucretia
Paper / Light choice applies whenever Obsidian is in light mode.

The same files target desktop and mobile. Use the active config folder on each
device, which may differ from `.obsidian`. On mobile, transfer the theme or snippet
through your vault's file or sync setup. Install or sync Style Settings as well
when you need switching. App-specific checks are in [demo/README.md](demo/README.md).

To update, replace the theme folder or snippet, then reload Obsidian. Do not
replace your vault settings or Style Settings data.

## Project

`dist/` contains the finished files. `docs/` is the preview site. `scripts/` contains
the generator. `review/` contains the detailed color checks, separate from the site.
See [DEVELOPMENT.md](DEVELOPMENT.md) for building, testing, and publishing the preview.

## Attribution

Lucretia is inspired by [Flexoki](https://stephango.com/flexoki) by Steph Ango.
The [third-party notice](THIRD_PARTY_NOTICES.md) is included with the app files.
