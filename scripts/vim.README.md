# Lucretia for Vim and Neovim

Light, Dark, and Paper. The same `.vim` files work in both editors.
Each file is self-contained. No plugin manager, Lua module, or Python is required.

Use Vim 9+ or Neovim 0.10+ with a true-color terminal, or a GUI with RGB support.
Enable `termguicolors` in your config. There is no 256-color approximation.

## Install

Copy the three files from `colors/` into your editor's colors directory.
Keep `THIRD_PARTY_NOTICES.md` with the downloaded files.

### Vim

On macOS and Linux, use `~/.vim/colors/`:

```sh
mkdir -p ~/.vim/colors
cp colors/lucretia-*.vim ~/.vim/colors/
```

Add to `~/.vimrc`:

```vim
syntax enable
set termguicolors
colorscheme lucretia-paper
```

### Neovim

On macOS and Linux, use `~/.config/nvim/colors/`:

```sh
mkdir -p ~/.config/nvim/colors
cp colors/lucretia-*.vim ~/.config/nvim/colors/
```

Add to your existing `init.lua`:

```lua
vim.opt.termguicolors = true
vim.cmd.colorscheme("lucretia-paper")
```

For `init.vim`, use the Vim settings above. Do not create both config files.
With `XDG_CONFIG_HOME` or `NVIM_APPNAME`, use the `colors` folder under the directory
shown by `:echo stdpath('config')` instead of the default path.

## Switch appearances

Run one of these commands in either editor:

```vim
:colorscheme lucretia-light
:colorscheme lucretia-dark
:colorscheme lucretia-paper
```

The chosen file sets `background` to light or dark. Use `:colorscheme` to switch;
changing `background` alone does not select another Lucretia appearance.
Edit the colorscheme line in your config to keep the choice after restarting.

## Coverage

The themes define editor UI, standard syntax groups, Markdown / basic TeX groups,
search, selection, completion, diffs, spelling, and terminal ANSI colors.
Neovim also gets Tree-sitter captures, LSP semantic highlights, diagnostics,
references, inlay hints, and floating-window colors.

Variables, parameters, and properties stay neutral. Definitions use blue,
keywords magenta, strings green, and numbers purple. Comments are italic.
Headings are bold rather than a different color for each level.
Tree-sitter function calls stay neutral when the query distinguishes them from
definitions; built-in functions use blue. Syntax grammars and language servers
decide which tokens are identified, so results can differ between editors.

The theme does not install parsers or language servers, enable their features,
or change your font, key mappings, layout, or diagnostic settings. Plugin-specific
UI colors are not included. Plugins using standard groups inherit these colors.

Terminal ANSI colors apply to newly opened `:terminal` buffers. After switching
appearances, reopen terminal buffers to use the new palette. No running terminal
jobs are restarted by the theme.

## Update

Replace the `.vim` files and run `:colorscheme lucretia-paper` again, or choose
another appearance. Existing editor settings are not replaced.

Generated from Lucretia's shared palette by `python3 scripts/build.py`.
Edit `scripts/vim_theme.py` for highlight mappings, not the generated files.
Inspired by Flexoki. See `THIRD_PARTY_NOTICES.md`.
