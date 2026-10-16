"""The locks: every package the builds install, each at one version, with the fingerprints (hashes) of its files.

    python scripts/lock.py              after changing requirements*.txt: writes the two lock files again
    python scripts/lock.py --check      (CI) the locks still match requirements*.txt; says what to run if not
    python scripts/lock.py --everything (CI) every package in requirements.lock, on every computer it's built for

requirements.lock is what the four builds install (Mac, Windows and Linux in one file: a package only one of them
needs says so after its version); requirements-lint.lock, the tools CI checks the code with. They're installed with
`--require-hashes --only-binary :all:`: a file whose fingerprint doesn't match is refused, and nothing runs a setup
script on the way in (the standard's 12.9). Versions stay as they are unless requirements*.txt asks for another.
Needs uv (https://docs.astral.sh/uv/), the version in requirements-lint.txt.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = "3.12"  # .python-version's
LOCKS = {  # lock -> (what it's made from, the computers it's for)
    "requirements.lock": ("requirements-dev.txt", ["--universal"]),
    "requirements-lint.lock": ("requirements-lint.txt", ["--python-platform", "linux"]),
}


def compile_lock(source: str, where: list[str], out: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        sys.exit("scripts/lock.py needs uv: pip install uv (the version in requirements-lint.txt)")
    subprocess.run(  # (uv, with this script's own arguments)
        [
            uv, "pip", "compile", "--quiet", "--generate-hashes", "--only-binary", ":all:",
            "--python-version", PYTHON, *where, "--custom-compile-command", "python scripts/lock.py",
            "-o", str(out), source,
        ],
        cwd=ROOT, check=True,
    )  # fmt: skip


def check() -> int:
    """Made again from requirements*.txt, keeping the versions they have (uv prefers what's in the lock), each lock
    is the same as the one in the repository."""
    stale = []
    with tempfile.TemporaryDirectory() as tmp:
        for lock, (source, where) in LOCKS.items():
            again = Path(tmp) / lock
            shutil.copyfile(ROOT / lock, again)
            compile_lock(source, where, again)
            if again.read_text(encoding="utf-8") != (ROOT / lock).read_text(encoding="utf-8"):
                stale.append(lock)
    if stale:
        print(f"{', '.join(stale)} no longer match requirements*.txt. Run: python scripts/lock.py, and commit them.")
        return 1
    print("The locks match requirements*.txt.")
    return 0


def everything() -> str:
    """name==version for every package in requirements.lock, whichever computer it's for (for pip-audit)."""
    found = re.findall(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s;\\]+)", (ROOT / "requirements.lock").read_text(), re.M)
    return "".join(f"{name}=={version}\n" for name, version in sorted(set(found)))


def main() -> int:
    if "--check" in sys.argv:
        return check()
    if "--everything" in sys.argv:
        sys.stdout.write(everything())
        return 0
    for lock, (source, where) in LOCKS.items():
        compile_lock(source, where, ROOT / lock)
        print(f"Wrote {lock}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
