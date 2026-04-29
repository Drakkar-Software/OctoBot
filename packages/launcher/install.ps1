#Requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$Service,
    [string]$Version
)

$ErrorActionPreference = 'Stop'

$REPO         = "Drakkar-Software/OctoBot"
$BINARY       = "octobot-launcher"
$DEFAULT_INSTALL_DIR = Join-Path $env:LOCALAPPDATA "Programs\OctoBot-Launcher"

function Main {
    $installDir = if ($env:OCTOBOT_LAUNCHER_INSTALL_DIR) {
        $env:OCTOBOT_LAUNCHER_INSTALL_DIR
    } else {
        $DEFAULT_INSTALL_DIR
    }

    # Detect architecture
    $arch = (Get-CimInstance Win32_ComputerSystem).SystemType
    $triple = switch -Wildcard ($arch) {
        "*x64*"  { "x86_64-pc-windows-msvc" }
        "*ARM64*" {
            Write-Error "No prebuilt binary for ARM64 Windows yet."
            exit 1
        }
        default {
            Write-Error "Unsupported architecture: $arch"
            exit 1
        }
    }

    # Resolve version
    $resolvedVersion = if ($Version) {
        $Version
    } elseif ($env:OCTOBOT_LAUNCHER_VERSION) {
        $env:OCTOBOT_LAUNCHER_VERSION
    } else {
        Write-Host "Fetching latest launcher release..."
        $releases = Invoke-RestMethod "https://api.github.com/repos/$REPO/releases"
        $tag = ($releases | Where-Object { $_.tag_name -like "launcher-v*" } | Select-Object -First 1).tag_name
        if (-not $tag) {
            Write-Error "Could not determine latest launcher release."
            exit 1
        }
        $tag -replace '^launcher-v', ''
    }

    $archive    = "${BINARY}-${resolvedVersion}-${triple}.zip"
    $baseUrl    = "https://github.com/${REPO}/releases/download/launcher-v${resolvedVersion}"
    $tmpDir     = [System.IO.Path]::GetTempPath() + [System.IO.Path]::GetRandomFileName()
    New-Item -ItemType Directory -Path $tmpDir | Out-Null

    try {
        Write-Host "Installing octobot-launcher v${resolvedVersion} (${triple})..."

        $archivePath = Join-Path $tmpDir $archive
        $sha256Path  = "$archivePath.sha256"

        # Download
        Invoke-WebRequest "${baseUrl}/${archive}"        -OutFile $archivePath
        Invoke-WebRequest "${baseUrl}/${archive}.sha256" -OutFile $sha256Path

        # Verify checksum
        $expected = (Get-Content $sha256Path).Split(' ')[0].ToLower()
        $actual   = (Get-FileHash $archivePath -Algorithm SHA256).Hash.ToLower()
        if ($actual -ne $expected) {
            Write-Error "Checksum mismatch!`n  expected: $expected`n  actual:   $actual"
            exit 1
        }

        # Extract
        Expand-Archive -Path $archivePath -DestinationPath $tmpDir -Force

        # Install
        if (-not (Test-Path $installDir)) {
            New-Item -ItemType Directory -Path $installDir | Out-Null
        }
        $dest = Join-Path $installDir "${BINARY}.exe"
        Move-Item -Force (Join-Path $tmpDir "${BINARY}.exe") $dest

        Write-Host ""
        Write-Host "Installed: $dest"
        Write-Host ""

        # Add to PATH if not already there
        $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
        if ($userPath -notlike "*$installDir*") {
            [Environment]::SetEnvironmentVariable('PATH', "$userPath;$installDir", 'User')
            Write-Host "Added $installDir to your user PATH."
            Write-Host "Restart your terminal for the change to take effect."
            Write-Host ""
        }

        # Service install
        if ($Service) {
            & $dest service install --user
            Write-Host "Service installed. Start it with:"
            Write-Host "  octobot-launcher service start"
        } else {
            Write-Host "Next steps:"
            Write-Host "  octobot-launcher service install --user"
            Write-Host "  octobot-launcher service start"
        }

    } finally {
        Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
    }
}

Main
