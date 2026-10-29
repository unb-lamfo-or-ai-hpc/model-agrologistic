# Local document verification only. No clone, install, solver, HPC or cloud upload.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{40}$')][string]$SourceSha,
    [string]$Base = 'C:\Users\cvict\OneDrive - unb.br\Posdoc\Temp Codex\model-agrologistic',
    [switch]$Render
)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($Base)
$allowed = @(
    [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.codex')),
    [IO.Path]::GetFullPath('C:\Users\cvict\OneDrive - unb.br\Posdoc\Temp Codex\model-agrologistic')
)
if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw 'Existing base required' }
$inside = $false
foreach ($item in $allowed) {
    if ($root -eq $item -or $root.StartsWith($item + '\', [StringComparison]::OrdinalIgnoreCase)) {
        $inside = $true
    }
}
if (-not $inside) { throw 'Use one of the approved local temporary locations' }
$python = (Get-Command python -ErrorAction Stop).Source
$quarto = if ($Render) { (Get-Command quarto -ErrorAction Stop).Source } else { $null }
$work = Join-Path $root ('journal-reader-review-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
[void](New-Item -ItemType Directory -Path $work)
$zipPath = Join-Path $work 'source.zip'
Invoke-WebRequest -Uri "https://codeload.github.com/unb-lamfo-or-ai-hpc/model-agrologistic/zip/$SourceSha" -OutFile $zipPath
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($zipPath)
$unpacked = Join-Path $work 'source'
[void](New-Item -ItemType Directory -Path $unpacked)
$prefix = [IO.Path]::GetFullPath($unpacked) + '\'
try {
    foreach ($entry in $zip.Entries) {
        $name = $entry.FullName
        if ($name.Contains('\') -or $name.StartsWith('/') -or $name.Contains(':') -or
            ($name.Split('/') -contains '..')) { throw 'Unsafe source ZIP member' }
        $kind = ($entry.ExternalAttributes -shr 16) -band 0xF000
        if ($kind -eq 0xA000) { throw 'Linked source ZIP member' }
        $target = [IO.Path]::GetFullPath((Join-Path $unpacked $name))
        if (-not $target.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Source ZIP target escaped the temporary workspace'
        }
        if ($name.EndsWith('/')) {
            [void][IO.Directory]::CreateDirectory($target)
        } else {
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $false)
        }
    }
} finally { $zip.Dispose() }
$folders = @(Get-ChildItem -LiteralPath $unpacked -Directory)
if ($folders.Count -ne 1) { throw 'One GitHub snapshot root required' }
$source = $folders[0].FullName
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Program ($LASTEXITCODE)" }
}
$log = Join-Path $work 'local-document-checks.txt'
Start-Transcript -LiteralPath $log | Out-Null
Push-Location -LiteralPath $source
try {
    Write-Host "SOURCE_COMMIT=$SourceSha"
    Invoke-Checked $python @('-B', '-m', 'ruff', 'check',
        'scripts/check_manuscript.py', 'scripts/check_manuscript_appendix_inputs.py',
        'scripts/build_scalar_manuscript.py', 'scripts/build_wd_manuscript.py',
        'scripts/inspect_parallel_solver_evidence.py', 'tests/test_manuscript.py')
    Invoke-Checked $python @('-B', '-m', 'scripts.build_scalar_manuscript', '--check')
    Invoke-Checked $python @('-B', '-m', 'scripts.build_wd_manuscript', '--check')
    Invoke-Checked $python @('-B', 'scripts/check_manuscript.py')
    Invoke-Checked $python @('-B', 'scripts/check_manuscript_appendix_inputs.py',
        '--output', (Join-Path $work 'appendix-reader-audit.json'))
    Invoke-Checked $python @('-B', '-m', 'pytest', 'tests/test_manuscript.py',
        'tests/test_manuscript_package.py', '-q', '-p', 'no:cacheprovider',
        '--basetemp', (Join-Path $work 'test-temp'))
    if ($Render) {
        Invoke-Checked $quarto @('render', 'manuscript')
        Invoke-Checked $quarto @('render', 'manuscript/supplement')
        Invoke-Checked $python @('-B', 'scripts/assemble_manuscript_outputs.py')
        Invoke-Checked $python @('-B', 'scripts/check_manuscript.py', '--rendered')
        Write-Host ('ARTICLE_PDF=' + (Join-Path $source 'manuscript\_manuscript\index.pdf'))
        Write-Host ('APPENDIX_PDF=' + (Join-Path $source 'manuscript\_manuscript\supplementary-review.pdf'))
    }
    Write-Host 'LOCAL_DOCUMENT_CHECKS=PASSED'
    Write-Host "TEMP_WORKSPACE=$work"
    Write-Host "LOCAL_LOG=$log"
} finally {
    Pop-Location
    Stop-Transcript | Out-Null
}
