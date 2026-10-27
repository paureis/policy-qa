# Starts the Recourse API for local development with the variables from .env
# (names in .env.example; values never in the repo). Run from anywhere:
#   & .\scripts\dev-api.ps1
# Loads each NAME=value line of .env into this process only, then runs uvicorn
# from the repo's venv with reload on port 8000.

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path .env)) {
    Write-Error ".env not found in $root. Copy .env.example to .env and fill in the values."
    exit 1
}

foreach ($line in Get-Content .env) {
    $t = $line.Trim()
    if ($t -eq '' -or $t.StartsWith('#')) { continue }
    $i = $t.IndexOf('=')
    if ($i -lt 1) { continue }
    $name = $t.Substring(0, $i).Trim()
    $value = $t.Substring($i + 1).Trim()
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}

$names = @('POLICYQA_LLM_MODEL', 'POLICYQA_LLM_REASONING_EFFORT', 'RECOURSE_PDF_DIR')
foreach ($n in $names) {
    $v = [Environment]::GetEnvironmentVariable($n, 'Process')
    Write-Host ("{0} = {1}" -f $n, $v)
}
if (-not [Environment]::GetEnvironmentVariable('POLICYQA_LLM_API_KEY', 'Process')) {
    Write-Warning "POLICYQA_LLM_API_KEY is empty: the API will run in fixture mode."
}

# Reload only on api/ and policyqa/ changes. The case store is in memory, so a reload drops every
# open case; watching the whole repo meant an edit under cases/ or web/ wiped live cases.
& .\.venv\Scripts\uvicorn.exe api.main:app --reload --reload-dir api --reload-dir policyqa --port 8000
