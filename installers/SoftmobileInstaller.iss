#define MyAppName "Softmobile 2025"
#define MyAppVersion "2.2.0"
#define MyAppPublisher "Softmobile"
#define BackendDir "dist\\softmobile_central"
#define FrontendDir "frontend\\dist"

[Setup]
AppId={{9F4B1162-8D9D-4F69-93B7-FA7D411FF1BE}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf64}\\Softmobile2025
DisableDirPage=no
DisableProgramGroupPage=no
OutputBaseFilename=Softmobile2025Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos"; Flags: unchecked

[Files]
Source: "{#BackendDir}\\*"; DestDir: "{app}\\backend"; Flags: recursesubdirs
Source: "{#FrontendDir}\\*"; DestDir: "{app}\\frontend"; Flags: recursesubdirs
Source: "config\\*"; DestDir: "{app}\\config"; Flags: recursesubdirs ignoreversion; Check: ConfigDirExists
Source: "backups\\*"; DestDir: "{app}\\backups"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\Panel central"; Filename: "{app}\\backend\\softmobile_central.exe"; WorkingDir: "{app}\\backend"
Name: "{group}\\Cliente de tienda"; Filename: "{cmd}"; Parameters: "/C start \"\" \"{app}\\frontend\\index.html\""; WorkingDir: "{app}\\frontend"; Tasks: desktopicon

[Run]
Filename: "{app}\\backend\\softmobile_central.exe"; Description: "Iniciar Softmobile Central"; Flags: postinstall nowait

[Code]
function ConfigDirExists(): Boolean;
begin
  Result := DirExists(ExpandConstant('config'));
end;
