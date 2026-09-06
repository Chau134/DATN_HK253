[CmdletBinding()]
param(
    [ValidateRange(30, 900)]
    [int]$ReadyTimeoutSeconds = 240,

    [ValidatePattern('^[a-z]{2}(-gov)?-[a-z]+-\d$')]
    [string]$BedrockRegion = 'ap-northeast-1',

    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$serviceDirectory = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $serviceDirectory 'docker-compose.yml'
$previousToken = [Environment]::GetEnvironmentVariable(
    'AWS_BEARER_TOKEN_BEDROCK',
    [EnvironmentVariableTarget]::Process
)
$previousRegion = [Environment]::GetEnvironmentVariable(
    'BEDROCK_REGION',
    [EnvironmentVariableTarget]::Process
)
$secureKey = $null
$pointer = [IntPtr]::Zero

try {
    $secureKey = Read-Host 'Enter Bedrock API key' -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer).Trim()

    if ([string]::IsNullOrWhiteSpace($token)) {
        throw 'Bedrock API key must not be empty.'
    }

    [Environment]::SetEnvironmentVariable(
        'AWS_BEARER_TOKEN_BEDROCK',
        $token,
        [EnvironmentVariableTarget]::Process
    )
    [Environment]::SetEnvironmentVariable(
        'BEDROCK_REGION',
        $BedrockRegion,
        [EnvironmentVariableTarget]::Process
    )
    $token = $null

    Write-Host "Starting service-ai with Bedrock Region: $BedrockRegion"

    $composeArguments = @(
        'compose',
        '--project-directory', $serviceDirectory,
        '-f', $composeFile,
        'up', '-d', '--force-recreate'
    )
    $composeArguments += if ($SkipBuild) { '--no-build' } else { '--build' }
    $composeArguments += 'service-ai'
    & docker @composeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Could not start service-ai (docker compose exit code $LASTEXITCODE)."
    }

    $containerId = (& docker compose --project-directory $serviceDirectory -f $composeFile `
        ps -q service-ai).Trim()
    if ([string]::IsNullOrWhiteSpace($containerId)) {
        throw 'Could not resolve the service-ai container ID.'
    }

    $deadline = [DateTime]::UtcNow.AddSeconds($ReadyTimeoutSeconds)
    do {
        $healthStatus = (& docker inspect `
            --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' `
            $containerId).Trim()
        if ($LASTEXITCODE -ne 0) {
            throw 'Could not inspect the service-ai container health.'
        }
        if ($healthStatus -eq 'healthy') {
            Write-Host 'service-ai container is ready.' -ForegroundColor Green
            & docker compose --project-directory $serviceDirectory -f $composeFile `
                exec -T service-ai python -c `
                "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health/ready').read().decode())"
            exit 0
        }

        Start-Sleep -Seconds 3
    } while ([DateTime]::UtcNow -lt $deadline)

    Write-Host `
        "service-ai was not ready after $ReadyTimeoutSeconds seconds. Recent logs:" `
        -ForegroundColor Red
    & docker compose --project-directory $serviceDirectory -f $composeFile `
        logs --tail 120 service-ai
    exit 1
}
finally {
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }

    [Environment]::SetEnvironmentVariable(
        'AWS_BEARER_TOKEN_BEDROCK',
        $previousToken,
        [EnvironmentVariableTarget]::Process
    )
    [Environment]::SetEnvironmentVariable(
        'BEDROCK_REGION',
        $previousRegion,
        [EnvironmentVariableTarget]::Process
    )
}
