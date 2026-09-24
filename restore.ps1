# Restore this branch with its root pixi-sandbox binary.
# On Windows this resolves to .\pixi-sandbox.exe at the branch root.
[CmdletBinding()]
param(
[Parameter(Position = 0)]
[string] $OutputPath = (Get-Location).Path,
[Parameter(ValueFromRemainingArguments = $true)]
[string[]] $RestoreArgs
)
$BranchDir = $PSScriptRoot
$Binary = Join-Path $BranchDir 'pixi-sandbox.exe'
if (-not (Test-Path -LiteralPath $Binary)) {
$Binary = Join-Path $BranchDir 'pixi-sandbox'
}
& $Binary restore --branch-location $BranchDir --output-path $OutputPath --force @RestoreArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
