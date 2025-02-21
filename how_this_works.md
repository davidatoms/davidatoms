---

## How This Works

This README is automatically updated using:

1. **YAML Files for Descriptions**  
   - Each repository includes YAML-based metadata (or parsed README content) describing the project’s purpose and technologies.

2. **Anthropic's Claude Integration**  
   - The script reads the YAML data (or extracted README text) and sends it to Claude to generate short, concise project descriptions.

3. **`update_readme.py` Script**  
   - Gathers repository info from GitHub’s API.
   - Fetches or truncates each repo’s README content (or YAML metadata) as needed.
   - Calls Claude to generate or refine the description.
   - Updates the `README.md` placeholders between `<!-- CLAUDE_DESCRIPTION#_START -->` and `<!-- CLAUDE_DESCRIPTION#_END -->`.
   - Optionally commits and pushes changes back to GitHub.

By automating these steps, new or updated repositories get a concise description in this README with minimal manual effort.

---