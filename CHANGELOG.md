# Changelog

All notable changes to this GitHub profile automation project are documented in this file.

## [Unreleased] - 2025-11-17

### Added
- Comprehensive formal documentation in `SETUP.md`
  - Prerequisites section with required tools and tokens
  - Step-by-step installation guide
  - Configuration options for customization
  - Troubleshooting section with common issues
  - Maintenance guidelines
  - Additional resources and support information

- Enhanced `how_this_works.md` with system architecture documentation
  - Detailed technical implementation explanations
  - Data flow diagram
  - Performance characteristics
  - Security considerations
  - Caching strategy documentation
  - Rate limiting details

- Repository metadata collection
  - Primary programming language
  - Star count
  - Extended repository information

### Changed
- **Updated Claude AI model** from `claude-3-sonnet-20240229` to `claude-haiku-4-5-20251001` (latest version)
  - Faster processing with Claude Haiku 4.5
  - More cost-effective API usage
  - Improved description quality
  - Better understanding of technical content
  - More concise and accurate summaries

- **Enhanced GraphQL repository query**
  - Increased from 10 to 20 repositories fetched
  - Added `ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]`
  - Now includes repositories you own, collaborate on, or are part of via organizations
  - Filters top 10 for display after fetching broader set

- **Script header documentation**
  - Added comprehensive docstring
  - Included usage instructions
  - Listed required environment variables
  - Documented output files
  - Added license information (All Rights Reserved)

### Improved
- Documentation structure and formality across all markdown files
- Code organization and maintainability
- Error handling documentation
- Configuration flexibility

## Repository Scope Changes

### Before
- Only fetched repositories you directly own
- Limited to 10 repositories total

### After
- Fetches repositories across multiple affiliations:
  - Repositories you own
  - Repositories you collaborate on
  - Repositories in organizations you're a member of
- Fetches 20 repositories, displays top 10 most recently updated
- Provides broader view of your public work

## Migration Notes

No breaking changes. The system is fully backward compatible. Existing cache files will continue to work, and new features will activate automatically on next workflow run.

To force regeneration of descriptions with the new model:
```bash
rm github_data/claude_descriptions.json
```

Then manually trigger the workflow in GitHub Actions.

## Future Enhancements

Potential additions for future versions:
- GitHub statistics integration
- Multi-language description support
- Advanced repository filtering (by stars, language, etc.)
- Blog post integration via RSS
- Social media feed integration
