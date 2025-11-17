#!/usr/bin/env python3
"""
GitHub Profile README Automation System

This script automates the generation and maintenance of a GitHub profile README by:
1. Fetching recent GitHub activity (commits, PRs, issues) for the past week
2. Generating a natural language summary of weekly activity using Anthropic's Claude AI
3. Updating README.md with the activity summary and timestamp

Author: David Adams
License: All Rights Reserved
Repository: https://github.com/davidatoms/davidatoms

Usage:
    python update_readme.py
    
Environment Variables Required:
    README_GITHUB_TOKEN: GitHub Personal Access Token with repo and read:user permissions
    README_CLAUDE_TOKEN: Anthropic API key for Claude access
    
Output:
    - github_data/activity_summary.json: Activity summary cache
    - github_data/activity_summary.txt: Activity summary text file
    - README.md: Updated profile README with weekly activity summary
"""

import os
import json
import time
import requests
import re
import pathlib
from datetime import datetime, timedelta
from python_graphql_client import GraphqlClient
import sys

# Try to load from .env file if python-dotenv is available (for local testing)
try:
    from dotenv import load_dotenv
    load_dotenv()  # This will load .env file if it exists
except ImportError:
    pass  # dotenv not installed, that's okay - we'll use environment variables directly

# Get environment variables directly
GITHUB_USERNAME = "davidatoms"

# Paths and file setup (safe to do at module level)
root = pathlib.Path(__file__).parent.parent.parent.resolve()  # Go up to repo root
DATA_DIRECTORY = root / "github_data"
ACTIVITY_SUMMARY_FILE = DATA_DIRECTORY / "activity_summary.json"
ACTIVITY_SUMMARY_TEXT_FILE = DATA_DIRECTORY / "activity_summary.txt"
README_FILE = root / "README.md"

# Ensure data directory exists
os.makedirs(DATA_DIRECTORY, exist_ok=True)

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

def fetch_recent_activity(github_token):
    """
    Fetch recent GitHub activity (commits, PRs, issues) for the past week
    """
    print("\nSTEP 1: Fetching recent GitHub activity...")
    
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v4+json"
    }
    
    # Initialize GraphQL client
    client = GraphqlClient(endpoint="https://api.github.com/graphql")
    
    # Calculate date 7 days ago
    week_ago = (datetime.now() - timedelta(days=7)).isoformat() + "Z"
    
    query = """
    query($sinceDateTime: DateTime!, $sinceGitTimestamp: GitTimestamp!) {
      user(login: "davidatoms") {
        contributionsCollection(from: $sinceDateTime) {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          commitContributionsByRepository(maxRepositories: 10) {
            repository {
              name
              url
            }
            contributions {
              totalCount
            }
          }
        }
        pullRequests(first: 10, orderBy: {field: UPDATED_AT, direction: DESC}, states: [OPEN, MERGED, CLOSED]) {
          nodes {
            title
            state
            url
            repository {
              name
            }
            updatedAt
            mergedAt
            closedAt
          }
        }
        issues(first: 10, orderBy: {field: UPDATED_AT, direction: DESC}, states: [OPEN, CLOSED]) {
          nodes {
            title
            state
            url
            repository {
              name
            }
            updatedAt
            closedAt
          }
        }
        repositories(first: 10, orderBy: {field: UPDATED_AT, direction: DESC}, privacy: PUBLIC) {
          nodes {
            name
            url
            updatedAt
            defaultBranchRef {
              target {
                ... on Commit {
                  history(first: 5, since: $sinceGitTimestamp) {
                    nodes {
                      message
                      committedDate
                      url
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    try:
        variables = {
            "sinceDateTime": week_ago,
            "sinceGitTimestamp": week_ago
        }
        response = client.execute(query=query, headers=headers, variables=variables)
        
        if "errors" in response:
            print(f"GraphQL errors: {response['errors']}")
            return {}
        
        user_data = response["data"]["user"]
        contributions = user_data["contributionsCollection"]
        
        activity_data = {
            "period_start": week_ago,
            "period_end": datetime.now().isoformat() + "Z",
            "summary": {
                "total_commits": contributions["totalCommitContributions"],
                "total_issues": contributions["totalIssueContributions"],
                "total_prs": contributions["totalPullRequestContributions"],
                "total_reviews": contributions["totalPullRequestReviewContributions"]
            },
            "commits_by_repo": [
                {
                    "repo": repo["repository"]["name"],
                    "repo_url": repo["repository"]["url"],
                    "commit_count": repo["contributions"]["totalCount"]
                }
                for repo in contributions["commitContributionsByRepository"]
            ],
            "pull_requests": [
                {
                    "title": pr["title"],
                    "state": pr["state"],
                    "url": pr["url"],
                    "repo": pr["repository"]["name"],
                    "updated_at": pr["updatedAt"],
                    "merged_at": pr.get("mergedAt"),
                    "closed_at": pr.get("closedAt")
                }
                for pr in user_data["pullRequests"]["nodes"]
                if pr["updatedAt"] >= week_ago
            ],
            "issues": [
                {
                    "title": issue["title"],
                    "state": issue["state"],
                    "url": issue["url"],
                    "repo": issue["repository"]["name"],
                    "updated_at": issue["updatedAt"],
                    "closed_at": issue.get("closedAt")
                }
                for issue in user_data["issues"]["nodes"]
                if issue["updatedAt"] >= week_ago
            ],
            "recent_commits": []
        }
        
        # Extract recent commits from repositories
        for repo in user_data["repositories"]["nodes"]:
            if repo["defaultBranchRef"] and repo["defaultBranchRef"]["target"]:
                commits = repo["defaultBranchRef"]["target"].get("history", {}).get("nodes", [])
                for commit in commits:
                    if commit["committedDate"] >= week_ago:
                        activity_data["recent_commits"].append({
                            "message": commit["message"],
                            "repo": repo["name"],
                            "repo_url": repo["url"],
                            "date": commit["committedDate"],
                            "url": commit["url"]
                        })
        
        print(f"Activity data collected:")
        print(f"  - {activity_data['summary']['total_commits']} commits")
        print(f"  - {activity_data['summary']['total_prs']} pull requests")
        print(f"  - {activity_data['summary']['total_issues']} issues")
        print(f"  - {len(activity_data['recent_commits'])} recent commits")
        
        return activity_data
        
    except Exception as e:
        print(f"Error fetching activity: {e}")
        import traceback
        traceback.print_exc()
        return {}

def generate_activity_summary(activity_data, claude_api_key):
    """
    Generate a natural language summary of weekly activity using Claude
    """
    print("\nSTEP 2: Generating activity summary with Claude...")
    
    if not activity_data or not activity_data.get("summary"):
        print("No activity data to summarize.")
        return None
    
    # Check if we have a recent summary (within last 6 days)
    if os.path.exists(ACTIVITY_SUMMARY_FILE):
        try:
            with open(ACTIVITY_SUMMARY_FILE, 'r', encoding='utf-8') as f:
                cached_summary = json.load(f)
            generated_at_str = cached_summary.get("generated_at", "")
            if generated_at_str:
                # Handle ISO format with or without timezone
                if generated_at_str.endswith("Z"):
                    generated_at_str = generated_at_str.replace("Z", "+00:00")
                summary_date = datetime.fromisoformat(generated_at_str)
                # Remove timezone info for comparison
                if summary_date.tzinfo:
                    summary_date = summary_date.replace(tzinfo=None)
                if (datetime.now() - summary_date) < timedelta(days=6):
                    summary_text = cached_summary.get("summary_text")
                    # Also write to text file for easy access
                    if summary_text:
                        with open(ACTIVITY_SUMMARY_TEXT_FILE, 'w', encoding='utf-8') as f:
                            f.write(summary_text)
                    print("Using cached activity summary (less than 6 days old).")
                    return summary_text
        except Exception as e:
            print(f"Error reading cached summary: {e}")
    
    # Format activity data for Claude
    summary_parts = []
    
    if activity_data["summary"]["total_commits"] > 0:
        summary_parts.append(f"Made {activity_data['summary']['total_commits']} commits")
        if activity_data["commits_by_repo"]:
            top_repos = sorted(activity_data["commits_by_repo"], key=lambda x: x["commit_count"], reverse=True)[:3]
            repo_names = [r["repo"] for r in top_repos]
            summary_parts.append(f"across {len(activity_data['commits_by_repo'])} repositories, with most activity in {', '.join(repo_names)}")
    
    if activity_data["summary"]["total_prs"] > 0:
        pr_states = {}
        for pr in activity_data["pull_requests"]:
            state = pr["state"].lower()
            pr_states[state] = pr_states.get(state, 0) + 1
        pr_details = ", ".join([f"{count} {state}" for state, count in pr_states.items()])
        summary_parts.append(f"Worked on {activity_data['summary']['total_prs']} pull requests ({pr_details})")
    
    if activity_data["summary"]["total_issues"] > 0:
        issue_states = {}
        for issue in activity_data["issues"]:
            state = issue["state"].lower()
            issue_states[state] = issue_states.get(state, 0) + 1
        issue_details = ", ".join([f"{count} {state}" for state, count in issue_states.items()])
        summary_parts.append(f"Addressed {activity_data['summary']['total_issues']} issues ({issue_details})")
    
    if activity_data["summary"]["total_reviews"] > 0:
        summary_parts.append(f"Reviewed {activity_data['summary']['total_reviews']} pull requests")
    
    activity_text = "\n".join(summary_parts) if summary_parts else "Limited activity this week"
    
    # Add recent commit messages for context
    if activity_data["recent_commits"]:
        commit_messages = "\n".join([
            f"- {commit['repo']}: {commit['message'][:100]}"
            for commit in activity_data["recent_commits"][:10]
        ])
        activity_text += f"\n\nRecent commits:\n{commit_messages}"
    
    # Generate summary with Claude
    headers = {
        "x-api-key": claude_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    data = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": f"""Generate a natural, engaging 2-3 sentence summary of my coding activity for the past week based on this data:

{activity_text}

Write it in first person, as if I'm describing what I've been working on. Make it conversational and highlight the most interesting or significant work. Focus on the impact and progress made, not just numbers.

IMPORTANT: Return ONLY the summary text as a single paragraph. Do NOT include any headings, titles, or markdown formatting like # or ##. Just the plain text summary."""
            }
        ]
    }
    
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
                    summary_text = result["content"][0]["text"].strip()
                    
                    # Remove any markdown headings (lines starting with #)
                    lines = summary_text.split('\n')
                    cleaned_lines = [line for line in lines if not line.strip().startswith('#')]
                    summary_text = '\n'.join(cleaned_lines).strip()
                    
                    # Cache the summary (JSON)
                    with open(ACTIVITY_SUMMARY_FILE, 'w', encoding='utf-8') as f:
                        json.dump({
                            "summary_text": summary_text,
                            "generated_at": datetime.now().isoformat(),
                            "activity_data": activity_data
                        }, f, indent=2)
                    
                    # Write summary to text file for easy insertion with echo/sed
                    with open(ACTIVITY_SUMMARY_TEXT_FILE, 'w', encoding='utf-8') as f:
                        f.write(summary_text)
                    
                    print("Activity summary generated successfully.")
                    return summary_text
                break
            elif response.status_code == 429 or response.status_code == 529:
                retry_count += 1
                print(f"Claude API overloaded or rate-limited. Retry {retry_count}/{max_retries} after {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"Claude API error: {response.status_code} - {response.text}")
                break
        
        except Exception as e:
            print(f"Exception calling Claude API: {e}")
            break
    
    return None

def update_readme(activity_summary=None):
    """
    Update the README.md file with activity summary and timestamp
    while preserving your personal bio and other sections.
    """
    print("\nSTEP 3: Updating README.md...")
    
    if not os.path.exists(README_FILE):
        print(f"ERROR: {README_FILE} not found.")
        return
    
    # Read existing README
    with open(README_FILE, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    # Update the last updated section
    now = datetime.now()
    last_updated = now.strftime('%B %d, %Y at %H:%M')
    day_of_year = now.timetuple().tm_yday
    year_progress = round(day_of_year / 365, 3)
    updated_content = replace_chunk(
        readme_content,
        "last_updated",
        f"{last_updated} ({day_of_year}/365 ({year_progress}) of the year)",
        inline=True
    )
    
    # Update activity summary if we have one
    if activity_summary:
        print("Inserting activity summary into README...")
        updated_content = replace_chunk(
            updated_content,
            "ai_generated_summary_recent_activity",
            activity_summary,
            inline=True
        )
    else:
        print("No activity summary to insert.")
    
    # Write updated README
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"README.md updated successfully.")

def main():
    """Run the complete process"""
    print("=" * 50)
    print("GitHub Profile README - Weekly Activity Summary")
    print("=" * 50)
    
    # Validate environment variables (moved here to be caught by try/except)
    GITHUB_TOKEN = os.environ.get("README_GITHUB_TOKEN")
    CLAUDE_API_KEY = os.environ.get("README_CLAUDE_TOKEN")
    
    print("\nEnvironment Check:")
    print(f"GitHub Token present: {'Yes' if GITHUB_TOKEN else 'No'}")
    print(f"Claude Token present: {'Yes' if CLAUDE_API_KEY else 'No'}")
    
    if not GITHUB_TOKEN:
        print("ERROR: README_GITHUB_TOKEN is not set in environment")
        sys.exit(1)
    if not CLAUDE_API_KEY:
        print("ERROR: README_CLAUDE_TOKEN is not set in environment")
        sys.exit(1)
    
    # Step 1: Fetch recent activity
    try:
        activity_data = fetch_recent_activity(GITHUB_TOKEN)
    except Exception as e:
        print(f"ERROR: Exception fetching activity data: {e}")
        import traceback
        traceback.print_exc()
        activity_data = {}
    
    # Step 2: Generate activity summary with Claude (if we have data)
    activity_summary = None
    if activity_data and activity_data.get("summary"):
        try:
            activity_summary = generate_activity_summary(activity_data, CLAUDE_API_KEY)
        except Exception as e:
            print(f"WARNING: Exception generating summary: {e}")
            import traceback
            traceback.print_exc()
            activity_summary = None
    
    # Step 3: Update README.md (always update timestamp, even if no summary)
    try:
        update_readme(activity_summary)
        print("\nREADME.md updated successfully!")
    except Exception as e:
        print(f"ERROR: Failed to update README: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    if activity_summary:
        print("Process completed successfully with activity summary!")
    else:
        print("WARNING: No activity summary generated, but README timestamp was updated.")
    
    sys.exit(0)

if __name__ == "__main__":
    main()