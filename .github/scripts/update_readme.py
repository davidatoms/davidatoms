#!/usr/bin/env python3
"""
github_to_readme.py - Lists your 10 most recent GitHub repositories with Claude-generated descriptions
"""

import os
import json
import time
import requests
import re
import pathlib
from datetime import datetime
from dotenv import load_dotenv
from python_graphql_client import GraphqlClient
import sys

load_dotenv()

GITHUB_USERNAME = "davidatoms"
GITHUB_TOKEN = os.getenv("README_GITHUB_TOKEN")
CLAUDE_API_KEY = os.getenv("README_CLAUDE_TOKEN")
MAX_REPOS = 10  

root = pathlib.Path(__file__).parent.parent.parent.resolve()  # Go up to repo root
DATA_DIRECTORY = root / "github_data"
GITHUB_DATA_FILE = DATA_DIRECTORY / "github_repos.json"
CLAUDE_DESCRIPTIONS_FILE = DATA_DIRECTORY / "claude_descriptions.json"
README_FILE = root / "README.md"

# Ensure data directory exists
os.makedirs(DATA_DIRECTORY, exist_ok=True)

# Add this new GraphQL client setup
client = GraphqlClient(endpoint="https://api.github.com/graphql")

# Add these debug lines
print("Debug token info:")
print(f"Token found: {'Yes' if GITHUB_TOKEN else 'No'}")
print(f"Token length: {len(GITHUB_TOKEN) if GITHUB_TOKEN else 0}")
print(f"Token starts with: {GITHUB_TOKEN[:7] if GITHUB_TOKEN else 'None'}...")

def replace_chunk(content, marker, chunk, inline=False):
    """
    Replace text between markers in the README file
    """
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    if not inline:
        chunk = "\n{}\n".format(chunk)
    chunk = "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)

def fetch_github_data():
    """
    Fetch the ten most recent repositories using GraphQL
    """
    print("STEP 1: Fetching GitHub repository data...")
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v4+json"
    }
    
    query = """
    query {
      user(login: "davidatoms") {
        repositories(first: 10, privacy: PUBLIC, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            name
            url
            description
            isPrivate
            isFork
            updatedAt
            object(expression: "HEAD:README.md") {
              ... on Blob {
                text
              }
            }
          }
        }
      }
    }
    """
    
    try:
        response = client.execute(query=query, headers=headers)
        repos = response["data"]["user"]["repositories"]["nodes"]
        
        repos_to_process = []
        for repo in repos:
            if not repo["isPrivate"]:  # Skip private repos
                repos_to_process.append({
                    "name": repo["name"],
                    "url": repo["url"],
                    "description": repo["description"],
                    "type": "fork" if repo["isFork"] else "original",
                    "updated_at": repo["updatedAt"],
                    "readme": repo["object"]["text"] if repo["object"] else ""
                })
        
        # Save the data
        with open(GITHUB_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(repos_to_process, f, indent=2)
        
        print(f"GitHub data saved to {GITHUB_DATA_FILE}")
        print(f"  - {len(repos_to_process)} repositories processed")
        
        return repos_to_process
        
    except Exception as e:
        print(f"Error fetching repos: {e}")
        return []

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
    retry_delay = 5  
    
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

def update_readme(repos, descriptions):
    """
    Update the README.md file with repository descriptions
    while preserving your personal bio and other sections.
    """
    print("\nSTEP 3: Updating README.md...")
    
    if not os.path.exists(README_FILE):
        print(f"ERROR: {README_FILE} not found.")
        return
    
    # Read existing README
    with open(README_FILE, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    # Format repositories list
    repos_md = "\n\n".join([
        f"[**{repo['name']}**]({repo['url']}) - {descriptions[repo['name']]['text']}"
        for repo in repos 
        if repo['name'] in descriptions
    ])
    
    # Update the repositories section
    updated_content = replace_chunk(readme_content, "recent_repos", repos_md)
    
    # Update the last updated section
    now = datetime.now()
    last_updated = now.strftime('%B %d, %Y at %H:%M')
    day_of_year = now.timetuple().tm_yday
    year_progress = round(day_of_year / 365, 3)
    updated_content = replace_chunk(
        updated_content, 
        "last_updated", 
        f"{last_updated} ({day_of_year}/365 ({year_progress}) of the year)",
        inline=True
    )
    
    # Write updated README
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"README.md updated successfully with new descriptions.")

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