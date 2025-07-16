# Used to create an editable template from a real OBS config file

$script:DataPath = $env:STREAMING_DATA_PATH # Change this manually if needed

$script:DataPath = if ($script:DataPath) {
  ($script:DataPath -replace '\\', '/').TrimEnd('/')
} else {
  $null
}

function ConvertTo-OBSTemplate {
  param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile
  )

  $OutputFile = $InputFile -replace "\.json$", ".template.json"

  Write-Host "Creating template from real config..." -ForegroundColor Green
  Write-Host "Input:  $InputFile" -ForegroundColor Gray
  Write-Host "Output: $OutputFile" -ForegroundColor Gray

  $content = Get-Content $InputFile -Raw

  if ($script:DataPath) {
    $content = $content -replace [regex]::Escape($script:DataPath), "{{STREAMING_DATA_PATH}}"
  }

  $content | Set-Content $OutputFile
  Write-Host "Template saved: $OutputFile" -ForegroundColor Yellow
}

function ConvertFrom-OBSTemplate {
  param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile
  )

  $OutputFile = $InputFile -replace "\.template\.", "."

  Write-Host "Creating real config from template..." -ForegroundColor Green
  Write-Host "Input:  $InputFile" -ForegroundColor Gray
  Write-Host "Output: $OutputFile" -ForegroundColor Gray

  $content = Get-Content $InputFile -Raw

  if ($content -match "{{STREAMING_DATA_PATH}}" -and -not $script:DataPath) {
    throw "Template contains {{STREAMING_DATA_PATH}} but STREAMING_DATA_PATH environment variable is not set"
  }

  if ($script:DataPath) {
    $content = $content -replace "{{STREAMING_DATA_PATH}}", $script:DataPath
  }

  $content | Set-Content $OutputFile
  Write-Host "Real config saved: $OutputFile" -ForegroundColor Yellow
}

Write-Host "OBS Templater functions loaded!" -ForegroundColor Green
Write-Host "Current paths:" -ForegroundColor Cyan
Write-Host "  Data Path: $($script:DataPath ?? 'Not set')" -ForegroundColor Gray
Write-Host ""
Write-Host "Usage:" -ForegroundColor Cyan
Write-Host "  ConvertTo-OBSTemplate 'scenes.json'             # Creates scenes.template.json (VC version)" -ForegroundColor Gray
Write-Host "  ConvertFrom-OBSTemplate 'scenes.template.json'  # Creates scenes.json" -ForegroundColor Gray

