"""Run core checks without rebuilding generated files."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    commands = [
        [sys.executable, str(ROOT / 'scripts/color.py')],
        [sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT / 'tests'), '-p', 'test_*.py', '-v'],
        [sys.executable, str(ROOT / 'scripts/build.py'), '--check'],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
