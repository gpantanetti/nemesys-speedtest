; Script generated by the Inno Setup Script Wizard.
; SEE THE DOCUMENTATION FOR DETAILS ON CREATING INNO SETUP SCRIPT FILES!

#define MyAppName "MisuraInternet Speed Test"
#define MyAppVersion "@version@"
#define MyAppPublisher "Fondazione Ugo Bordoni"
#define MyAppURL "http://www.misurainternet.it/"
#define MyAppExeName "MisuraInternetSpeedTest"
#define MyRoot "."
#define MyAppDir MyRoot + ""

; Read the previuos build number. If there is none take 0 instead.
#define BuildNum Int(ReadIni(SourcePath + "\\buildinfo.ini","Info","Build","0"))
; Increment the build number by one.
#expr BuildNum = BuildNum + 1
; Store the number in the ini file for the next build
#expr WriteIni(SourcePath + "\\buildinfo.ini","Info","Build", BuildNum)

[Setup]
;AppId={21F1511D-B744-4DCE-AEAA-55E5C0668A35}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppExeName}
DefaultGroupName={#MyAppName}
AllowNoIcons=true
InfoBeforeFile={#MyAppDir}\EULA
LicenseFile={#MyAppDir}\LICENSE
OutputDir={#MyAppDir}
OutputBaseFilename={#MyAppExeName}_v.{#myAppVersion}-{#BuildNum}
SolidCompression=true
VersionInfoCopyright=(c) 2010-2016 Fondazione Ugo Bordoni
PrivilegesRequired=admin
SetupIconFile={#MyAppDir}\mist.ico
WizardSmallImageFile={#MyAppDir}\mist_55.bmp
WizardImageFile={#MyAppDir}\mist_164.bmp
AppCopyright=Fondazione Ugo Bordoni

[Messages]
italian.AdminPrivilegesRequired=Errore nell'installazione.%nSono necessarie le credenziali di amministratore per poter procedere.

[Languages]
Name: italian; MessagesFile: compiler:Languages\Italian.isl

[Tasks]
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1; Languages: italian

[Files]
Source: {#MyAppDir}\mist\dist\*; DestDir: {app}\dist; Flags: ignoreversion recursesubdirs createallsubdirs
Source: {#MyAppDir}\ABOUT; DestDir: {app}; Flags: ignoreversion
Source: {#MyAppDir}\mist.ico; DestDir: {app}; Flags: ignoreversion
Source: {#MyAppDir}\COPYING; DestDir: {app}; Flags: ignoreversion
Source: {#MyAppDir}\LICENSE; DestDir: {app}; Flags: ignoreversion
Source: {#MyAppDir}\icons\*.png; DestDir: {app}\icons; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Dirs]
;Name: {app}\outbox
;Name: {app}\sent
;Name: {app}\logs

[Icons]
Name: {group}\{#MyAppName}; Filename: {app}\dist\mist.exe
Name: {group}\{cm:UninstallProgram,{#MyAppName}}; Filename: {uninstallexe}
Name: {commondesktop}\{#MyAppName}; Filename: {app}\dist\mist.exe; IconIndex: 0
Name: {userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}; Filename: {app}\dist\mist.exe; Tasks: quicklaunchicon; IconIndex: 0

[Run]
Filename: {sys}\netsh.exe; Parameters: " int ip set global taskoffload=disabled"; Description: "Disable TCP Task Offload"; Flags: RunHidden RunAsCurrentUser; 
Filename: {sys}\netsh.exe; Parameters: " firewall add allowedprogram ""{app}\dist\mist.exe"" ""MisuraInternetSpeedTest"" ENABLE CUSTOM 193.104.137.0/24 ALL"; Description: "Enable MisuraInternet Speed Test traffic"; Flags: RunHidden RunAsCurrentUser; 
Filename: {sys}\netsh.exe; Parameters: " advfirewall firewall add rule name=""MisuraInternetSpeedTest"" dir=out action=allow program=""{app}\dist\mist.exe"" enable=yes"; Description: "Enable MisuraInternet Speed Test traffic"; Flags: RunHidden RunAsCurrentUser; MinVersion: 0,6.1.7600; 
Filename: {app}\dist\mist.exe; Parameters: start; Description: "Avvia MisuraInternet Speed Test"; Flags: PostInstall runmaximized RunAsCurrentUser; StatusMsg: "Avvia MisuraInternet Speed Test";
;Filename: {app}\dist\Nemesys.exe; Parameters: "--startup auto install"; Description: "Installazione del servizio Nemesys."; StatusMsg: "Installazione del servizio Nemesys"; Flags: RunHidden RunAsCurrentUser; 
;Filename: {app}\dist\Nemesys.exe; Parameters: start; Description: "Avvia il servizio Nemesys"; Flags: PostInstall RunHidden RunAsCurrentUser; StatusMsg: "Avvia il servizio Nemesys";

 
[UninstallRun]
Filename: taskkill; Parameters: /f /im mist.exe; WorkingDir: {sys}; Flags: runminimized RunAsCurrentUser
Filename: {sys}\netsh.exe; Parameters: " firewall delete allowedprogram program=""{app}\dist\mist.exe"""; Flags: RunHidden RunAsCurrentUser; 
;Filename: {app}\dist\Nemesys.exe; Parameters: " --wait 25 stop"; Flags: runminimized RunAsCurrentUser
;Filename: {app}\dist\NemesysSpeedtest.exe; Parameters: " remove"; Flags: runminimized RunAsCurrentUser

[UninstallDelete]
;Type: files; Name: {app}\dist\cfg\*
;Type: files; Name: {app}\dist\*
;Type: files; Name: {app}\config\*
;Type: files; Name: {app}\docs\*
;Type: files; Name: {app}\icons\*
;Type: files; Name: {app}\logs\*
;Type: files; Name: {app}\outbox\*
;Type: files; Name: {app}\sent\*
;Type: dirifempty; Name: {app}\dist\cfg
Type: filesandordirs; Name: {app}\dist
Type: filesandordirs; Name: {app}\config
Type: filesandordirs; Name: {app}\docs
Type: filesandordirs; Name: {app}\icons
Type: filesandordirs; Name: {app}\logs
Type: filesandordirs; Name: {app}\outbox
Type: filesandordirs; Name: {app}\sent
Type: filesandordirs; Name: {app}

[Registry]
;root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\Nemesys; valuetype: expandsz; valuename: ImagePath; valuedata: {app}; Flags: UninsDeleteKey DeleteKey
;root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\Nemesys; valuetype: multisz; valuename: DependOnService; valuedata: EventSystem{break}Tcpip{break}Netman{break}EventLog{break}; Flags: UninsDeleteKey DeleteKey
;root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\Nemesys; valuetype: binary; valuename: FailureActions; Flags: UninsDeleteKey DeleteKey; ValueData: 00 00 00 00 00 00 00 00 00 00 00 00 03 00 00 00 53 00 65 00 01 00 00 00 60 ea 00 00 01 00 00 00 60 ea 00 00 01 00 00 00 60 ea 00 00 
root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\EventSystem; valuetype: dword; valuename: Start; valuedata: 2
root: HKLM; subkey: SYSTEM\CurrentControlSet\Services\Tcpip\Parameters; valuetype: dword; valuename: DisableTaskOffload; valuedata: 1; 

[Code]
procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  Cancel := true;
  Confirm := false;
end;

var
  WarningPage: TOutputMsgWizardPage;

procedure InitializeWizard;
begin

  WarningPage := CreateOutputMsgPage(wpInfoBefore,
    'Attenzione', 'Prima di continuare l''installazione....',
    '....� consigliato controllare che sia tutto in ordine per ottenere un risultato il pi� possibile attendibile. In particolare:'#13#13
    '1. Hai connesso il PC al modem via cavo?'#13#13 +
    '2. Hai chiuso tutte le applicazioni che accedono ad Internet? Ad esempio:'#13 +
    '   * programmi per l''accesso alla posta elettronica'#13 +
    '   * altri programmi come: Skype, MSN Messenger, Dropbox, etc....'#13#13 +
    '3. Hai spento tutti i dispositivi che accedono ad Internet? Ad esempio:'#13 +
    '   * Console        * Smart-TV        * Smartphone        * IPTV        * VoIP'#13#13 +
    'L�interfaccia grafica di MisuraInternet Speed Test ti aiuter� nel controllo delle impostazioni del PC e della rete domestica per minimizzare le interferenze con le misure.'#13#13
    'Controlla di aver verificato che tutte le condizioni siano rispettate,'#13 +
    'poi procedi pure con l''installazione.');

end;

