; Inno Setup script — builds Bodega-Setup.exe (per-user install, no admin needed)
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

[Setup]
AppId={{67FB9967-2AB3-4596-92C3-0BC407D0B799}
AppName=Bodega
AppVersion={#MyAppVersion}
AppPublisher=Bodega
DefaultDirName={localappdata}\Programs\Bodega
DefaultGroupName=Bodega
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=Bodega-Setup
SetupIconFile=..\..\build\icon.ico
UninstallDisplayIcon={app}\Bodega.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\..\dist\Bodega\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Bodega"; Filename: "{app}\Bodega.exe"
Name: "{userdesktop}\Bodega"; Filename: "{app}\Bodega.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Bodega.exe"; Description: "Open Bodega now"; Flags: nowait postinstall skipifsilent
