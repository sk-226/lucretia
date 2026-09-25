import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build
import release


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.version = (ROOT / 'VERSION').read_text().strip()
        cls.outputs = build.render()
        cls.assets = release.release_assets(cls.version, cls.outputs)

    def test_version_changes_use_numeric_order_and_reject_rollbacks(self):
        for current, previous, expected in (
            ('0.3.1', '0.3.0', True), ('0.10.0', '0.9.9', True),
            ('1.0.0', '0.99.99', True), ('0.3.0', '0.3.0\n', False),
            ('0.3.0', None, False),
        ):
            with self.subTest(current=current, previous=previous):
                self.assertEqual(release.version_changed(current, previous), expected)
        with self.assertRaisesRegex(ValueError, 'must not decrease'):
            release.version_changed('0.3.0', '0.4.0')

    def test_invalid_versions_cannot_become_release_tags(self):
        for version in ('', 'v0.3.0', '0.3', '0.3.1-rc.1', '01.2.3', '１.2.3',
                        '0.3.1\nchanged=true', '0.3.1; echo unsafe'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                release.version_changed(version, '0.3.0')
        with self.assertRaises(ValueError):
            release.version_changed('0.3.1', 'invalid')

    def test_assets_cover_every_distribution_and_match_checksums(self):
        expected = {'lucretia-theme.vsix', 'SHA256SUMS',
                    *{f'lucretia-{kind}-{self.version}.zip'
                      for kind in ('ghostty', 'obsidian', 'palette', 'vim', 'zed')}}
        self.assertEqual(set(self.assets), expected)
        lines = self.assets['SHA256SUMS'].decode().splitlines()
        self.assertEqual(len(lines), len(expected) - 1)
        for line in lines:
            digest, name = line.split('  ')
            self.assertEqual(hashlib.sha256(self.assets[name]).hexdigest(), digest)
        self.assertEqual(self.assets['lucretia-theme.vsix'], self.outputs['dist/vscode/lucretia-theme.vsix'])
        self.assertEqual(self.assets[f'lucretia-vim-{self.version}.zip'], self.outputs['dist/vim/lucretia-vim.zip'])

    def test_zip_layouts_are_installable_and_include_notices(self):
        for kind in ('ghostty', 'palette'):
            prefix = f'dist/{kind}/'
            with self.subTest(kind=kind), ZipFile(BytesIO(self.assets[f'lucretia-{kind}-{self.version}.zip'])) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn(build.NOTICE, archive.namelist())
                self.assertEqual({prefix + name: archive.read(name) for name in archive.namelist()},
                                 {name: data for name, data in self.outputs.items() if name.startswith(prefix)})
        with ZipFile(BytesIO(self.assets[f'lucretia-zed-{self.version}.zip'])) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()),
                             {'extension.toml', 'README.md', 'LICENSE', build.NOTICE, 'themes/lucretia.json'})
            zed_root = ROOT / 'extensions/zed'
            for name in ('extension.toml', 'README.md', 'LICENSE', build.NOTICE):
                self.assertEqual(archive.read(name), (zed_root / name).read_bytes())
            self.assertEqual(archive.read('themes/lucretia.json'),
                             self.outputs['extensions/zed/themes/lucretia.json'])
        with ZipFile(BytesIO(self.assets[f'lucretia-obsidian-{self.version}.zip'])) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {'Lucretia/manifest.json', 'Lucretia/theme.css',
                f'Lucretia/{build.NOTICE}', 'lucretia-minimal.css', build.NOTICE})
            self.assertEqual(json.loads(archive.read('Lucretia/manifest.json'))['version'], self.version)
            self.assertEqual(archive.read('lucretia-minimal.css'), self.outputs['dist/obsidian/lucretia-minimal.css'])
            self.assertEqual(archive.read(build.NOTICE), (ROOT / build.NOTICE).read_bytes())

    def test_release_archives_are_reproducible(self):
        self.assertEqual(release.release_assets(self.version, self.outputs), self.assets)

    def test_preparation_refuses_stale_outputs_without_changing_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            for name in ('VERSION', build.NOTICE):
                shutil.copyfile(ROOT / name, root / name)
            shutil.copytree(ROOT / 'extensions', root / 'extensions')
            build.write_outputs(root, self.outputs)
            stale = root / 'dist/vscode/lucretia-theme.vsix'
            stale.write_bytes(b'stale package')
            destination = root / 'release-assets'
            with patch.object(build, 'ROOT', root), self.assertRaisesRegex(ValueError, 'Stale:'):
                release.prepare(destination)
            self.assertFalse(destination.exists())
            self.assertEqual(stale.read_bytes(), b'stale package')

    def test_cli_prepares_assets_but_refuses_to_overwrite_a_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'release-assets'
            command = [sys.executable, str(ROOT / 'scripts/release.py'), '--output', str(destination),
                       '--previous-version', self.version]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(dict(line.split('=', 1) for line in result.stdout.splitlines()),
                             {'version': self.version, 'tag': f'v{self.version}', 'changed': 'false'})
            self.assertEqual({path.name: path.read_bytes() for path in destination.iterdir()}, self.assets)
            sentinel = destination / 'keep.txt'
            sentinel.write_text('keep this')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), 'keep this')


if __name__ == '__main__':
    unittest.main(verbosity=2)
