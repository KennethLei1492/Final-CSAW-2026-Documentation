param(
    [Parameter(Mandatory=$true)][string]$Config,
    [switch]$Apply
)
$ErrorActionPreference = 'Stop'
$scribeScript = Join-Path $PSScriptRoot '..\scribe.mjs'
$scribeArgs = @('--no-warnings', $scribeScript, 'setup', '--config', $Config)
if ($Apply) { $scribeArgs += '--apply' }
& node @scribeArgs
if ($LASTEXITCODE -ne 0) { throw 'Project Scribe setup failed. Review the message above.' }
