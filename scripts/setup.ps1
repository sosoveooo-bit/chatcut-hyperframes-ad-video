param(
    [string]$MaterialRoot = "$HOME\ChatCutMaterials",
    [string]$ConfigDirectory = "$HOME\.codex\chatcut-hyperframes",
    [int]$Port = 8794,
    [int]$HyperFramesTimeoutSeconds = 300,
    [switch]$StartPanel,
    [switch]$SkipHyperFrames,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$SkillRoot = Split-Path -Parent $PSScriptRoot
$Doctor = Join-Path $PSScriptRoot "doctor.py"
$PanelServer = Join-Path $SkillRoot "panel\server.py"
$ExpandedConfigDirectory = [Environment]::ExpandEnvironmentVariables($ConfigDirectory)
if ([System.IO.Path]::IsPathRooted($ExpandedConfigDirectory)) {
    $ConfigDir = [System.IO.Path]::GetFullPath($ExpandedConfigDirectory)
} else {
    $ConfigDir = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $ExpandedConfigDirectory))
}
$ConfigFile = Join-Path $ConfigDir "config.json"
$ExpandedMaterialRoot = [Environment]::ExpandEnvironmentVariables($MaterialRoot)
if ([System.IO.Path]::IsPathRooted($ExpandedMaterialRoot)) {
    $ResolvedMaterialRoot = [System.IO.Path]::GetFullPath($ExpandedMaterialRoot)
} else {
    $ResolvedMaterialRoot = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $ExpandedMaterialRoot))
}

function Get-RequiredCommand([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Required command is missing: $Name"
    }
    return $command
}

function Invoke-WithTimeout([string]$FilePath, [string[]]$Arguments, [int]$TimeoutSeconds) {
    Write-Output "Running: $FilePath $($Arguments -join ' ')"
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    } else {
        $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -PassThru
    }
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        $process.Kill()
        throw "Command timed out after $TimeoutSeconds seconds: $FilePath $($Arguments -join ' ')"
    }
    if ($process.ExitCode -ne 0) {
        throw "Command failed with exit code $($process.ExitCode): $FilePath $($Arguments -join ' ')"
    }
}

$Python = Get-RequiredCommand "python"

if ($CheckOnly) {
    & $Python.Source $Doctor --material-root $ResolvedMaterialRoot --panel-url "http://127.0.0.1:$Port"
    exit $LASTEXITCODE
}

New-Item -ItemType Directory -Force -Path $ResolvedMaterialRoot | Out-Null
& $Python.Source -B $PanelServer --material-root $ResolvedMaterialRoot --init-only

if (-not $SkipHyperFrames) {
    $Npx = Get-RequiredCommand "npx"
    Invoke-WithTimeout $Npx.Source @("--yes", "hyperframes@latest", "skills", "update", "general-video") $HyperFramesTimeoutSeconds
}

New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
$config = [ordered]@{
    version = 1
    materialRoot = $ResolvedMaterialRoot
    panelUrl = "http://127.0.0.1:$Port"
    skillRoot = $SkillRoot
}
$config | ConvertTo-Json | Set-Content -LiteralPath $ConfigFile -Encoding UTF8

if ($StartPanel) {
    $arguments = @(
        "-B",
        "`"$PanelServer`"",
        "--host", "127.0.0.1",
        "--port", "$Port",
        "--material-root", "`"$ResolvedMaterialRoot`""
    )
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        Start-Process -FilePath $Python.Source -ArgumentList $arguments -WindowStyle Hidden
    } else {
        Start-Process -FilePath $Python.Source -ArgumentList $arguments
    }

    $healthy = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/healthz" -TimeoutSec 2
            if ($health.ok) { $healthy = $true; break }
        } catch {
        }
    }
    if (-not $healthy) { throw "Material panel did not become healthy on port $Port" }
    Write-Output "Material panel: http://127.0.0.1:$Port/materials.html"
}

Write-Output "Portable material root: $ResolvedMaterialRoot"
Write-Output "Local config: $ConfigFile"
& $Python.Source $Doctor --material-root $ResolvedMaterialRoot --panel-url "http://127.0.0.1:$Port"
$DoctorExitCode = $LASTEXITCODE
if ($StartPanel -and $DoctorExitCode -ne 0) {
    throw "Bundle doctor failed after starting the panel"
}
exit 0
