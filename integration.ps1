<#
.SYNOPSIS
    Integrates Notepad-- into Windows Context Menus and File Associations.
.DESCRIPTION
    v4 Fix: Adds "Open With" registration for Windows 11 Modern Menu support.
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
$AppExeName = "notepad--.exe" # Used for Applications registration
$ContextMenuName = "Edit with Notepad--" # Renamed to "Edit with" to distinguish from "Open with" submenu
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
        # --- A. Create the ProgID ---
        Write-Host "Creating ProgID: $ProgID..."
        if (-not (Test-Path "HKCR:\$ProgID")) { New-Item -Path "HKCR:\$ProgID" -Force | Out-Null }
        New-ItemProperty -Path "HKCR:\$ProgID" -Name "(default)" -Value "Notepad-- Document" -PropertyType String -Force | Out-Null
        
        # Set Icon
        if (-not (Test-Path "HKCR:\$ProgID\DefaultIcon")) { New-Item -Path "HKCR:\$ProgID\DefaultIcon" -Force | Out-Null }
        New-ItemProperty -Path "HKCR:\$ProgID\DefaultIcon" -Name "(default)" -Value $iconPath -PropertyType String -Force | Out-Null
        
        # Set Open Command for ProgID
        if (-not (Test-Path "HKCR:\$ProgID\shell\open\command")) { New-Item -Path "HKCR:\$ProgID\shell\open\command" -Force | Out-Null }
        New-ItemProperty -Path "HKCR:\$ProgID\shell\open\command" -Name "(default)" -Value $command -PropertyType String -Force | Out-Null

        # --- B. Register in HKCR\Applications (CRITICAL FOR WINDOWS 11 OPEN WITH) ---
        Write-Host "Registering App Capabilities..."
        $appKey = "HKCR:\Applications\$AppExeName"
        if (-not (Test-Path $appKey)) { New-Item -Path $appKey -Force | Out-Null }
        
        # Define commands for the App Key
        if (-not (Test-Path "$appKey\shell\open\command")) { New-Item -Path "$appKey\shell\open\command" -Force | Out-Null }
        New-ItemProperty -Path "$appKey\shell\open\command" -Name "(default)" -Value $command -PropertyType String -Force | Out-Null
        # Add Friendly Name
        New-ItemProperty -Path "$appKey\shell\open" -Name "FriendlyAppName" -Value $AppName -PropertyType String -Force | Out-Null

        # --- C. Add to "Classic" Context Menu (Background Right Click) ---
        Write-Host "Adding 'Classic' Context Menu item..."
        $regKeyBase = "HKCR\*\shell\$ContextMenuName"
        Start-Process cmd.exe -ArgumentList "/c reg add `"$regKeyBase`" /ve /d `"$ContextMenuName`" /f" -Wait -WindowStyle Hidden
        Start-Process cmd.exe -ArgumentList "/c reg add `"$regKeyBase`" /v Icon /d `"$iconPath`" /f" -Wait -WindowStyle Hidden
        Start-Process cmd.exe -ArgumentList "/c reg add `"$regKeyBase\command`" /ve /d `"$escapedCommand`" /f" -Wait -WindowStyle Hidden

        # --- D. Associate Extensions & OpenWithProgids ---
        Write-Host "Associating extensions and populating 'Open With'..."
        foreach ($ext in $TargetExtensions) {
            # 1. Create Extension Key if missing
            if (-not (Test-Path "HKCR:\$ext")) { New-Item "HKCR:\$ext" -Force | Out-Null }
            
            # 2. Set Default Association (Optional: User can change this in Settings, but this hints it)
            New-ItemProperty -Path "HKCR:\$ext" -Name "(default)" -Value $ProgID -PropertyType String -Force | Out-Null
            
            # 3. Add to OpenWithProgids (This puts it in the modern "Open With" list)
            if (-not (Test-Path "HKCR:\$ext\OpenWithProgids")) { New-Item "HKCR:\$ext\OpenWithProgids" -Force | Out-Null }
            New-ItemProperty -Path "HKCR:\$ext\OpenWithProgids" -Name $ProgID -Value "" -PropertyType String -Force | Out-Null

            Write-Host "  Processed $ext" -ForegroundColor Gray
        }

        Write-Host "`nSUCCESS!" -ForegroundColor Green
        Write-Host "1. Right-click a file -> 'Show more options' -> '$ContextMenuName'"
        Write-Host "2. Right-click a file -> 'Open With' -> Notepad-- should now appear there."
    }
    catch {
        Write-Error "An error occurred: $_"
    }
}

function Uninstall-Integration {
    Write-Host "`n--- REMOVING INTEGRATION ---" -ForegroundColor Magenta
    
    try {
        # --- A. Remove Classic Context Menu ---
        Write-Host "Removing Context Menu item..."
        $regKeyBase = "HKCR\*\shell\$ContextMenuName"
        Start-Process cmd.exe -ArgumentList "/c reg delete `"$regKeyBase`" /f" -Wait -WindowStyle Hidden

        # --- B. Remove ProgID ---
        if (Test-Path "HKCR:\$ProgID") {
            Write-Host "Removing ProgID configuration..."
            Remove-Item "HKCR:\$ProgID" -Recurse -Force
        }

        # --- C. Remove Applications Registration ---
        if (Test-Path "HKCR:\Applications\$AppExeName") {
            Write-Host "Removing Application registration..."
            Remove-Item "HKCR:\Applications\$AppExeName" -Recurse -Force
        }

        # --- D. Unlink extensions & Clean OpenWith ---
        Write-Host "Unlinking file extensions..."
        foreach ($ext in $TargetExtensions) {
            # Clear default if it matches us
            $current = (Get-ItemProperty -Path "HKCR:\$ext" -Name "(default)" -ErrorAction SilentlyContinue)."(default)"
            if ($current -eq $ProgID) {
                Remove-ItemProperty -Path "HKCR:\$ext" -Name "(default)" -ErrorAction SilentlyContinue
            }

            # Clear OpenWithProgids entry
            if (Test-Path "HKCR:\$ext\OpenWithProgids") {
                 Remove-ItemProperty -Path "HKCR:\$ext\OpenWithProgids" -Name $ProgID -ErrorAction SilentlyContinue
            }
            Write-Host "  Cleared $ext" -ForegroundColor Gray
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