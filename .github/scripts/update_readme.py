#!/usr/bin/env python3
"""
github_to_readme.py
-------------------
A 3-step process to update your GitHub README.md with Claude-generated descriptions
while preserving your personal bio and other sections:

1. Fetch GitHub Data: Get repo info and README content from GitHub API
2. Generate Descriptions: Send to Claude for processing, save permanent records
3. Update README.md: Update only the repo description sections of your README.md

Requirements:
- Python 3.6+
- requests
- python-dotenv (optional, for .env file)

Set environment variables:
- GITHUB_TOKEN: Your GitHub personal access token
- CLAUDE_API_KEY: Your Anthropic Claude API key
"""

import os
import json
import time
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GITHUB_USERNAME = "davidatoms"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
MAX_REPOS = 10  # Maximum repos to process

# File paths
DATA_DIRECTORY = "github_data"
GITHUB_DATA_FILE = f"{DATA_DIRECTORY}/github_repos.json"
CLAUDE_DESCRIPTIONS_FILE = f"{DATA_DIRECTORY}/claude_descriptions.json"
README_FILE = "README.md"

# Ensure data directory exists
os.makedirs(DATA_DIRECTORY, exist_ok=True)

# --------------------------------------------------
# STEP 1: Fetch GitHub Data
# --------------------------------------------------

def fetch_github_data():
    """
    Get the latest 10 repos from GitHub and save them.
    """
    print("Getting GitHub repos...")
    
    headers = {}
    if GITHUB_TOKEN:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos?sort=updated&per_page=10"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print("Error getting repos:", response.status_code, response.text)
        return {}
    
    repos = response.json()
    
    repos_to_process = []
    for repo in repos:
        repo_info = {
            "name": repo["name"],
            "url": repo["html_url"],
            "description": repo["description"],
            "type": "original" if not repo["fork"] else "fork",
            "readme": fetch_readme(repo["name"], headers)
        }
        repos_to_process.append(repo_info)
    
    with open(GITHUB_DATA_FILE, 'w') as f:
        json.dump(repos_to_process, f, indent=2)
    
    print("Saved GitHub data to file")
    print("Processed", len(repos_to_process), "repos")
    
    return repos_to_process

def fetch_readme(repo_name, headers):
    """Fetch README content for a repository"""
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/readme"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        import base64
        try:
            encoded_content = response.json().get("content", "")
            return base64.b64decode(encoded_content).decode("utf-8")
        except Exception as e:
            print(f"Error decoding README for {repo_name}: {e}")
    
    return ""

# --------------------------------------------------
# STEP 2: Generate Descriptions with Claude
# --------------------------------------------------

def generate_descriptions(repos):
    """
    Send README content to Claude API for each repo and save the results.
    Returns a dictionary of repo names and their Claude-generated descriptions.
    """
    print("\nSTEP 2: Generating descriptions with Claude...")
    
    if not CLAUDE_API_KEY:
        print("ERROR: CLAUDE_API_KEY not found in environment variables.")
        return {}
    
    # Check if descriptions file already exists
    existing_descriptions = {}
    if os.path.exists(CLAUDE_DESCRIPTIONS_FILE):
        try:
            with open(CLAUDE_DESCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                existing_descriptions = json.load(f)
            print(f"Found existing descriptions for {len(existing_descriptions)} repositories.")
        except json.JSONDecodeError:
            print("Error reading existing descriptions file. Starting fresh.")
    
    # Process each repo
    descriptions = {}
    for i, repo in enumerate(repos):
        repo_name = repo["name"]
        
        # Skip if we already have a description for this repo
        if repo_name in existing_descriptions:
            print(f"Using existing description for {repo_name}")
            descriptions[repo_name] = existing_descriptions[repo_name]
            continue
        
        print(f"Processing {i+1}/{len(repos)}: {repo_name}")
        
        # Use the same prompt for all repos
        description = get_claude_description(
            repo_name, 
            repo["readme"], 
            "Generate a concise 1-2 sentence description of this repository explaining what it does."
        )
        
        if description:
            descriptions[repo_name] = {
                "text": description,
                "generated_at": datetime.now().isoformat(),
                "repo_type": repo["type"]
            }
        else:
            # Fallback to GitHub description
            fallback = repo["description"] or f"Repository {repo_name}"
            descriptions[repo_name] = {
                "text": fallback,
                "generated_at": datetime.now().isoformat(),
                "repo_type": repo["type"],
                "is_fallback": True
            }
        
        # Save after each repo to maintain progress
        with open(CLAUDE_DESCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump({**existing_descriptions, **descriptions}, f, indent=2)
        
        # Rate limiting to avoid overloading
        if i < len(repos) - 1:
            time.sleep(2)
    
    print(f"Claude descriptions saved to {CLAUDE_DESCRIPTIONS_FILE}")
    return descriptions

def get_claude_description(repo_name, readme_content, instruction):
    """Send a single README to Claude and get a description"""
    if not readme_content:
        return None
    
    # Truncate if very long
    if len(readme_content) > 10000:
        readme_content = readme_content[:10000] + "... [truncated]"
    
    # Claude API request
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    data = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 150,
        "messages": [
            {
                "role": "user",
                "content": f"""
Repository name: {repo_name}

README content:
```
{readme_content}
```

{instruction}
Keep it under 150 characters if possible.
Avoid phrases like "This repository contains" or "This is a".
"""
            }
        ]
    }
    
    # Add retry logic with exponential backoff
    max_retries = 3
    retry_count = 0
    retry_delay = 5  # Start with 5 seconds
    
    while retry_count < max_retries:
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if "content" in result and len(result["content"]) > 0:
                    return result["content"][0]["text"].strip()
                break
            elif response.status_code == 429 or response.status_code == 529:
                # Rate limit or overloaded - retry after delay
                retry_count += 1
                print(f"Claude API overloaded or rate-limited. Retry {retry_count}/{max_retries} after {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Claude API error: {response.status_code} - {response.text}")
                break
        
        except Exception as e:
            print(f"Exception calling Claude API: {e}")
            break
    
    return None

# --------------------------------------------------
# STEP 3: Update README.md
# --------------------------------------------------

def update_readme(github_data, descriptions):
    """
    Update the README.md file with repository descriptions
    while preserving your personal bio and other sections.
    """
    print("\nSTEP 3: Updating README.md...")
    
    if not os.path.exists(README_FILE):
        print(f"ERROR: {README_FILE} not found. Creating a new one.")
        create_new_readme(github_data, descriptions)
        return
    
    # Read existing README
    with open(README_FILE, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    # Prepare a single list of all repos
    all_repos = []
    
    # Use the github_data list to keep the original sorting (most recent first)
    for repo in github_data:
        repo_name = repo["name"]
        if repo_name in descriptions:
            all_repos.append((repo_name, repo["url"], descriptions[repo_name]["text"], descriptions[repo_name]["repo_type"]))
    
    # Generate the combined section with all repos
    combined_section = ""
    for i, (repo_name, repo_url, desc, repo_type) in enumerate(all_repos):
        combined_section += f"- [{repo_name}]({repo_url}) - <!-- CLAUDE_DESCRIPTION{i+1}_START -->{desc}<!-- CLAUDE_DESCRIPTION{i+1}_END -->\n"
    
    # Update the PROJECTS-LIST section with all repos
    projects_pattern = re.compile(r'(<!-- PROJECTS-LIST:START -->).*?(<!-- PROJECTS-LIST:END -->)', re.DOTALL)
    readme_content = projects_pattern.sub(f'\\1 \n{combined_section}\\2', readme_content)
    
    # Remove the RECENT_FORKED_REPOS section if not needed anymore
    if "<!-- RECENT_FORKED_REPOS:START -->" in readme_content:
        forks_pattern = re.compile(r'(<!-- RECENT_FORKED_REPOS:START -->).*?(<!-- RECENT_FORKED_REPOS:END -->)', re.DOTALL)
        # Replace with empty content between the markers
        readme_content = forks_pattern.sub('\\1 \n\\2', readme_content)
    
    # Update the LAST_UPDATED section if it exists
    last_updated = datetime.now().strftime('%B %d, %Y at %H:%M')
    day_of_year = datetime.now().timetuple().tm_yday
    year_progress = round(day_of_year / 365, 3)
    
    updated_pattern = re.compile(r'(<!-- LAST_UPDATED:START -->).*?(<!-- LAST_UPDATED:END -->)', re.DOTALL)
    readme_content = updated_pattern.sub(f'\\1 {last_updated} ({day_of_year}/365 ({year_progress}) of the year) \\2', readme_content)
    
    # Write updated README
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"README.md updated successfully with new descriptions.")

def create_new_readme(github_data, descriptions):
    """Create a new README.md file if none exists"""
    # Create one combined list of repos
    all_repos = []
    for repo in github_data:
        repo_name = repo["name"]
        if repo_name in descriptions:
            all_repos.append((repo_name, repo["url"], descriptions[repo_name]["text"]))
    
    last_updated = datetime.now().strftime('%B %d, %Y at %H:%M')
    day_of_year = datetime.now().timetuple().tm_yday
    year_progress = round(day_of_year / 365, 3)
    
    # Generate combined section
    combined_section = ""
    for i, (repo_name, repo_url, desc) in enumerate(all_repos):
        combined_section += f"- [{repo_name}]({repo_url}) - <!-- CLAUDE_DESCRIPTION{i+1}_START -->{desc}<!-- CLAUDE_DESCRIPTION{i+1}_END -->\n"
    
    # Create README content with preserved bio
    readme_content = f"""# {GITHUB_USERNAME}'s GitHub Readme

<p align="left"><b>Last Updated:</b> <!-- LAST_UPDATED:START --> {last_updated} ({day_of_year}/365 ({year_progress}) of the year) <!-- LAST_UPDATED:END --></p>

<p align="left">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Go-00ADD8?style=flat&logo=go&logoColor=white" />
  <img src="https://img.shields.io/badge/Rust-000000?style=flat&logo=rust&logoColor=white" />
  <img src="https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB" />
  <img src="https://img.shields.io/badge/Bash-4EAA25?style=flat&logo=gnu-bash&logoColor=white" />
</p>

I am interested in how technology pushes the frontier of human possibility and in making life a little better for both now and the future. If you're interested in supporting, feel free to buy me a book from **The King's English**.

## Recent Repositories

<!-- PROJECTS-LIST:START --> 
{combined_section}<!-- PROJECTS-LIST:END -->

_Project descriptions generated by Anthropic's Claude, backed by GitHub Actions_

---

## How This Works

This README is automatically updated using:

1. **GitHub API Integration**  
   - Fetches repository information and README content.

2. **Anthropic's Claude Integration**  
   - Sends README content to Claude to generate short, concise project descriptions.

3. **Automated Updates**  
   - Updates this README.md with the latest repositories and descriptions.
   - Last updated on {last_updated}.

---
"""
    
    # Write new README
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"New {README_FILE} created successfully with your bio preserved.")

# --------------------------------------------------
# Main Function
# --------------------------------------------------

def main():
    """Run the complete process"""
    print("=" * 50)
    print("GitHub to README.md Pipeline")
    print("=" * 50)
    
    # Step 1: Fetch GitHub data
    github_data = fetch_github_data()
    if not github_data:
        print("ERROR: Failed to fetch GitHub data. Exiting.")
        return
    
    # Step 2: Generate descriptions with Claude
    descriptions = generate_descriptions(github_data)
    
    # Step 3: Update README.md
    if descriptions:
        update_readme(github_data, descriptions)
        print("\nProcess completed successfully!")
    else:
        print("ERROR: No descriptions generated. README not updated.")

if __name__ == "__main__":
    main()