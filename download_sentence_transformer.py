#!/usr/bin/env python3
"""
Download sentence-transformers model manually to ./models/all-MiniLM-L6-v2
This script downloads all the files that make up the sentence-transformers model.
"""

import os
from huggingface_hub import snapshot_download

def download_sentence_transformer_model():
    """Download the sentence-transformers model manually to ./models directory"""
    
    # Model configuration
    model_repo = "sentence-transformers/all-MiniLM-L6-v2"
    local_dir = os.path.join("models", "all-MiniLM-L6-v2")
    
    print(f"📥 Downloading {model_repo} to {local_dir}")
    print("This will download all model files (config.json, pytorch_model.bin, tokenizer files, etc.)")
    
    # Create models directory if it doesn't exist
    os.makedirs("models", exist_ok=True)
    
    try:
        # Download the entire model repository
        snapshot_download(
            repo_id=model_repo,
            local_dir=local_dir,
            local_dir_use_symlinks=False,  # Use actual files, not symlinks
            resume_download=True,          # Resume if partially downloaded
        )
        
        print(f"✅ Successfully downloaded {model_repo} to {local_dir}")
        
        # List downloaded files
        print("\n📁 Downloaded files:")
        for root, dirs, files in os.walk(local_dir):
            level = root.replace(local_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                print(f"{subindent}{file} ({size_str})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        print("\n💡 Alternative methods:")
        print("1. Try running this script with a stable internet connection")
        print("2. Use 'git lfs clone' if you have git-lfs installed:")
        print(f"   git clone https://huggingface.co/{model_repo} {local_dir}")
        print("3. Download manually from https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/main")
        return False

if __name__ == "__main__":
    print("🚀 Sentence-Transformers Model Downloader")
    print("=" * 50)
    
    success = download_sentence_transformer_model()
    
    if success:
        print("\n🎉 Download complete!")
        print("Your diagnostic agent will now use the local model instead of downloading it during Docker build.")
        print("\n📋 Next steps:")
        print("1. Run your Docker build: ./deploy.sh or .\\deploy.ps1")
        print("2. The build should be much faster now!")
    else:
        print("\n❌ Download failed. The Docker build will fall back to auto-download during build.")
