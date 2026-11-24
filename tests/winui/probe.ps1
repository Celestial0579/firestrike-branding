# Baut die Probe, startet sie im hellen, dunklen und hohen Kontrast und vergleicht die Werte.
# Aufruf aus der Wurzel des Repos: pwsh -File tests/winui/probe.ps1
$ErrorActionPreference = 'Stop'
$wurzel = (Resolve-Path "$PSScriptRoot/../..").Path
$aus = Join-Path $wurzel 'tests/winui/ergebnis'
New-Item -ItemType Directory -Force -Path $aus | Out-Null
dotnet publish "$wurzel/tests/winui/Probe/Probe.csproj" -c Release -o "$aus/app" -warnaserror
if ($LASTEXITCODE -ne 0) { throw "Bauen gescheitert" }
$xaml = Join-Path $wurzel 'exporte/winui/Firestrike.xaml'

function Starte([string]$thema, [string]$name) {
    $json = Join-Path $aus "$name.json"
    Remove-Item -Force -ErrorAction SilentlyContinue $json, "$json.fehler"
    $p = Start-Process -FilePath "$aus/app/FsProbe.exe" -ArgumentList '--thema', $thema, '--xaml', "`"$xaml`"", '--aus', "`"$json`"" -PassThru
    if (-not $p.WaitForExit(120000)) { $p.Kill(); throw "${name}: Probe hängt" }
    if (Test-Path "$json.fehler") { Get-Content "$json.fehler"; throw "${name}: Probe meldet einen Fehler" }
    if ($p.ExitCode -ne 0 -or -not (Test-Path $json)) { throw "${name}: Exit-Code $($p.ExitCode), kein Ergebnis" }
    Write-Host "${name}: geladen"
}

Starte 'Light' 'hell'
Starte 'Dark' 'dunkel'
& "$PSScriptRoot/hoher-kontrast.ps1" -An $true
try { Starte 'System' 'kontrast' } finally { & "$PSScriptRoot/hoher-kontrast.ps1" -An $false }

exit 0
