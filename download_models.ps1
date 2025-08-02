#!/usr/bin/env powershell
<#
.SYNOPSIS
Download Models Script for Diagnostic Agent (Windows)

.DESCRIPTION
Downloads TinyLlama and Sentence Transformer models for local deployment.
This is the Windows PowerShell version of download_models.sh.

.PARAMETER TinyLlamaOnly
Download only the TinyLlama model

.PARAMETER SentenceOnly
Download only the sentence transformer model

.PARAMETER Check
Check existing models without downloading

.EXAMPLE
.\download_models.ps1
Download all models

.EXAMPLE
.\download_models.ps1 -TinyLlamaOnly
Download only TinyLlama model

.EXAMPLE
.\download_models.ps1 -Check
Check existing models without downloading
#>

param(
    [switch]$TinyLlamaOnly,
    [switch]$SentenceOnly,
    [switch]$Check
)

# Model configurations
$TINYLLAMA_URL = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-GGUF/resolve/main/tinyllama-1.1b-chat.Q4_K_M.gguf"
$TINYLLAMA_PATH = ".\models\tinyllama.gguf"
$SENTENCE_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
$SENTENCE_MODEL_PATH = ".\models\all-MiniLM-L6-v2"

# Determine what to download
$DOWNLOAD_TINYLLAMA = !$SentenceOnly
$DOWNLOAD_SENTENCE = !$TinyLlamaOnly

Write-Host "Download Models for Diagnostic Agent" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Gray

# Create models directory
if (!(Test-Path "models")) {
    Write-Host "Creating models directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Name "models" | Out-Null
}

# Function to check file size
function Get-FileSize {
    param([string]$Path)
    
    if (Test-Path $Path) {
        $size = (Get-Item $Path).Length
        if ($size -gt 1MB) {
            return "$([math]::Round($size / 1MB, 1))MB"
        } else {
            return "$([math]::Round($size / 1KB, 1))KB"
        }
    } else {
        return "Not found"
    }
}

# Function to check models
function Check-Models {
    Write-Host "`nChecking existing models..." -ForegroundColor Blue
    
    # Check TinyLlama
    $tinySize = Get-FileSize $TINYLLAMA_PATH
    if ($tinySize -ne "Not found") {
        Write-Host "  [OK] TinyLlama: Found ($tinySize)" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] TinyLlama: Not found" -ForegroundColor Red
    }
    
    # Check Sentence Transformer
    if ((Test-Path $SENTENCE_MODEL_PATH) -and (Get-ChildItem $SENTENCE_MODEL_PATH -ErrorAction SilentlyContinue)) {
        $fileCount = (Get-ChildItem $SENTENCE_MODEL_PATH -Recurse -File).Count
        Write-Host "  [OK] Sentence Transformer: Found ($fileCount files)" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] Sentence Transformer: Not found" -ForegroundColor Red
    }
    
    # Check cache directory
    $cacheDir = "$env:USERPROFILE\.cache\sentence_transformers"
    if ((Test-Path $cacheDir) -and (Get-ChildItem $cacheDir -ErrorAction SilentlyContinue)) {
        Write-Host "  [INFO] Sentence Transformer Cache: Found" -ForegroundColor Cyan
    } else {
        Write-Host "  [WARN] Sentence Transformer Cache: Empty" -ForegroundColor Yellow
    }
}

# Function to download TinyLlama
function Download-TinyLlama {
    Write-Host "`nDownloading TinyLlama model..." -ForegroundColor Yellow
    Write-Host "URL: $TINYLLAMA_URL" -ForegroundColor Gray
    Write-Host "Size: ~600MB" -ForegroundColor Gray
    
    if (Test-Path $TINYLLAMA_PATH) {
        $existingSize = Get-FileSize $TINYLLAMA_PATH
        Write-Host "File already exists ($existingSize)" -ForegroundColor Yellow
        $response = Read-Host "Overwrite? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "Skipping TinyLlama download" -ForegroundColor Cyan
            return
        }
    }
    
    try {
        Write-Host "Starting download..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri $TINYLLAMA_URL -OutFile $TINYLLAMA_PATH -UseBasicParsing
        
        if (Test-Path $TINYLLAMA_PATH) {
            $finalSize = Get-FileSize $TINYLLAMA_PATH
            Write-Host "TinyLlama downloaded successfully ($finalSize)" -ForegroundColor Green
        } else {
            Write-Error "TinyLlama download failed"
            exit 1
        }
    } catch {
        Write-Error "TinyLlama download failed: $_"
        exit 1
    }
}

# Function to download Sentence Transformer
function Download-SentenceTransformer {
    Write-Host "`nDownloading Sentence Transformer model..." -ForegroundColor Yellow
    Write-Host "Model: $SENTENCE_MODEL_NAME" -ForegroundColor Gray
    Write-Host "Size: ~120MB" -ForegroundColor Gray
    
    if ((Test-Path $SENTENCE_MODEL_PATH) -and (Get-ChildItem $SENTENCE_MODEL_PATH -ErrorAction SilentlyContinue)) {
        Write-Host "Model directory already exists" -ForegroundColor Yellow
        $response = Read-Host "Re-download? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Host "Skipping Sentence Transformer download" -ForegroundColor Cyan
            return
        }
        Remove-Item $SENTENCE_MODEL_PATH -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    # Check if Python is available
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "Using Python: $pythonVersion" -ForegroundColor Gray
    } catch {
        Write-Error "Python not found. Python is required to download the sentence transformer model."
        exit 1
    }
    
    # Use existing download script if available
    if (Test-Path "download_sentence_transformer.py") {
        Write-Host "Using download_sentence_transformer.py..." -ForegroundColor Cyan
        python download_sentence_transformer.py
    } else {
        Write-Host "Creating temporary download script..." -ForegroundColor Cyan
        
        $downloadScript = @'
import os
from huggingface_hub import snapshot_download

model_repo = "sentence-transformers/all-MiniLM-L6-v2"
local_dir = "models/all-MiniLM-L6-v2"

print(f"Downloading {model_repo} to {local_dir}")
os.makedirs("models", exist_ok=True)

try:
    snapshot_download(
        repo_id=model_repo,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    print(f"Successfully downloaded to {local_dir}")
except Exception as e:
    print(f"Download failed: {e}")
    exit(1)
'@
        
        $downloadScript | Out-File -FilePath "temp_download_sentence.py" -Encoding UTF8
        
        # Install huggingface_hub if needed
        try {
            python -c "import huggingface_hub" 2>$null
        } catch {
            Write-Host "Installing huggingface_hub..." -ForegroundColor Yellow
            pip install huggingface_hub
        }
        
        python temp_download_sentence.py
        Remove-Item "temp_download_sentence.py" -ErrorAction SilentlyContinue
    }
    
    # Verify download
    if ((Test-Path $SENTENCE_MODEL_PATH) -and (Get-ChildItem $SENTENCE_MODEL_PATH -ErrorAction SilentlyContinue)) {
        $fileCount = (Get-ChildItem $SENTENCE_MODEL_PATH -Recurse -File).Count
        Write-Host "Sentence Transformer downloaded successfully ($fileCount files)" -ForegroundColor Green
    } else {
        Write-Error "Sentence Transformer download failed"
        exit 1
    }
}

# Main execution
Check-Models

if ($Check) {
    Write-Host "`nCheck complete. Run without -Check to download missing models." -ForegroundColor Cyan
    exit 0
}

# Download models based on flags
if ($DOWNLOAD_TINYLLAMA) {
    Download-TinyLlama
}

if ($DOWNLOAD_SENTENCE) {
    Download-SentenceTransformer
}

# Final check
Write-Host "`nModel download complete!" -ForegroundColor Green
Check-Models

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "  • Run deployment: .\deploy.ps1" -ForegroundColor Gray
Write-Host "  • Models will be mounted into containers automatically" -ForegroundColor Gray
Write-Host "  • Use '.\download_models.ps1 -Check' to verify models anytime" -ForegroundColor Gray
