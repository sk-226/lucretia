import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import re
import sys
from zipfile import ZipFile

import build
from package import zip_bytes


def version_parts(version):
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ValueError('VERSION must be a three-part version without leading zeros, such as 0.3.1')
    return tuple(map(int, version.split('.')))


def version_changed(version, previous):
    current = version_parts(version)
    if previous is None:
        return False
    old = version_parts(previous.strip())
    if current < old:
        raise ValueError(f'VERSION must not decrease from {previous.strip()} to {version}')
    return current > old


def release_assets(version, outputs):
    assets = {'lucretia-theme.vsix': outputs['dist/vscode/lucretia-theme.vsix'],
              f'lucretia-vim-{version}.zip': outputs['dist/vim/lucretia-vim.zip']}
    for kind in ('ghostty', 'palette', 'zed'):
        prefix = f'dist/{kind}/'
        files = {name.removeprefix(prefix): data for name, data in outputs.items()
                 if name.startswith(prefix)}
        assets[f'lucretia-{kind}-{version}.zip'] = zip_bytes(files)
    with ZipFile(BytesIO(outputs['dist/obsidian/Lucretia.zip'])) as archive:
        obsidian = {name: archive.read(name) for name in archive.namelist()}
    obsidian['lucretia-minimal.css'] = outputs['dist/obsidian/lucretia-minimal.css']
    obsidian[build.NOTICE] = outputs[f'dist/obsidian/{build.NOTICE}']
    assets[f'lucretia-obsidian-{version}.zip'] = zip_bytes(obsidian)
    assets['SHA256SUMS'] = ''.join(
        f'{hashlib.sha256(data).hexdigest()}  {name}\n'
        for name, data in sorted(assets.items())).encode('ascii')
    return assets


def prepare(output, previous=None):
    version = (build.ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    changed = version_changed(version, previous)
    outputs = build.render()
    errors = build.differences(build.ROOT, outputs)
    if errors:
        raise ValueError('\n'.join(errors) + '\nRun python3 scripts/build.py and commit the generated files.')
    assets = release_assets(version, outputs)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in assets.items():
        (output / name).write_bytes(data)
    return version, changed


def main():
    parser = argparse.ArgumentParser(description='Prepare checked release assets in a new directory. No publishing.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous-version')
    args = parser.parse_args()
    try:
        version, changed = prepare(args.output, args.previous_version)
    except (OSError, ValueError) as error:
        print(f'Release preparation failed: {error}', file=sys.stderr)
        return 1
    print(f'version={version}')
    print(f'tag=v{version}')
    print(f'changed={str(changed).lower()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
