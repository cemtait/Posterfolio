#define MyAppName "Posterfolio"
#define MyAppVersion "1.0.0"
#define MyAppExeName "Posterfolio.exe"

[Setup]
AppId={{764E99A9-58B4-44F8-9EAC-POSTERFOLIO10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Posterfolio
DefaultGroupName=Posterfolio
OutputBaseFilename=Posterfolio-1.0.0-Setup
SetupIconFile=..\src\poster_montage_designer\assets\icons\posterfolio.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\dist\Posterfolio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Posterfolio"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Posterfolio"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Registry]
Root: HKCR; Subkey: ".pmd"; ValueType: string; ValueData: "Posterfolio.Project"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "Posterfolio.Project"; ValueType: string; ValueData: "Posterfolio Project"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Posterfolio.Project\DefaultIcon"; ValueType: string; ValueData: "{app}\posterfolio_project.ico"
Root: HKCR; Subkey: "Posterfolio.Project\shell\open\command"; ValueType: string; ValueData: "\"{app}\{#MyAppExeName}\" \"%1\""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Posterfolio"; Flags: nowait postinstall skipifsilent
