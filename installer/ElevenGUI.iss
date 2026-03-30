#define MyAppName "Eleven GUI"
#define MyAppPublisher "BarryAllen53"
#define MyAppExeName "ElevenGUI.exe"
#define RootDir ExtractFilePath(SourcePath) + "..\"

#ifndef MyAppVersion
  #define MyAppVersion "1.0.1"
#endif

#ifndef ReleaseDir
  #error "ReleaseDir must be provided."
#endif

#define SourceDir AddBackslash(ReleaseDir) + "ElevenGUI-" + MyAppVersion + "-win64"

[Setup]
AppId={{1D18C183-7DA5-4D8A-B6E9-A83D6C6908B2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/BarryAllen53/eleven-gui
AppSupportURL=https://github.com/BarryAllen53/eleven-gui/issues
AppUpdatesURL=https://github.com/BarryAllen53/eleven-gui/releases/latest
DefaultDirName={localappdata}\Programs\Eleven GUI
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
OutputDir={#ReleaseDir}
OutputBaseFilename=ElevenGUI-{#MyAppVersion}-setup
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile={#RootDir}LICENSE
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Dirs]
Name: "{userappdata}\ElevenGUI"
Name: "{localappdata}\ElevenGUI"
Name: "{localappdata}\ElevenGUI\outputs"
Name: "{localappdata}\ElevenGUI\.cache"

[Files]
Source: "{#SourceDir}\ElevenGUI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\.env.example"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "{#SourceDir}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autoprograms}\{#MyAppName}\Open User Data Folder"; Filename: "{localappdata}\ElevenGUI"
Name: "{autoprograms}\{#MyAppName}\Project Website"; Filename: "https://github.com/BarryAllen53/eleven-gui"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Eleven GUI"; Flags: nowait postinstall skipifsilent
