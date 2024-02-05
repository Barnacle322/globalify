# Load environment variables from .env file
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#].+?)\s*=\s*(.+)\s*$') {
            $varName = $matches[1]
            $varValue = $matches[2] -replace '^"(.*)"$','$1'
            [System.Environment]::SetEnvironmentVariable($varName, $varValue, "Process")
        }
    }
}

flask run