# Third-party software in Bodega

The packaged app includes these open-source components. Thank you to their authors.

| Component | License | Source |
|---|---|---|
| Qt 6 / PySide6 | LGPL-3.0 | https://www.qt.io/download-open-source · https://code.qt.io/cgit/pyside/pyside-setup.git |
| Python | PSF License | https://www.python.org |
| certifi | MPL-2.0 | https://github.com/certifi/python-certifi |
| openpyxl (reading .xlsx) | MIT | https://foss.heptapod.net/openpyxl/openpyxl |
| defusedxml | PSF License | https://github.com/tiran/defusedxml |
| keyring (the system keychain) | MIT | https://github.com/jaraco/keyring |
| segno (QR codes on labels) | BSD-3-Clause | https://github.com/heuer/segno |
| shiboken6 (part of PySide6) | LGPL-3.0 | https://code.qt.io/cgit/pyside/pyside-setup.git |
| et_xmlfile (used by openpyxl) | MIT | https://foss.heptapod.net/openpyxl/et_xmlfile |
| jaraco.classes, jaraco.context, jaraco.functools (used by keyring) | MIT | https://github.com/jaraco |
| more-itertools (used by keyring) | MIT | https://github.com/more-itertools/more-itertools |
| pywin32-ctypes (keyring on Windows) | BSD-3-Clause | https://github.com/enthought/pywin32-ctypes |
| SecretStorage (keyring on Linux) | BSD-3-Clause | https://github.com/mitya57/secretstorage |
| jeepney (keyring on Linux) | MIT | https://gitlab.com/takluyver/jeepney |
| cryptography (SecretStorage on Linux) | Apache-2.0 or BSD-3-Clause | https://github.com/pyca/cryptography |
| cffi, pycparser (used by cryptography) | MIT; BSD-3-Clause | https://github.com/python-cffi/cffi · https://github.com/eliben/pycparser |
| PyInstaller bootloader (starts the packaged app) | GPL-2.0 with the bootloader exception | https://github.com/pyinstaller/pyinstaller |
| Inter typeface (the app and the paper) | SIL Open Font License 1.1 | https://github.com/rsms/inter |
| IBM Plex Mono (serial numbers; unmodified) | SIL Open Font License 1.1 | https://github.com/IBM/plex |
| Icons (redrawn line icons) | ISC (Lucide) | https://lucide.dev |

The fonts' license files are in `bodega/assets/fonts` (OFL-*.txt). Inter's fixed weights are included as
published; IBM Plex Mono is included exactly as published.
Qt libraries are shipped as separate shared libraries in the app folder and can be replaced.
