param(
    [string]$CaseFile = (Join-Path $PSScriptRoot '..\docs\natural-radio-d1-gold-cases.json'),
    [string]$ResultFile = (Join-Path $PSScriptRoot '..\docs\natural-radio-d1-gold-results.json')
)

$ErrorActionPreference = 'Stop'
$cases = Get-Content -LiteralPath $CaseFile -Raw | ConvertFrom-Json
$result = Get-Content -LiteralPath $ResultFile -Raw | ConvertFrom-Json
$expectedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $CaseFile).Hash.ToLowerInvariant()
if ($result.case_file_sha256 -ne $expectedHash) { throw 'The result does not identify the retained case file.' }
if (($result.system_instruction -ne $cases.system_instruction) -or (($result.acceptance | ConvertTo-Json -Compress) -ne ($cases.acceptance | ConvertTo-Json -Compress))) { throw 'The result does not retain the evaluated contract.' }
if ($result.cases.Count -ne $cases.cases.Count) { throw 'The result case count differs from the retained case file.' }

$forbidden = @($cases.acceptance.forbidden_terms)
$maximumWords = [int]$cases.acceptance.maximum_words
$derived = foreach ($case in $result.cases) {
    $spec = @($cases.cases | Where-Object { $_.id -eq $case.id })
    if ($spec.Count -ne 1 -or $case.fact -ne $spec[0].fact -or $case.expected_response -ne $spec[0].expected_response) { throw "Result case $($case.id) does not match the retained case file." }
    $text = ([string]$case.response).Trim()
    $missing = @($spec[0].required_terms | Where-Object { $text -notmatch [regex]::Escape([string]$_) })
    $presentForbidden = @($forbidden | Where-Object { $text -match ('(?i)(?<![A-Za-z])' + [regex]::Escape([string]$_) + '(?![A-Za-z])') })
    $words = @($text -split '\s+' | Where-Object { $_ }).Count
    $passed = $case.finish_reason -eq 'stop' -and $words -le $maximumWords -and $missing.Count -eq 0 -and $presentForbidden.Count -eq 0 -and $text -eq $spec[0].expected_response
    if (($case.words -ne $words) -or (($case.missing_terms -join '|') -ne ($missing -join '|')) -or (($case.forbidden_terms -join '|') -ne ($presentForbidden -join '|')) -or ($case.passed -ne $passed)) { throw "Result case $($case.id) does not match derived acceptance." }
    $passed
}
$overall = @($derived | Where-Object { -not $_ }).Count -eq 0
if ($result.passed -ne $overall) { throw 'The result summary does not match the derived cases.' }
[PSCustomObject]@{ cases = $result.cases.Count; passed = $overall; consistency = 'passed' } | ConvertTo-Json
