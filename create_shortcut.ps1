param(
    [string]$ShortcutPath,
    [string]$TargetPath,
    [string]$WorkingDirectory,
    [string]$IconPath
)

try {
    Write-Host "Creating desktop shortcut for Financial Command Center AI..."

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)

    # Use cmd.exe as target to run the batch file with better icon support
    $shortcut.TargetPath = "cmd.exe"
    $shortcut.Arguments = "/c `"$TargetPath`""
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.WindowStyle = 1

    # Try custom icon first, fallback to professional system icon
    if (Test-Path $IconPath) {
        Write-Host "Setting custom icon..."
        $shortcut.IconLocation = "$IconPath,0"
        $shortcut.Save()

        # Verify if icon was set correctly
        Start-Sleep -Milliseconds 500
        $testShortcut = $shell.CreateShortcut($ShortcutPath)
        if ($testShortcut.IconLocation -match [regex]::Escape($IconPath)) {
            Write-Host "Custom icon set successfully!"
        } else {
            Write-Host "Custom icon failed, using professional system icon..."
            $shortcut.IconLocation = "C:\Windows\System32\imageres.dll,109"
            $shortcut.Save()
        }
    } else {
        Write-Host "Custom icon not found, using professional system icon..."
        $shortcut.IconLocation = "C:\Windows\System32\imageres.dll,109"
        $shortcut.Save()
    }

    # Force refresh icon cache
    try {
        $signature = @'
[DllImport("shell32.dll")]
public static extern void SHChangeNotify(uint wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@
        if (-not ([System.Management.Automation.PSTypeName]'Win32.Shell32').Type) {
            Add-Type -MemberDefinition $signature -Namespace Win32 -Name Shell32
        }
        [Win32.Shell32]::SHChangeNotify(0x08000000, 0x0000, [System.IntPtr]::Zero, [System.IntPtr]::Zero)
    } catch {
        # Silent fallback if cache refresh fails
    }

    Write-Host "Shortcut created successfully at: $ShortcutPath"

} catch {
    Write-Host "Error creating shortcut: $($_.Exception.Message)"
    exit 1
}