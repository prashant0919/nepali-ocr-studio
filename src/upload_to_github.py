import sys
import os
import subprocess
import urllib.request
import json

def run_git_cmd(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Git command failed: {' '.join(args)}")
        print(f"    Error: {result.stderr.strip()}")
        return False
    return True

def create_github_repo(username, token, repo_name):
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    data = {
        "name": repo_name,
        "description": "Mountmind PeakOCR - Advanced Interactive Preprocessing Studio and Synthetic Devanagari Corpus Builder",
        "private": False,
        "has_issues": True,
        "has_projects": True,
        "has_wiki": True
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            print(f"[+] Successfully created GitHub repository: {res_data['html_url']}")
            return res_data["clone_url"]
    except urllib.error.HTTPError as e:
        res_body = e.read().decode("utf-8")
        try:
            res_json = json.loads(res_body)
            # If repo already exists, we can still get the clone URL
            if "already exists" in res_json.get("errors", [{}])[0].get("message", ""):
                print(f"[*] Repository '{repo_name}' already exists on GitHub. Proceeding with push.")
                return f"https://github.com/{username}/{repo_name}.git"
        except Exception:
            pass
        print(f"[!] GitHub API Error: {e.code} {e.reason}")
        print(f"    Details: {res_body}")
        return None

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 src/upload_to_github.py <your-github-username> <your-github-token>")
        sys.exit(1)
        
    username = sys.argv[1]
    token = sys.argv[2]
    repo_name = "nepali-ocr-studio"
    
    # 1. Create .gitignore if it doesn't exist
    gitignore_path = ".gitignore"
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write("venv/\n.venv/\n__pycache__/\n*.pyc\n.DS_Store\noutputs/line_crops/\ndataset/\n")
        print("[+] Created .gitignore file.")
        
    # 2. Git init and commit
    print("[*] Initializing local Git repository...")
    if not os.path.exists(".git"):
        if not run_git_cmd(["git", "init", "-b", "main"]):
            # Fallback for older git versions
            if run_git_cmd(["git", "init"]):
                run_git_cmd(["git", "checkout", "-b", "main"])
    
    # Configure user credentials locally if needed
    run_git_cmd(["git", "config", "user.name", username])
    run_git_cmd(["git", "config", "user.email", f"{username}@users.noreply.github.com"])
    
    print("[*] Staging files...")
    run_git_cmd(["git", "add", "."])
    
    print("[*] Committing files...")
    # Check if there's anything to commit
    status_proc = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if status_proc.stdout.strip():
        run_git_cmd(["git", "commit", "-m", "Initial commit: Mountmind PeakOCR Studio codebase with structured parser, synthetic corpus builder, and Hugging Face integration"])
        print("[+] Committed changes locally.")
    else:
        print("[*] Nothing new to commit.")

    # 3. Create repo on GitHub
    print(f"[*] Creating GitHub repository '{repo_name}' under user '{username}'...")
    clone_url = create_github_repo(username, token, repo_name)
    if not clone_url:
        print("[!] Aborting push due to repo creation failure.")
        sys.exit(1)
        
    # Inject token into the clone URL for authentication
    auth_clone_url = clone_url.replace("https://github.com/", f"https://{username}:{token}@github.com/")
    
    # 4. Set remote and push
    # Remove existing remote if present
    subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
    
    print("[*] Adding git remote 'origin'...")
    if not run_git_cmd(["git", "remote", "add", "origin", auth_clone_url]):
        sys.exit(1)
        
    print("[*] Pushing to GitHub 'main' branch...")
    # Try pushing
    result = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True, text=True)
    if result.returncode != 0:
        # Try pushing master branch if main branch is missing
        print("[*] Push to main failed, trying master branch...")
        result = subprocess.run(["git", "push", "-u", "origin", "master"], capture_output=True, text=True)
        
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("[+] Code successfully uploaded to GitHub!")
        print(f"    Repository URL: https://github.com/{username}/{repo_name}")
        print("=" * 60 + "\n")
    else:
        print(f"[!] Push failed: {result.stderr.strip()}")

if __name__ == "__main__":
    main()
