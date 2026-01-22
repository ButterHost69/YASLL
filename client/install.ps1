# install.ps1
# Run as Administrator or a user with pip access

set-strictmode -Version Latest
$ErrorActionPreference = "Stop"

# -------- CONFIG --------
$EnvFile = ".env"  # Path to your existing .env file

# -------- FUNCTIONS --------

function Load-DotEnv($path) {
    if (-Not (Test-Path $path)) {
        throw "Env file not found at $path"
    }
    
    # Get content, skip comments and empty lines
    $envVars = Get-Content $path | Where-Object { 
        $_ -match "=" -and -not $_.StartsWith("#") -and -not [string]::IsNullOrWhiteSpace($_)
    }

    foreach ($line in $envVars) {
        $parts = $line -split "=", 2
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()

        # Optional: Remove surrounding quotes from value if present (common in .env)
        $value = $value -replace '^"|"$','' -replace "^'|'$",''

        Write-Output "Setting environment variable: $name"
        
        # FIX: Use Set-Item for dynamic environment variable names
        Set-Item -Path "env:$name" -Value $value
    }
}

function Install-AWSCLI() {
    Write-Output "Installing/upgrading AWS CLI ; Boto3 and other required packages via pip..."
    pip install --upgrade awscli
    pip install --upgrade python-dotenv boto3
}

function Configure-AWSCLI() {
    # Check variables (now correctly loaded into the Env drive)
    if (-not (Get-Item -Path env:AWS_ACCESS_KEY_ID -ErrorAction SilentlyContinue) -or 
        -not (Get-Item -Path env:AWS_SECRET_ACCESS_KEY -ErrorAction SilentlyContinue) -or 
        -not (Get-Item -Path env:AWS_DEFAULT_REGION -ErrorAction SilentlyContinue)) {
        throw "AWS environment variables not found. Ensure your .env has AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION"
    }

    Write-Output "Configuring AWS CLI..."
    aws configure set aws_access_key_id $env:AWS_ACCESS_KEY_ID
    aws configure set aws_secret_access_key $env:AWS_SECRET_ACCESS_KEY
    aws configure set region $env:AWS_DEFAULT_REGION

    if ($env:AWS_DEFAULT_OUTPUT) {
        aws configure set output $env:AWS_DEFAULT_OUTPUT
    }

    Write-Output "AWS CLI configured successfully!"
}

# -------- SCRIPT --------

Write-Output "Loading environment variables from $EnvFile"
Load-DotEnv $EnvFile

Write-Output "Installing/upgrading AWS CLI..."
Install-AWSCLI

Write-Output "Configuring AWS CLI from environment variables..."
Configure-AWSCLI

Write-Output "Done ✅"