param(
    [string]$ServerUrl = 'http://127.0.0.1:18878',
    [string]$CaseFile = (Join-Path $PSScriptRoot '..\docs\natural-radio-d1-gold-results.json'),
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
$record = Get-Content -LiteralPath $CaseFile -Raw | ConvertFrom-Json
$instruction = [string]$record.system_instruction
$forbidden = @($record.acceptance.forbidden_terms)
$maximumWords = [int]$record.acceptance.maximum_words

$results = foreach ($case in $record.cases) {
    $required = @($case.required_terms)
    $user = "Fact: $($case.fact)`nREQUIRED LITERALS: $($required -join ' | ')"
    $body = @{
        model = 'race-engineer-qwen3-0.6b-q4_k_m.gguf'
        temperature = 0
        max_tokens = 80
        messages = @(
            @{ role = 'system'; content = $instruction },
            @{ role = 'user'; content = $user }
        )
    } | ConvertTo-Json -Depth 6

    $response = Invoke-RestMethod -Method Post -Uri "$($ServerUrl.TrimEnd('/'))/v1/chat/completions" -ContentType 'application/json' -Body $body
    $text = ([string]$response.choices[0].message.content).Trim()
    $missing = @($required | Where-Object { $text -notmatch [regex]::Escape([string]$_) })
    $presentForbidden = @($forbidden | Where-Object { $text -match ('(?i)(?<![A-Za-z])' + [regex]::Escape([string]$_) + '(?![A-Za-z])') })
    $words = @($text -split '\s+' | Where-Object { $_ }).Count
    $finish = [string]$response.choices[0].finish_reason
    $passed = $finish -eq 'stop' -and $words -le $maximumWords -and $missing.Count -eq 0 -and $presentForbidden.Count -eq 0 -and $text -eq [string]$case.expected_response

    [PSCustomObject]@{
        id = $case.id
        fact = $case.fact
        required_terms = $required
        expected_response = $case.expected_response
        response = $text
        finish_reason = $finish
        words = $words
        missing_terms = $missing
        forbidden_terms = $presentForbidden
        total_ms = [math]::Round($response.timings.prompt_ms + $response.timings.predicted_ms, 2)
        passed = $passed
    }
}

$output = [PSCustomObject]@{
    schema = 1
    evaluation = $record.evaluation
    inputs = $record.inputs
    environment = $record.environment
    acceptance = $record.acceptance
    cases = $results
    passed = @($results | Where-Object { -not $_.passed }).Count -eq 0
}
$json = $output | ConvertTo-Json -Depth 8
if ($OutputPath) {
    Set-Content -LiteralPath $OutputPath -Value $json -Encoding utf8NoBOM
}
$json
if (-not $output.passed) {
    exit 1
}
