; Creado por Codex el 2025-10-20
[Setup]
AppName=Softmobile 2025 v2.2.0
AppVersion=2.2.0
DefaultDirName={autopf64}\\Softmobile2025
OutputBaseFilename=Softmobile2025-Setup
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "..\\backend\\*"; DestDir: "{app}\\backend"; Flags: recursesubdirs createallsubdirs
Source: "..\\frontend\\dist\\*"; DestDir: "{app}\\frontend\\dist"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "start_softmobile.bat"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "{app}\\start_softmobile.bat"; Description: "Iniciar Softmobile"; Flags: postinstall nowait
