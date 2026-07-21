#define MyAppName "Posterfolio"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Charles Tait"
#define MyAppURL "https://github.com/cemtait/Posterfolio"
#define MyAppExeName "Posterfolio.exe"

[Setup]
AppId={{764E99A9-58B4-44F8-9EAC-504F53544552}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Posterfolio is installed only for the current Windows user.
; This avoids an unnecessary Administrator/UAC prompt.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\Posterfolio
DefaultGroupName=Posterfolio
DisableProgramGroupPage=yes

OutputDir=..\release
OutputBaseFilename=Posterfolio-1.0.0-Setup
SetupIconFile=..\src\poster_montage_designer\assets\icons\posterfolio.ico
UninstallDisplayIcon={app}\Posterfolio.exe

Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

CloseApplications=yes
RestartApplications=no
ChangesAssociations=no

VersionInfoVersion=1.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Posterfolio Setup
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\Posterfolio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Posterfolio"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Posterfolio"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Posterfolio"; Flags: nowait postinstall skipifsilent
