<#
.SYNOPSIS
    Integrates Notepad-- into Windows Context Menus and File Associations.
.DESCRIPTION
    v3 Fix: Uses 'reg.exe' for the Context Menu to avoid PowerShell 5.1 wildcard expansion hangs.
#>

# -----------------------------------------------------------------------------
# 1. ADMIN CHECK
# -----------------------------------------------------------------------------
$currentPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList ("-file `"{0}`"" -f $MyInvocation.MyCommand.Definition)
    Exit
}

# -----------------------------------------------------------------------------
# 2. MOUNT HKCR (Just in case)
# -----------------------------------------------------------------------------
if (-not (Get-PSDrive -Name HKCR -ErrorAction SilentlyContinue)) {
    New-PSDrive -Name HKCR -PSProvider Registry -Root HKEY_CLASSES_ROOT | Out-Null
}

# -----------------------------------------------------------------------------
# 3. CONFIGURATION
# -----------------------------------------------------------------------------
$ProgID = "NotepadMinusMinus.File"
$AppName = "Notepad--"
$ContextMenuName = "Open with Notepad--"
# List of extensions to associate
$TargetExtensions = @(
    ".txt", ".log", ".md", ".json", ".xml", ".yaml", ".yml", 
    ".py", ".js", ".html", ".css", ".ini", ".cfg", ".bat", ".ps1", ".sh"
)

Add-Type -AssemblyName System.Windows.Forms

# -----------------------------------------------------------------------------
# 4. HELPER FUNCTIONS
# -----------------------------------------------------------------------------

function Get-BinaryPath {
    $openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
    $openFileDialog.Title = "Select the Notepad-- Binary (executable)"
    $openFileDialog.Filter = "Executables (*.exe)|*.exe|All Files (*.*)|*.*"
    $openFileDialog.InitialDirectory = [System.Environment]::GetFolderPath('Desktop')
    
    if ($openFileDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        return $openFileDialog.FileName
    }
    return $null
}

function Install-Integration {
    Write-Host "`n--- INSTALLING INTEGRATION ---" -ForegroundColor Cyan
    
    $exePath = Get-BinaryPath
    if (-not $exePath) {
        Write-Warning "No file selected. Aborting."
        return
    }
    
    $iconPath = "$exePath,0" 
    $command = "`"$exePath`" `"%1`""
    $escapedCommand = $command.Replace('"', '\"') # Escape quotes for reg.exe

    try {
        # --- A. Create the ProgID (PowerShell is fine here) ---
        Write-Host "Creating ProgID: $ProgID..."
        if (-not (Test-Path "HKCR:\$ProgID")) { New-Item -Path "HKCR:\$ProgID" -Force | Out-Null }
        New-ItemProperty -Path "HKCR:\$ProgID" -Name "(default)" -Value "Notepad-- Document" -PropertyType String -Force | Out-Null
        
        # Set Icon
        if (-not (Test-Path "HKCR:\$ProgID\DefaultIcon")) { New-Item -Path "HKCR:\$ProgID\DefaultIcon" -Force | Out-Null }
        New-ItemProperty -Path "HKCR:\$ProgID\DefaultIcon" -Name "(default)" -Value $iconPath -PropertyType String -Force | Out-Null
        
        # Set Open Command
        if (-not (Test-Path "HKCR:\$ProgID\shell\open\command")) { New-Item -Path "HKCR:\$ProgID\shell\open\command" -Force | Out-Null }
        New-ItemProperty -Path "HKCR:\$ProgID\shell\open\command" -Name "(default)" -Value $command -PropertyType String -Force | Out-Null

        # --- B. Add to Context Menu (Using reg.exe to avoid wildcard hang) ---
        Write-Host "Adding Context Menu item..."
        
        # 1. Create the key "Open with Notepad--" under *
        $regKeyBase = "HKCR\*\shell\$ContextMenuName"
        Start-Process cmd.exe -ArgumentList "/c reg add `"$regKeyBase`" /ve /d `"$ContextMenuName`" /f" -Wait -WindowStyle Hidden
        Start-Process cmd.exe -ArgumentList "/c reg add `"$regKeyBase`" /v Icon /d `"$iconPath`" /f" -Wait -WindowStyle Hidden

        # 2. Create the command key
        Start-Process cmd.exe -ArgumentList "/c reg add `"$regKeyBase\command`" /ve /d `"$escapedCommand`" /f" -Wait -WindowStyle Hidden

        # --- C. Associate Extensions ---
        Write-Host "Associating extensions..."
        foreach ($ext in $TargetExtensions) {
            if (-not (Test-Path "HKCR:\$ext")) { New-Item "HKCR:\$ext" -Force | Out-Null }
            New-ItemProperty -Path "HKCR:\$ext" -Name "(default)" -Value $ProgID -PropertyType String -Force | Out-Null
            Write-Host "  Assigning $ext" -ForegroundColor Gray
        }

        Write-Host "`nSUCCESS!" -ForegroundColor Green
        Write-Host "Notepad-- has been added to the context menu."
        Write-Host "File associations set." -ForegroundColor Yellow
    }
    catch {
        Write-Error "An error occurred: $_"
    }
}

function Uninstall-Integration {
    Write-Host "`n--- REMOVING INTEGRATION ---" -ForegroundColor Magenta
    
    try {
        # --- A. Remove Context Menu (Using reg.exe) ---
        Write-Host "Removing Context Menu item..."
        $regKeyBase = "HKCR\*\shell\$ContextMenuName"
        # We use reg delete because removing a key named '*' in PS is also tricky
        Start-Process cmd.exe -ArgumentList "/c reg delete `"$regKeyBase`" /f" -Wait -WindowStyle Hidden

        # --- B. Remove ProgID ---
        if (Test-Path "HKCR:\$ProgID") {
            Write-Host "Removing ProgID configuration..."
            Remove-Item "HKCR:\$ProgID" -Recurse -Force
        }

        # --- C. Unlink extensions ---
        Write-Host "Unlinking file extensions..."
        foreach ($ext in $TargetExtensions) {
            $current = (Get-ItemProperty -Path "HKCR:\$ext" -Name "(default)" -ErrorAction SilentlyContinue)."(default)"
            if ($current -eq $ProgID) {
                Remove-ItemProperty -Path "HKCR:\$ext" -Name "(default)" -ErrorAction SilentlyContinue
                Write-Host "  Cleared $ext" -ForegroundColor Gray
            }
        }

        Write-Host "`nUNINSTALL COMPLETE." -ForegroundColor Green
    }
    catch {
        Write-Error "An error occurred during uninstall: $_"
    }
}

# -----------------------------------------------------------------------------
# 5. MAIN MENU
# -----------------------------------------------------------------------------
Clear-Host
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "      Notepad-- Integration Tool" -ForegroundColor Cyan
Write-Host "========================================="
Write-Host "1. Install / Update Integration"
Write-Host "2. Remove Integration (Uninstall)"
Write-Host "3. Exit"
Write-Host "========================================="

$choice = Read-Host "Select an option [1-3]"

switch ($choice) {
    '1' { Install-Integration }
    '2' { Uninstall-Integration }
    '3' { Write-Host "Exiting..."; Exit }
    Default { Write-Host "Invalid selection."; Exit }
}

Write-Host "`nPress any key to close..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")