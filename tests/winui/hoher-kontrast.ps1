# Schaltet den Modus Hoher Kontrast der angemeldeten Sitzung ein oder aus und wartet,
# bis Windows ihn meldet. Aufruf: pwsh -File hoher-kontrast.ps1 -An $true
param([Parameter(Mandatory)][bool]$An)
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class Kontrast
{
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct HIGHCONTRAST { public int cbSize; public int dwFlags; public IntPtr lpszDefaultScheme; }

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool SystemParametersInfo(int uiAction, int uiParam, ref HIGHCONTRAST pvParam, int fWinIni);

    public static bool Setzen(bool an)
    {
        var hc = new HIGHCONTRAST { cbSize = Marshal.SizeOf<HIGHCONTRAST>(), dwFlags = an ? 1 : 0 };
        // SPI_SETHIGHCONTRAST, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
        return SystemParametersInfo(0x0043, hc.cbSize, ref hc, 3);
    }

    public static bool Ist()
    {
        var hc = new HIGHCONTRAST { cbSize = Marshal.SizeOf<HIGHCONTRAST>() };
        SystemParametersInfo(0x0042, hc.cbSize, ref hc, 0);  // SPI_GETHIGHCONTRAST
        return (hc.dwFlags & 1) == 1;
    }
}
'@
if (-not [Kontrast]::Setzen($An)) { throw "SystemParametersInfo meldet einen Fehler: $([Runtime.InteropServices.Marshal]::GetLastWin32Error())" }
for ($i = 0; $i -lt 30; $i++) {
    if ([Kontrast]::Ist() -eq $An) { Start-Sleep -Seconds 3; Write-Host "Hoher Kontrast: $An"; exit 0 }
    Start-Sleep -Seconds 1
}
throw "Hoher Kontrast blieb nach 30 s nicht $An"
