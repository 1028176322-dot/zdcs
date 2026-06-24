param(
    [Parameter(Mandatory = $true, Position = 0, HelpMessage = "pageId, displayName, or alias, such as character_info")]
    [string]$Page,
    [string]$Python = "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe",
    [switch]$StrictDrafts,
    [switch]$DryRun,
    [string]$Note,
    [string]$Date
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $scriptDir "check_and_record_completed_mapping_page.py"

if (-not (Test-Path $scriptPath)) {
    Write-Error "Script not found: $scriptPath"
    exit 2
}

if (-not (Test-Path $Python)) {
    Write-Error "Python not found: $Python"
    exit 2
}

$argsList = @($scriptPath, $Page)
if ($StrictDrafts) { $argsList += "--strict-drafts" }
if ($DryRun) { $argsList += "--dry-run" }
if ($PSBoundParameters.ContainsKey('Date') -and -not [string]::IsNullOrWhiteSpace($Date)) {
    $argsList += "--date"; $argsList += $Date
}
if ($PSBoundParameters.ContainsKey('Note') -and -not [string]::IsNullOrWhiteSpace($Note)) {
    $argsList += "--note"; $argsList += $Note
}

& $Python @argsList
exit $LASTEXITCODE
