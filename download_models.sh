#!/bin/bash
#
# Download Models Script for Diagnostic Agent
# Downloads TinyLlama and Sentence Transformer models for local deployment
#
# Usage:
#   ./download_models.sh                    # Download all models
#   ./download_models.sh --tinyllama-only   # Download only TinyLlama
#   ./download_models.sh --sentence-only    # Download only sentence transformer
#   ./download_models.sh --check            # Check existing models
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Model configurations
TINYLLAMA_URL="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-GGUF/resolve/main/tinyllama-1.1b-chat.Q4_K_M.gguf"
TINYLLAMA_PATH="./models/tinyllama.gguf"
SENTENCE_MODEL_NAME="sentence-transformers/all-MiniLM-L6-v2"
SENTENCE_MODEL_PATH="./models/all-MiniLM-L6-v2"

# Parse command line arguments
DOWNLOAD_TINYLLAMA=true
DOWNLOAD_SENTENCE=true
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --tinyllama-only)
            DOWNLOAD_SENTENCE=false
            shift
            ;;
        --sentence-only)
            DOWNLOAD_TINYLLAMA=false
            shift
            ;;
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --help|-h)
            echo -e "${GREEN}Download Models Script for Diagnostic Agent${NC}"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --tinyllama-only    Download only TinyLlama model"
            echo "  --sentence-only     Download only sentence transformer model"
            echo "  --check             Check existing models without downloading"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Models:"
            echo "  TinyLlama:          ~600MB GGUF model for local inference"
            echo "  Sentence Transformer: ~120MB model for embeddings/search"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🔽 Diagnostic Agent Model Downloader${NC}"
echo -e "${GRAY}============================================${NC}"

# Create models directory
if [[ ! -d "models" ]]; then
    echo -e "${YELLOW}📁 Creating models directory...${NC}"
    mkdir -p models
fi

# Function to check file size
check_file_size() {
    local file_path="$1"
    if [[ -f "$file_path" ]]; then
        local size_bytes=$(stat -f%z "$file_path" 2>/dev/null || stat -c%s "$file_path" 2>/dev/null || echo "0")
        if [[ $size_bytes -gt 1000000 ]]; then
            local size_mb=$((size_bytes / 1024 / 1024))
            echo "${size_mb}MB"
        else
            echo "${size_bytes}B"
        fi
    else
        echo "Not found"
    fi
}

# Function to check models
check_models() {
    echo -e "${BLUE}📋 Checking existing models...${NC}"
    echo ""
    
    # Check TinyLlama
    local tinyllama_size=$(check_file_size "$TINYLLAMA_PATH")
    if [[ -f "$TINYLLAMA_PATH" && "$tinyllama_size" != "Not found" ]]; then
        echo -e "  ✅ TinyLlama: ${GREEN}Found${NC} ($tinyllama_size)"
    else
        echo -e "  ❌ TinyLlama: ${RED}Missing${NC}"
    fi
    
    # Check Sentence Transformer
    if [[ -d "$SENTENCE_MODEL_PATH" && -n "$(ls -A "$SENTENCE_MODEL_PATH" 2>/dev/null)" ]]; then
        local file_count=$(find "$SENTENCE_MODEL_PATH" -type f | wc -l)
        echo -e "  ✅ Sentence Transformer: ${GREEN}Found${NC} ($file_count files)"
    else
        echo -e "  ❌ Sentence Transformer: ${RED}Missing${NC}"
    fi
    
    # Check cache directory
    local cache_dir="$HOME/.cache/sentence_transformers"
    if [[ -d "$cache_dir" && -n "$(ls -A "$cache_dir" 2>/dev/null)" ]]; then
        echo -e "  ℹ️  Sentence Transformer Cache: ${CYAN}Found${NC}"
    else
        echo -e "  ⚠️  Sentence Transformer Cache: ${YELLOW}Empty${NC}"
    fi
}

# Function to download TinyLlama
download_tinyllama() {
    echo -e "${YELLOW}📥 Downloading TinyLlama model...${NC}"
    echo -e "${GRAY}URL: $TINYLLAMA_URL${NC}"
    echo -e "${GRAY}Size: ~600MB${NC}"
    
    if [[ -f "$TINYLLAMA_PATH" ]]; then
        local existing_size=$(check_file_size "$TINYLLAMA_PATH")
        echo -e "${YELLOW}⚠️  File already exists ($existing_size)${NC}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${CYAN}Skipping TinyLlama download${NC}"
            return
        fi
    fi
    
    # Download with progress bar
    if command -v wget >/dev/null 2>&1; then
        wget --progress=bar:force:noscroll -O "$TINYLLAMA_PATH" "$TINYLLAMA_URL"
    elif command -v curl >/dev/null 2>&1; then
        curl -L --progress-bar -o "$TINYLLAMA_PATH" "$TINYLLAMA_URL"
    else
        echo -e "${RED}❌ Error: Neither wget nor curl is available${NC}"
        echo "Please install wget or curl to download models"
        exit 1
    fi
    
    # Verify download
    if [[ -f "$TINYLLAMA_PATH" ]]; then
        local final_size=$(check_file_size "$TINYLLAMA_PATH")
        echo -e "${GREEN}✅ TinyLlama downloaded successfully ($final_size)${NC}"
    else
        echo -e "${RED}❌ TinyLlama download failed${NC}"
        exit 1
    fi
}

# Function to download Sentence Transformer
download_sentence_transformer() {
    echo -e "${YELLOW}📥 Downloading Sentence Transformer model...${NC}"
    echo -e "${GRAY}Model: $SENTENCE_MODEL_NAME${NC}"
    echo -e "${GRAY}Size: ~120MB${NC}"
    
    if [[ -d "$SENTENCE_MODEL_PATH" && -n "$(ls -A "$SENTENCE_MODEL_PATH" 2>/dev/null)" ]]; then
        echo -e "${YELLOW}⚠️  Model directory already exists${NC}"
        read -p "Re-download? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${CYAN}Skipping Sentence Transformer download${NC}"
            return
        fi
        rm -rf "$SENTENCE_MODEL_PATH"
    fi
    
    # Check if Python and required packages are available
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}❌ Python3 not found${NC}"
        echo "Python3 is required to download the sentence transformer model"
        exit 1
    fi
    
    # Try to use the download script
    if [[ -f "download_sentence_transformer.py" ]]; then
        echo -e "${CYAN}Using download_sentence_transformer.py...${NC}"
        python3 download_sentence_transformer.py
    else
        echo -e "${CYAN}Creating temporary download script...${NC}"
        cat > temp_download_sentence.py << 'EOF'
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
EOF
        
        # Install huggingface_hub if needed
        python3 -c "import huggingface_hub" 2>/dev/null || {
            echo -e "${YELLOW}Installing huggingface_hub...${NC}"
            pip3 install huggingface_hub
        }
        
        python3 temp_download_sentence.py
        rm temp_download_sentence.py
    fi
    
    # Verify download
    if [[ -d "$SENTENCE_MODEL_PATH" && -n "$(ls -A "$SENTENCE_MODEL_PATH" 2>/dev/null)" ]]; then
        local file_count=$(find "$SENTENCE_MODEL_PATH" -type f | wc -l)
        echo -e "${GREEN}✅ Sentence Transformer downloaded successfully ($file_count files)${NC}"
    else
        echo -e "${RED}❌ Sentence Transformer download failed${NC}"
        exit 1
    fi
}

# Main execution
check_models

if [[ "$CHECK_ONLY" == true ]]; then
    echo -e "\n${CYAN}Check complete. Use without --check to download missing models.${NC}"
    exit 0
fi

echo ""

# Download models based on flags
if [[ "$DOWNLOAD_TINYLLAMA" == true ]]; then
    download_tinyllama
    echo ""
fi

if [[ "$DOWNLOAD_SENTENCE" == true ]]; then
    download_sentence_transformer
    echo ""
fi

# Final check
echo -e "${GREEN}🎉 Model download complete!${NC}"
echo ""
check_models

echo ""
echo -e "${CYAN}📝 Next steps:${NC}"
echo -e "${GRAY}  • Run deployment: ./deploy.sh or .\\deploy.ps1${NC}"
echo -e "${GRAY}  • Models will be mounted into containers automatically${NC}"
echo -e "${GRAY}  • Use './download_models.sh --check' to verify models anytime${NC}"
