import sys
import os
from huggingface_hub import HfApi

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 src/upload_to_hf.py <your-hf-username> <your-hf-token>")
        sys.exit(1)
        
    username = sys.argv[1]
    token = sys.argv[2]
    repo_id = f"{username}/nepali-synthetic-ocr-lines"
    
    print(f"[*] Authenticating and uploading to Hugging Face dataset: {repo_id}")
    
    api = HfApi(token=token)
    try:
        # Create dataset repo on Hugging Face (if it doesn't already exist)
        api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, private=False)
        print(f"[+] Repository '{repo_id}' is ready.")
        
        # Upload folder
        print("[*] Uploading dataset files (this might take a minute)...")
        api.upload_folder(
            folder_path="dataset",
            repo_id=repo_id,
            repo_type="dataset"
        )
        print("\n" + "=" * 60)
        print("[+] Upload complete! You can view and download your dataset at:")
        print(f"    https://huggingface.co/datasets/{repo_id}")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n[!] Error uploading dataset: {e}\n")

if __name__ == "__main__":
    main()
