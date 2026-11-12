# Builds dist\quick_inset_map-<version>.zip for plugins.qgis.org / "Install from ZIP".
# The zip holds one top-level folder, quick_inset_map, without caches or hidden files.
# Usage:  powershell -ExecutionPolicy Bypass -File .\build.ps1

$ErrorActionPreference = 'Stop'

$pluginName = 'quick_inset_map'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$src = Join-Path $root $pluginName
$dist = Join-Path $root 'dist'

foreach ($required in 'metadata.txt', '__init__.py', 'LICENSE') {
    if (-not (Test-Path (Join-Path $src $required))) {
        throw "Missing required file: $pluginName\$required"
    }
}

$metadata = Get-Content (Join-Path $src 'metadata.txt')
$versionLine = $metadata | Where-Object { $_ -match '^\s*version\s*=' } | Select-Object -First 1
if (-not $versionLine) { throw 'No version= line in metadata.txt' }
$version = ($versionLine -split '=', 2)[1].Trim()

if ($metadata -match 'YOUR[ _]|example\.com') {
    Write-Warning 'metadata.txt still contains placeholder values (author, email or URLs).'
}

# Everything under the plugin folder except caches, compiled files and hidden files.
$srcFull = (Resolve-Path $src).Path.TrimEnd('\')
$files = Get-ChildItem -Path $srcFull -Recurse -File -Force | Where-Object {
    $relative = $_.FullName.Substring($srcFull.Length + 1)
    $parts = $relative -split '\\'
    -not ($_.Attributes -band [IO.FileAttributes]::Hidden) -and
    -not ($parts | Where-Object { $_.StartsWith('.') -or $_ -eq '__pycache__' -or $_ -eq '__MACOSX' }) -and
    $_.Extension -notin '.pyc', '.pyo', '.zip'
} | Sort-Object FullName

New-Item -ItemType Directory -Force -Path $dist | Out-Null
$zipPath = Join-Path $dist "$pluginName-$version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

# Written entry by entry so that paths inside the zip use forward slashes.
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::Open($zipPath, [IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($srcFull.Length + 1) -replace '\\', '/'
        $entryName = "$pluginName/$relative"
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip, $file.FullName, $entryName, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
        Write-Host "  $entryName"
    }
}
finally {
    $zip.Dispose()
}

$size = (Get-Item $zipPath).Length
Write-Host "Built $zipPath ($size bytes, $($files.Count) files)"
