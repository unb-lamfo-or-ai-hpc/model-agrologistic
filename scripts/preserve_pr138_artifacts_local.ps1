# Preserve old PR138 PDF previews locally; optional narrowly scoped artifact cleanup.
[CmdletBinding()]
param(
    [string]$Base = 'C:\Users\cvict\OneDrive - unb.br\Posdoc\Temp Codex\model-agrologistic',
    [switch]$DeleteVerifiedArtifacts
)
$ErrorActionPreference = 'Stop'
$repo = 'unb-lamfo-or-ai-hpc/model-agrologistic'
$renderSource = '5966c08e3fca8ff84d67b88d4d8526ac0a1ae2dc'
$runId = 40791273903
$basePath = [IO.Path]::GetFullPath($Base)
$approved = @(
    [IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.codex')),
    [IO.Path]::GetFullPath('C:\Users\cvict\OneDrive - unb.br\Posdoc\Temp Codex\model-agrologistic')
)
$inside = $false
foreach ($allowed in $approved) {
    if ($basePath -eq $allowed -or
        $basePath.StartsWith($allowed + '\', [StringComparison]::OrdinalIgnoreCase)) {
        $inside = $true
    }
}
if (-not $inside -or -not (Test-Path -LiteralPath $basePath -PathType Container)) {
    throw 'Use an existing approved local temporary directory'
}
$destination = Join-Path $basePath 'pr138-preserved-previews-5966c08e'
if (-not (Test-Path -LiteralPath $destination)) {
    [void](New-Item -ItemType Directory -Path $destination)
}
$specs = @(
    @{ Id=12861268320; Name='index.pdf'; Local='article-pr138.pdf';
       Sha='d24e14c264ae6cc9b3cb79f1cff92b5d7ea8e35362dfae8f9e5f223c058b2716' },
    @{ Id=12861946512; Name='supplementary-review.pdf'; Local='appendices-pr138.pdf';
       Sha='43e8dd2d96d066f9c243ac6c5e058b9cad196f240f4efe48584d002d60de19b6' }
)
$oldInteractive = $env:GCM_INTERACTIVE
$oldPrompt = $env:GIT_TERMINAL_PROMPT
try {
    $env:GCM_INTERACTIVE = 'never'
    $env:GIT_TERMINAL_PROMPT = '0'
    $git = (Get-Command git -ErrorAction Stop).Source
    $request = [string]::Join([char]10, @('protocol=https', 'host=github.com', "path=$repo.git", '', ''))
    $credentials = @($request | & $git -c credential.interactive=false credential fill)
    if ($LASTEXITCODE -ne 0) { throw 'No usable saved GitHub credential; no login was opened' }
    $password = @($credentials | Where-Object { $_.StartsWith('password=') })
    if ($password.Count -ne 1) { throw 'Saved GitHub credential unavailable; stop' }
    $headers = @{
        Authorization = 'Bearer ' + $password[0].Substring(9)
        Accept = 'application/vnd.github+json'
        'X-GitHub-Api-Version' = '2022-11-28'
    }
    function Get-RepositoryApi([string]$Path) {
        Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/$Path" -Headers $headers
    }
    $copies = @()
    foreach ($spec in $specs) {
        $meta = Get-RepositoryApi "actions/artifacts/$($spec.Id)"
        if ($meta.name -ne $spec.Name -or $meta.workflow_run.head_sha -ne $renderSource -or
            $meta.workflow_run.id -ne $runId -or $meta.expired) {
            throw 'Original render artifact metadata differs'
        }
        $target = Join-Path $destination $spec.Local
        if (-not (Test-Path -LiteralPath $target)) {
            $partial = $target + '.part'
            if (Test-Path -LiteralPath $partial) { throw 'Preserve existing partial download' }
            Invoke-WebRequest -UseBasicParsing -Uri "https://api.github.com/repos/$repo/actions/artifacts/$($spec.Id)/zip" -Headers $headers -OutFile $partial
            if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant() -ne $spec.Sha) {
                throw 'Downloaded PDF bytes differ; no artifact was deleted'
            }
            Move-Item -LiteralPath $partial -Destination $target
        }
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $spec.Sha) {
            throw 'Local PDF differs; no artifact was deleted'
        }
        $copies += @{ path=$target; sha256=$spec.Sha; artifact_id=$spec.Id }
    }
    $commits = @(Get-RepositoryApi 'pulls/138/commits?per_page=100')
    $allowedCommits = @($commits | ForEach-Object { $_.sha })
    $artifacts = @()
    $allowedNames = @('index.pdf', 'supplementary-review.pdf', 'render-review.html', 'manuscript-draft')
    foreach ($sha in $allowedCommits) {
        $runs = (Get-RepositoryApi "actions/runs?head_sha=$sha&per_page=100").workflow_runs
        foreach ($run in $runs) {
            if ($run.name -ne 'Manuscript draft' -or $run.head_sha -ne $sha -or
                $run.head_branch -ne 'docs/literature-claims-reconciliation-20261028') { continue }
            $items = (Get-RepositoryApi "actions/runs/$($run.id)/artifacts?per_page=100").artifacts
            foreach ($item in $items) {
                if ($allowedNames -contains $item.name -and -not $item.expired) {
                    $artifacts += @{ id=$item.id; name=$item.name; source_sha=$sha; run_id=$run.id }
                }
            }
        }
    }
    $receipt = @{
        schema_version='pr138-local-artifact-preservation-v1'
        rendered_source=$renderSource
        note='Historical PR138 working previews; not final main/Pages PDFs'
        pdfs=$copies
        cleanup_candidates=$artifacts
    }
    $receiptPath = Join-Path $destination ('preservation-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.json')
    [IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))
    Write-Host "LOCAL_PRESERVATION=$receiptPath"
    Write-Host "PDF_DIRECTORY=$destination"
    Write-Host "CLEANUP_CANDIDATES=$($artifacts.Count)"
    if ($DeleteVerifiedArtifacts) {
        foreach ($item in $artifacts) {
            $meta = Get-RepositoryApi "actions/artifacts/$($item.id)"
            if ($meta.name -ne $item.name -or $meta.workflow_run.head_sha -ne $item.source_sha -or
                $meta.workflow_run.id -ne $item.run_id) { throw 'Cleanup target changed' }
            Invoke-RestMethod -Method Delete -Uri "https://api.github.com/repos/$repo/actions/artifacts/$($item.id)" -Headers $headers | Out-Null
            Write-Host "DELETED_PR138_DOCUMENT_ARTIFACT=$($item.id)"
        }
        Write-Host 'Only verified PR138 document artifacts were removed through GitHub API.'
        Write-Host 'Underlying provider retention/cache expiry cannot be independently attested.'
    } else {
        Write-Host 'PRESERVED_ONLY; no cloud artifact has been deleted.'
    }
} finally {
    $env:GCM_INTERACTIVE = $oldInteractive
    $env:GIT_TERMINAL_PROMPT = $oldPrompt
    $credentials = $null
    $password = $null
    $headers = $null
}
