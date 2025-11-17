# Installation and Configuration Guide

This document provides comprehensive instructions for deploying an automated GitHub profile README with AI-generated weekly activity summaries.

## Prerequisites

- GitHub account
- GitHub Personal Access Token with `repo` and `read:user` permissions
- Anthropic API key with Claude access
- Git installed locally (optional, for local testing)
- Python 3.11+ (optional, for local testing)

## Step 1: Repository Creation

Create a special GitHub repository that matches your username:

1. Navigate to https://github.com/new
2. Configure the repository:
   - **Repository name**: `<your-username>` (must match your GitHub username exactly)
   - **Description**: "Automated GitHub profile with AI-generated content"
   - **Visibility**: Public (required for profile README functionality)
   - **Initialize**: Check "Add a README file"
3. Click "Create repository"

**Note**: GitHub automatically displays the README from a repository named after your username on your profile page.

## Step 2: Project Structure Setup

Clone your repository and establish the required directory structure:

```bash
git clone git@github.com:<your-username>/<your-username>.git
cd <your-username>
```

Create the following structure:

```
<your-username>/
├── .github/
│   ├── workflows/
│   │   └── update-readme.yml
│   └── scripts/
│       └── update_readme.py
├── github_data/
│   └── activity_summary.json (auto-generated)
├── README.md
├── how_this_works.md
├── SETUP.md
├── requirements.txt
├── .gitignore
├── light_mode.svg (optional)
└── dark_mode.svg (optional)
```

## Step 3: Configuration Files

### requirements.txt

Create a requirements file for Python dependencies:

```txt
python-dotenv>=1.0.0
requests>=2.31.0
python-graphql-client>=0.4.3
pathlib>=1.0.1
```

### .gitignore

Ensure sensitive files are excluded:

```
.env
__pycache__/
*.pyc
.DS_Store
```

## Step 4: GitHub Secrets Configuration

Configure repository secrets for API authentication:

1. Navigate to your repository on GitHub
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

   **README_GITHUB_TOKEN**
   - Value: GitHub Personal Access Token
   - Permissions required: `repo`, `read:user`
   - [Generate token here](https://github.com/settings/tokens/new)

   **README_CLAUDE_TOKEN**
   - Value: Anthropic API key
   - [Get API key here](https://console.anthropic.com/settings/keys)

## Step 5: README.md Template

Update your README.md to include content markers for automated updates:

```markdown
# Your Name

<p align="left"><b>Last Updated:</b> <!-- last_updated starts --><!-- last_updated ends --></p>

<p>AI-generated summary of my recent coding activity</p>
<!-- ai_generated_summary_recent_activity starts --><!-- ai_generated_summary_recent_activity ends -->

Your bio and introduction here.
```

**Critical**: The HTML comment markers are required for the automation to work.

## Step 6: Deploy Files

Commit and push all configuration files:

```bash
git add .
git commit -m "Initial setup: Add automated profile README system"
git push origin main
```

## Step 7: Manual Trigger and Verification

### Initial Run

1. Navigate to **Actions** tab in your repository
2. Select **Update README** workflow
3. Click **Run workflow** → **Run workflow**
4. Monitor execution in the workflow run logs

### Verification Checklist

- [ ] Workflow completes without errors
- [ ] `github_data/activity_summary.json` is populated
- [ ] README.md is updated with weekly activity summary
- [ ] Last updated timestamp is current
- [ ] Profile page displays updated content (visit `https://github.com/<your-username>`)

## Features

This automated profile README provides:

### Core Functionality
- **AI-Generated Activity Summaries**: Claude Haiku 4.5 generates natural language summaries of your weekly coding activity
- **Automatic Updates**: Weekly scheduled updates via GitHub Actions
- **Comprehensive Repository Data**: Includes all public repos (owned, collaborated, org member)
- **Smart Caching**: Reuses descriptions for unchanged repositories
- **Graceful Degradation**: Falls back to GitHub descriptions on API failures

### Customization Options
- **Update Frequency**: Modify cron schedule in workflow file
- **Repository Count**: Adjust `MAX_REPOS` in Python script
- **Description Style**: Customize AI prompt for different tones
- **Content Sections**: Add additional markers for expandable content

## Configuration Options

### Workflow Schedule

Modify the update frequency in `.github/workflows/update-readme.yml`:

```yaml
schedule:
  - cron: "0 12 * * 2"  # Weekly on Tuesdays at 12:00 UTC
```

Common schedules:
- Daily: `"0 0 * * *"`
- Weekly: `"0 0 * * 0"` (Sunday)
- Monthly: `"0 0 1 * *"` (1st of month)

### Repository Count

Adjust the number of displayed repositories in `update_readme.py`:

```python
MAX_REPOS = 10  # Change to desired number
```

### AI Model Configuration

Modify the Claude model or parameters:

```python
data = {
    "model": "claude-haiku-4-5-20251001",  # Update model version
    "max_tokens": 150,  # Adjust description length
}
```

### Description Prompt Customization

Edit the instruction in `generate_descriptions()` function:

```python
instruction = "Generate a concise 1-2 sentence description..."  # Customize tone/style
```

### GraphQL Query Customization

Modify the repository filter criteria:

```graphql
repositories(
  first: 20,
  privacy: PUBLIC,
  orderBy: {field: UPDATED_AT, direction: DESC},
  ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]
)
```

Available `ownerAffiliations` options:
- `OWNER`: Repositories you own
- `COLLABORATOR`: Repositories you collaborate on
- `ORGANIZATION_MEMBER`: Repositories in your organizations

## Troubleshooting

### Workflow Failures

**Authentication Errors**
```
ValueError: README_GITHUB_TOKEN is not set in environment
```
**Solution**: Verify repository secrets are properly configured in Settings → Secrets and variables → Actions

**API Rate Limiting**
```
Claude API error: 429
```
**Solution**: The script implements exponential backoff. If persistent, reduce update frequency or repository count.

**GraphQL Errors**
```
Error fetching repos: ...
```
**Solution**: 
- Verify GitHub token has correct permissions (`repo`, `read:user`)
- Check token hasn't expired
- Ensure username in query matches account

### Local Testing

Test the script locally before deployment:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export README_GITHUB_TOKEN="your_token_here"
export README_CLAUDE_TOKEN="your_claude_key_here"

# Run script
python .github/scripts/update_readme.py
```

### Data Issues

**Stale Descriptions**

Delete cache to force regeneration:
```bash
rm github_data/claude_descriptions.json
```

**Missing Repositories**

Increase fetch count in GraphQL query:
```python
repositories(first: 30, ...)  # Increase from 20
```

### README Not Updating

1. Check workflow execution logs in Actions tab
2. Verify content markers exist in README.md:
   ```html
   <!-- recent_repos starts --><!-- recent_repos ends -->
   <!-- last_updated starts --><!-- last_updated ends -->
   ```
3. Ensure bot has write permissions (should be automatic for GitHub Actions)

## Maintenance

### Regular Tasks

- **Review AI Descriptions**: Periodically check generated descriptions for accuracy
- **Update Dependencies**: Keep Python packages current
  ```bash
  pip install --upgrade -r requirements.txt
  ```
- **Monitor API Costs**: Track Claude API usage via Anthropic console
- **Rotate Tokens**: Refresh GitHub and Claude tokens periodically for security

### Extending Functionality

Potential enhancements:

1. **Add GitHub Statistics**
   - Integration with github-readme-stats
   - Custom contribution graphs
   - Language distribution charts

2. **Multi-Section Updates**
   - Recent blog posts (RSS feed)
   - Latest tweets or social media
   - Conference talks or presentations

3. **Advanced Filtering**
   - Exclude specific repositories
   - Prioritize by star count or activity
   - Separate sections for different project types

4. **Enhanced AI Features**
   - Multi-language descriptions
   - Technical depth customization
   - Keyword extraction and tagging

## Additional Resources

- [GitHub Profile README Guide](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-github-profile/customizing-your-profile/managing-your-profile-readme)
- [Anthropic Claude API Documentation](https://docs.anthropic.com/)
- [GitHub GraphQL API Explorer](https://docs.github.com/en/graphql/overview/explorer)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Support

For issues or questions:
1. Check existing GitHub Issues in this repository
2. Review workflow execution logs in Actions tab
3. Consult API documentation for authentication/rate limit issues
4. Create a new issue with detailed error logs and configuration
