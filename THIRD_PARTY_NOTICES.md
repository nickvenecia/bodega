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
| Inter typeface (the app and the paper) | SIL Open Font License 1.1 | https://github.com/rsms/inter |
| IBM Plex Mono (serial numbers; unmodified) | SIL Open Font License 1.1 | https://github.com/IBM/plex |
| Icons (redrawn line icons) | ISC (Lucide) | https://lucide.dev |

The fonts' license files are in `bodega/assets/fonts` (OFL-*.txt). Inter's fixed weights are the same cut
Cobro ships; IBM Plex Mono is included exactly as published.
Qt libraries are shipped as separate shared libraries in the app folder and can be replaced.
