$ErrorActionPreference = 'Stop'

$source = $PSScriptRoot
$packageName = 'icw-web-installer-test-package'
$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ($packageName + '-' + [guid]::NewGuid().ToString('N'))
$staging = Join-Path $stagingRoot $packageName
$archive = Join-Path (Split-Path $source -Parent) ($packageName + '.zip')
$checksum = $archive + '.sha256'

try {
    New-Item -ItemType Directory -Path $staging -Force | Out-Null

    Get-ChildItem -Path $source -Force | Where-Object {
        $_.Name -notin @('__pycache__', '.git')
    } | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $staging -Recurse -Force
    }

    Get-ChildItem -Path $staging -Recurse -Force | Where-Object {
        $_.PSIsContainer -and $_.Name -eq '__pycache__'
    } | Remove-Item -Recurse -Force
    Get-ChildItem -Path $staging -Recurse -File -Include '*.pyc', '*.pyo' | Remove-Item -Force

    Remove-Item -Path $archive, $checksum -Force -ErrorAction SilentlyContinue
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::Open(
        $archive,
        [System.IO.Compression.ZipArchiveMode]::Create
    )
    try {
        Get-ChildItem -Path $staging -Recurse -File | ForEach-Object {
            $relativePath = $_.FullName.Substring($stagingRoot.Length + 1).Replace('\', '/')
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $zip,
                $_.FullName,
                $relativePath,
                [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    }
    finally {
        $zip.Dispose()
    }

    $hash = (Get-FileHash -Path $archive -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -Path $checksum -Value ($hash + '  ' + (Split-Path $archive -Leaf)) -Encoding Ascii

    Write-Output $archive
    Write-Output $checksum
}
finally {
    Remove-Item -Path $stagingRoot -Recurse -Force -ErrorAction SilentlyContinue
}
