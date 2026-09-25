# Development

Python 3.10 or later is sufficient for the build and core checks. No packages need
to be installed. Run commands from the repository root.

```sh
python3 scripts/build.py
python3 scripts/check.py
```

The build creates the JSON, CSS, VSIX, Obsidian ZIP, Ghostty files, Vim / Neovim
colorschemes and ZIP, the Zed theme JSON, preview, and review pages. It does not
install anything or change app settings. `VERSION` sets the VS Code extension and
Obsidian theme versions and names the release assets. Keep
`extensions/zed/extension.toml` at the same version when shipping a release.
The VS Code extension ID is `sugu.lucretia-theme`; the Zed extension ID is
`lucretia-theme`.

## Edit and output locations

| Location | Purpose |
| --- | --- |
| `scripts/palette.py` | Edit palette parameters and role assignments here. |
| `scripts/color.py` | Color conversion and numerical checks. |
| `scripts/export.py` | App mappings and public CSS variables. |
| `scripts/vim_theme.py`, `scripts/vim.README.md` | Shared Vim / Neovim mappings and installation text. |
| `scripts/zed_theme.py` | Zed theme mapping and generated theme family. |
| `extensions/zed/` | Zed extension root; manifest, README, and notice are source files. |
| `extensions/zed/themes/lucretia.json` | Generated Zed theme family. Do not edit by hand. |
| `scripts/package.py` | Fixed ZIP / VSIX packaging for these data-only themes. |
| `scripts/preview.html` | The preview's HTML template. |
| `docs/style.css`, `docs/preview.js` | The preview's layout and interactions. |
| `docs/fonts/` | Web fonts and their source attribution and licenses. |
| `scripts/review.py` | Detailed color review pages. |
| `dist/` | Generated, ready-to-use files. Commit them with their sources. |
| `docs/index.html` | Generated preview, with palette values embedded. |
| `review/` | Generated color review pages. Not part of the public preview site. |
| `tests/` | Color, format, packaging, and failure-path checks. |

Do not edit `dist/`, `review/`, `docs/index.html`, or
`extensions/zed/themes/lucretia.json` by hand. The build owns these generated
locations and removes unexpected files there, including old VSIX copies. The other
files under `extensions/zed/` are source files and are not overwritten.

Every output uses a freshly generated in-memory palette from `scripts/palette.py`.

The VSIX contains only package metadata, the three theme JSON files, a README,
and the third-party notice. The packager uses the VSIX ZIP/XML format.
ZIP timestamps and permissions are fixed for reproducible builds.

## Checks

```sh
python3 scripts/check.py
```

This runs the color self-test, the standard-library test suite, and the generated
file check. A failure returns a nonzero exit code. The checker does not update
or repair generated files.

```sh
python3 scripts/build.py --check
```

This narrower check reports missing, stale, or extra generated files. Tests also
inspect the archives' metadata, theme paths, colors, and included notices.
`tests/baseline.json` records hashes of the reference palette and VS Code themes
to detect unintended color changes. Update the baseline after reviewing an
intentional color change.

### Vim and Neovim checks

The core suite checks the generated schemes, links, palette mappings, ANSI colors,
and ZIP contents. When `vim` or `nvim` is on `PATH`, it also starts that editor
with no user config. Each editor tests all three appearances, all nine ordered
appearance transitions, explicit highlight colors, and actual Python syntax tokens
with syntax enabled both before and after theme loading. Missing editors are
reported as skipped tests; a successful core check is not proof that both editors
were run. Set `LUCRETIA_REQUIRE_EDITORS=1` to make a missing editor fail instead.
No editor is installed by the tests.

The [Check workflow](.github/workflows/check.yml) runs on pull requests and pushes
to `main`. It installs Vim and a pinned, checksum-verified Neovim release, runs
`scripts/check.py` with `LUCRETIA_REQUIRE_EDITORS=1`, then runs the browser check.

```sh
python3 -m unittest discover -s tests -p 'test_vim.py' -v
```

The installed themes are static Vimscript. Neovim-only groups are inside
`has('nvim')`; no Lua loader, plugin hooks, color calculations, or automatic
updates run in the editor. Terminal palettes apply to new terminal buffers.
The schemes use RGB colors only; they do not attempt a 256-color fallback.
Native visual checks are described in [demo/README.md](demo/README.md).

### Zed checks

```sh
python3 -m unittest discover -s tests -p 'test_zed.py' -v
```

These tests check the three appearances, syntax styles, shared UI and ANSI colors,
palette updates, JSON value types, and generated extension files. The release tests
also check the Zed ZIP and its checksum. They do not launch Zed or validate native
rendering. No network access or Zed installation is required for the core suite.

For a native check, follow [the Zed README](extensions/zed/README.md), switch through
Light, Dark, and Paper, and inspect code comments, Markdown emphasis, selections,
diagnostics, and an ANSI terminal sample. Check both the local-JSON installation
and the development extension separately; they use the same theme names.

### Browser checks

The optional browser test needs Playwright and a Chromium installation. These are
test tools, not dependencies of the site, build, or installed themes.

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tests/browser_check.py
```

An existing browser can be selected with `--chromium /path/to/chromium`.
Use `--screenshots /path/to/output` to save screenshots. The test loads the generated
HTML and its CSS / JavaScript directly into Chromium, without URL navigation or a
server. It checks appearance buttons, keyboard operation, narrow layouts, and
Obsidian CSS under controlled body classes. Clipboard success uses a stub; denial
and absence exercise actual text selection. It does not verify OS clipboard access,
local-file navigation, native apps, or Style Settings' command registration and
persistence. Follow `demo/README.md` for those app checks.

The contrast, CVD, reading, and gallery checks are in `review/`. Their
images live in `assets/`. To regenerate the optional chart images, install NumPy
and Matplotlib and run `python3 scripts/plot_check.py`. This is not part of the
normal build. See `assets/photos/README.md` for the review images.

## Releases

To ship a version, change the sources, increase `VERSION` (for example, `0.3.1`),
then build and check:

```sh
python3 scripts/build.py
python3 scripts/check.py
```

Review and commit the sources and generated files together. When that change
reaches `main`, the [Release workflow](.github/workflows/release.yml) checks the
files, creates the `vX.Y.Z` tag at the tested commit, and publishes a GitHub Release
with generated release notes and these assets:

- `lucretia-theme.vsix` for VS Code and Cursor.
- `lucretia-ghostty-X.Y.Z.zip` with all three themes and the third-party notice.
- `lucretia-obsidian-X.Y.Z.zip` with the `Lucretia/` theme folder, Minimal snippet,
  and third-party notices. Install the theme folder or the snippet, as described
  in the README.
- `lucretia-vim-X.Y.Z.zip` for Vim and Neovim.
- `lucretia-zed-X.Y.Z.zip` assembled from `extensions/zed/`, with the generated
  theme family, extension manifest, README, and third-party notice. This does not
  publish to the Zed extension store.
- `lucretia-palette-X.Y.Z.zip` with JSON, CSS, usage instructions, and the notice.
- `SHA256SUMS` with the SHA-256 digest of each asset.

Only a version increase on `main` publishes a release. Ordinary commits do not
create releases. Pull requests and manual **Run workflow** runs check the files
and prepare downloadable Actions artifacts, without publishing.
Stale generated files, invalid versions, and version
decreases fail the workflow. The workflow does not commit generated files for you.
It uses the repository's `GITHUB_TOKEN`; no personal token or extra secret is needed.
Write permission is limited to the publish job.

The release stays a draft until all assets have uploaded. If a run fails, use
**Actions > Release > the failed run > Re-run failed jobs**. A draft for the same
commit is resumed; an existing published release is left unchanged. A conflicting
tag or draft targeting a different commit stops publication. Keep the same version
when retrying that commit; use a new version for changes to a published release.

To inspect the release files locally without publishing, choose a new output
directory outside the generated locations:

```sh
python3 scripts/release.py --output /tmp/lucretia-release
```

Releases are not installed automatically. Users download and replace the files
from GitHub.

## Publish the preview

The `docs/` folder is a self-contained static site. Opening `docs/index.html`
locally does not require a server. There are no external scripts, fonts, or
runtime requests for the palette.

In the GitHub repository, open **Settings > Pages > Build and deployment** and
set **Source** to **GitHub Actions**. This is a one-time setting.

The workflow in `.github/workflows/pages.yml` runs on pushes to `main` and can
also be started from **Actions > Build and deploy Pages > Run workflow** on
`main`. It runs `python3 scripts/build.py`, then `python3 scripts/check.py`, and
publishes only `docs/` if both succeed. Runs on other branches do not deploy.

The site is regenerated on GitHub, so a local build is not required just to
publish preview changes. The workflow does not commit generated files back to
the repository or update the downloadable `dist/` files on the branch. Continue
to build and commit distribution changes with their sources as described above.

## Migration from 0.2.x

When updating a copy extracted from a ZIP, remove the root `palette.json`, `out/`,
`assets/previews/`, `plan.md`, `repo-review-plan.md`, `scripts/build_dist.py`, and
`scripts/install_editor_theme.sh`. Version 0.3.0 replaces these files and folders.
Building replaces the old contents of `dist/`.

Colors now live in `dist/palette/`. Generic CSS roles use `--lu-` names and
`data-lu-theme="light|dark|paper"`, not `--bg`, `--tx`, or `data-theme`.
Disable the 0.2.x `lucretia-paper.css` snippet before enabling the Lucretia theme
or `lucretia-minimal.css`.
The extension ID and appearance names have not changed.

## Zed registry publishing

The repository does not need a separate Zed-only repository. When registering the
extension in `zed-industries/extensions`, point the submodule at this repository
and set `path = "extensions/zed"`.

Lucretia is MIT-licensed. `extensions/zed/LICENSE` is a relative symbolic link to
the repository's `LICENSE`, because the registry reads the license from the
extension root. `THIRD_PARTY_NOTICES.md` covers Flexoki's license and attribution.

## References

- [Ghostty theme configuration](https://ghostty.org/docs/config/reference#theme)
- [VS Code extension packaging](https://code.visualstudio.com/api/working-with-extensions/publishing-extension)
- [Obsidian theme development](https://docs.obsidian.md/Themes/App+themes/Build+a+theme)
- [Zed theme extensions](https://zed.dev/docs/extensions/themes)
- [Vim colorscheme loading](https://vimhelp.org/syntax.txt.html#%3Acolorscheme)
- [Neovim Tree-sitter captures](https://neovim.io/doc/user/treesitter/#treesitter-highlight-groups)
- [Neovim LSP semantic highlights](https://neovim.io/doc/user/lsp/#lsp-semantic-highlight)
- [Neovim terminal colors](https://neovim.io/doc/user/terminal/#terminal-config)
- [Style Settings class toggles](https://github.com/community-archive/obsidian-style-settings#class-toggle)

Style Settings registers `addCommand` for a `class-toggle` and applies that
setting's ID as a body class. Lucretia uses a single false-by-default
`lucretia-light` setting in a `lucretia` section. The theme and Minimal overlay
share those IDs, so switching between the two installation methods does not
require two sets of color choices. Do not enable both methods at once.
