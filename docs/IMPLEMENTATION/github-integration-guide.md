# GitHub Integration Implementation Guide

This guide provides step-by-step instructions for implementing and configuring the GitHub Projects and Wikis integration with BMAD.

## Overview

The GitHub integration enables seamless synchronization between:
- **BMAD Epics** ↔ **GitHub Projects**
- **BMAD Stories** ↔ **GitHub Issues**  
- **Documentation** ↔ **GitHub Wikis**

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation & Setup](#installation--setup)
3. [Configuration](#configuration)
4. [Authentication](#authentication)
5. [Testing the Integration](#testing-the-integration)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

## Prerequisites

### System Requirements
- Python 3.8+
- Flask application with BMAD methodology implemented
- GitHub repository with admin access
- GitHub Personal Access Token or GitHub App

### Required Permissions
Your GitHub token needs the following scopes:
- `repo` - Repository access
- `write:repo_hook` - Webhook management
- `read:org` - Organization access (if applicable)
- `project` - Project board access
- `wiki` - Wiki access

### Dependencies
```bash
pip install requests>=2.31.0
pip install pydantic>=2.0.0
pip install pyyaml>=6.0
```

## Installation & Setup

### 1. Enable GitHub Integration

Add the GitHub integration routes to your Flask application:

```python
# In your main Flask app file
from api.github_integration_routes import github_bp

app.register_blueprint(github_bp)
```

### 2. Environment Variables

Set up the required environment variables:

```bash
export GITHUB_TOKEN="your_github_token_here"
export GITHUB_OWNER="your_github_username_or_org"
export GITHUB_REPO="your_repository_name"
export GITHUB_WEBHOOK_SECRET="your_webhook_secret"
export GITHUB_CONFIG_PATH="config/github_integration.json"
```

### 3. Initialize Configuration

```python
from config.github_integration_config import GitHubConfigManager

# Initialize configuration
config_manager = GitHubConfigManager()
config = config_manager.get_config()

# Validate configuration
errors = config_manager.validate_config()
if errors:
    print("Configuration errors:", errors)
```

## Configuration

### Basic Configuration

Create a configuration file at `config/github_integration.json`:

```json
{
  "version": "1.0.0",
  "enabled": true,
  "authentication": {
    "token": "${GITHUB_TOKEN}",
    "method": "personal_token",
    "webhook_secret": "${GITHUB_WEBHOOK_SECRET}"
  },
  "repository": {
    "owner": "${GITHUB_OWNER}",
    "name": "${GITHUB_REPO}",
    "default_branch": "main",
    "wiki_enabled": true,
    "projects_enabled": true
  },
  "epic_mapping": {
    "enabled": true,
    "auto_create_projects": true,
    "project_template": "EPIC: {epic_name}",
    "project_description_template": "Epic: {epic_description}\\n\\nBMAD Phase: {current_phase}",
    "default_columns": ["To Do", "In Progress", "Review", "Done"],
    "labels": ["epic", "bmad"]
  },
  "story_mapping": {
    "enabled": true,
    "auto_create_issues": true,
    "issue_template": "STORY: {story_title}",
    "labels": ["story", "bmad"],
    "milestone_mapping": true
  },
  "wiki_integration": {
    "enabled": true,
    "auto_update": true,
    "epic_page_template": "Epic-{epic_id}-{epic_name}",
    "story_page_template": "Story-{story_id}-{story_title}",
    "index_page": "BMAD-Project-Index"
  },
  "synchronization": {
    "enabled": true,
    "bidirectional": true,
    "real_time_webhook": true,
    "batch_sync_interval": 300,
    "retry_attempts": 3
  },
  "monitoring": {
    "enabled": true,
    "metrics_collection": true,
    "log_level": "INFO"
  }
}
```

### Template Customization

#### Epic Project Templates

Customize how epics are represented as GitHub projects:

```json
{
  "epic_mapping": {
    "project_template": "EPIC: {epic_name} | Phase: {current_phase}",
    "project_description_template": "## Epic Overview\\n{epic_description}\\n\\n**Current Phase**: {current_phase}\\n**Progress**: {progress_percentage}%\\n\\n**Technical Details**:\\n{technical_details}",
    "default_columns": ["Backlog", "In Progress", "Review", "Testing", "Done"]
  }
}
```

#### Story Issue Templates

Customize how stories are represented as GitHub issues:

```json
{
  "story_mapping": {
    "issue_template": "[{priority}] STORY: {story_title}",
    "issue_body_template": "## Story Description\\n{story_description}\\n\\n## Acceptance Criteria\\n{acceptance_criteria}\\n\\n## Epic Context\\n**Epic**: {epic_name}\\n**Phase**: {current_phase}\\n\\n## Implementation Notes\\n{technical_details}"
  }
}
```

#### Wiki Page Templates

Customize wiki page structure and content:

```json
{
  "wiki_integration": {
    "epic_page_content_template": "# Epic: {epic_name}\\n\\n## Overview\\n{epic_description}\\n\\n## Progress\\n- **Phase**: {current_phase}\\n- **Completion**: {progress_percentage}%\\n\\n## Stories\\n{stories_list}\\n\\n## Architecture\\n{technical_architecture}",
    "story_page_content_template": "# Story: {story_title}\\n\\n## Description\\n{story_description}\\n\\n## Epic\\n[{epic_name}]({epic_wiki_link})\\n\\n## Implementation\\n{technical_implementation}"
  }
}
```

## Authentication

### Personal Access Token (Recommended)

1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Generate a new token with required scopes
3. Set the token in your environment variables

### GitHub App (Advanced)

For organizations, consider using a GitHub App:

```json
{
  "authentication": {
    "method": "github_app",
    "app_id": "12345",
    "app_private_key": "/path/to/private-key.pem",
    "installation_id": "67890"
  }
}
```

### Webhook Configuration

Set up webhooks for real-time synchronization:

1. Go to your repository Settings > Webhooks
2. Add webhook with:
   - **URL**: `https://your-domain.com/api/github/webhook`
   - **Content type**: `application/json`
   - **Secret**: Your webhook secret
   - **Events**: `Issues`, `Projects`, `Project cards`

## Testing the Integration

### 1. Configuration Test

```python
from config.github_integration_config import GitHubConfigManager

manager = GitHubConfigManager()
test_results = manager.test_configuration()
print(test_results)
```

### 2. API Endpoints Test

Test via HTTP requests:

```bash
# Test configuration
curl -X GET http://localhost:5000/api/github/config

# Test health check
curl -X GET http://localhost:5000/api/github/health

# Test manual sync
curl -X POST http://localhost:5000/api/github/sync/manual \
  -H "Content-Type: application/json" \
  -d '{"type": "epics", "force": true}'
```

### 3. Run Test Suite

```bash
# Run integration tests
pytest tests/test_github_integration.py -v

# Run with coverage
pytest tests/test_github_integration.py --cov=src.github_integration
```

## Usage Examples

### Sync Epic to GitHub Project

```python
from src.github_integration.epic_mapping_service import EpicMappingService
from src.github_integration.github_api_client import GitHubAPIClient
from config.github_integration_config import get_github_config

# Initialize services
config = get_github_config()
github_client = GitHubAPIClient(
    token=config.authentication.token,
    owner=config.repository.owner,
    repo=config.repository.name
)
epic_service = EpicMappingService(config, github_client)

# Epic data
epic_data = {
    "id": "epic_auth",
    "name": "Authentication System",
    "description": "Implement user authentication",
    "current_phase": "build",
    "progress_percentage": 45
}

# Sync to GitHub
result = epic_service.sync_epic_to_project(epic_data)
print(f"Status: {result.status}, Project ID: {result.project_id}")
```

### Sync Story to GitHub Issue

```python
from src.github_integration.story_mapping_service import StoryMappingService

# Initialize service
story_service = StoryMappingService(config, github_client)

# Story data
story_data = {
    "id": "story_login",
    "title": "Login Form Implementation",
    "description": "Create login form with validation",
    "epic_id": "epic_auth",
    "current_phase": "build",
    "priority": "high",
    "assignee": "developer1"
}

# Sync to GitHub
result = story_service.sync_story_to_issue(story_data, epic_data)
print(f"Status: {result.status}, Issue Number: {result.issue_number}")
```

### Generate Wiki Documentation

```python
from src.github_integration.wiki_integration_service import WikiIntegrationService

# Initialize service
wiki_service = WikiIntegrationService(config, github_client)

# Sync documentation
epic_result = wiki_service.sync_epic_documentation(epic_data)
story_result = wiki_service.sync_story_documentation(story_data, epic_data)

print(f"Epic wiki: {epic_result.page_url}")
print(f"Story wiki: {story_result.page_url}")
```

### Full Synchronization

```python
# Complete sync of all epics and stories
epics = [epic_data]  # Your epic data
stories = [story_data]  # Your story data

# Sync everything
results = []

for epic in epics:
    # Sync epic to project
    epic_result = epic_service.sync_epic_to_project(epic)
    results.append(epic_result)
    
    # Sync epic documentation
    wiki_result = wiki_service.sync_epic_documentation(epic)
    results.append(wiki_result)

for story in stories:
    # Find parent epic
    parent_epic = next(e for e in epics if e["id"] == story["epic_id"])
    
    # Sync story to issue
    story_result = story_service.sync_story_to_issue(story, parent_epic)
    results.append(story_result)
    
    # Sync story documentation
    wiki_result = wiki_service.sync_story_documentation(story, parent_epic)
    results.append(wiki_result)

# Check results
for result in results:
    print(f"{result.__class__.__name__}: {result.status}")
```

## Troubleshooting

### Common Issues

#### 1. Authentication Failures

**Error**: `GitHubAuthenticationError: Invalid GitHub token`

**Solution**:
- Verify token has correct scopes
- Check token hasn't expired
- Ensure token is set in environment variables

#### 2. Rate Limit Exceeded

**Error**: `GitHubRateLimitError: Rate limit exceeded`

**Solution**:
- Wait for rate limit reset
- Implement exponential backoff
- Consider using GitHub App for higher limits

#### 3. Webhook Signature Verification Failed

**Error**: `Invalid webhook signature`

**Solution**:
- Verify webhook secret matches configuration
- Check payload encoding (should be UTF-8)
- Ensure using correct hashing algorithm (SHA-256)

#### 4. Wiki Not Available

**Error**: `Wiki not available or not initialized`

**Solution**:
- Initialize wiki in GitHub repository
- Create at least one page manually
- Verify repository has wiki enabled

### Debug Mode

Enable debug logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('src.github_integration')
logger.setLevel(logging.DEBUG)
```

### Health Checks

Monitor integration health:

```bash
# Check overall health
curl -X GET http://localhost:5000/api/github/health

# Check sync status
curl -X GET http://localhost:5000/api/github/sync/status

# View metrics
curl -X GET http://localhost:5000/api/github/metrics
```

## Advanced Configuration

### Custom Label Management

```python
# Custom phase-to-label mapping
PHASE_LABELS = {
    'build': ['phase:build', 'status:development'],
    'measure': ['phase:measure', 'status:testing'],
    'analyze': ['phase:analyze', 'status:review'],
    'document': ['phase:document', 'status:documentation']
}
```

### Assignee Mapping

```json
{
  "story_mapping": {
    "assignee_mapping": {
      "john_doe": "johndoe-github",
      "jane_smith": "janesmith-gh",
      "team_lead": "teamlead"
    }
  }
}
```

### Milestone Management

```python
# Automatic milestone creation for epics
def create_epic_milestone(epic_data):
    milestone = github_client.create_milestone(
        title=f"Epic: {epic_data['name']}",
        description=epic_data['description'],
        due_on=epic_data.get('target_completion')
    )
    return milestone['number']
```

### Custom Sync Workflows

```python
class CustomSyncWorkflow:
    def __init__(self, config, github_client):
        self.epic_service = EpicMappingService(config, github_client)
        self.story_service = StoryMappingService(config, github_client)
        self.wiki_service = WikiIntegrationService(config, github_client)
    
    def sync_with_validation(self, epic_data, stories_data):
        # Custom validation before sync
        if not self._validate_epic(epic_data):
            return {"error": "Epic validation failed"}
        
        # Sync with custom logic
        results = []
        
        # Epic sync with custom column setup
        epic_result = self.epic_service.sync_epic_to_project(epic_data)
        if epic_result.status == 'created':
            self._setup_custom_columns(epic_result.project_id)
        
        results.append(epic_result)
        
        # Story sync with custom prioritization
        for story in sorted(stories_data, key=lambda s: s.get('priority_score', 0)):
            story_result = self.story_service.sync_story_to_issue(story, epic_data)
            results.append(story_result)
        
        return results
```

## API Reference

### Configuration Endpoints

- `GET /api/github/config` - Get configuration
- `PUT /api/github/config` - Update configuration
- `POST /api/github/config/validate` - Validate configuration
- `POST /api/github/config/test` - Test configuration

### Projects & Issues

- `GET /api/github/projects` - List projects
- `POST /api/github/projects` - Create project
- `GET /api/github/issues` - List issues
- `POST /api/github/issues` - Create issue

### Synchronization

- `POST /api/github/sync/manual` - Manual sync
- `GET /api/github/sync/status` - Sync status
- `GET /api/github/sync/history` - Sync history

### Monitoring

- `GET /api/github/health` - Health check
- `GET /api/github/status` - Integration status
- `GET /api/github/metrics` - Performance metrics

## Security Considerations

1. **Token Security**: Store tokens in environment variables, never in code
2. **Webhook Security**: Always verify webhook signatures
3. **Rate Limiting**: Implement proper rate limiting and backoff
4. **Access Control**: Use minimal required permissions
5. **Audit Logging**: Log all integration activities
6. **Data Validation**: Validate all input data before processing

## Best Practices

1. **Incremental Sync**: Sync changes incrementally rather than full syncs
2. **Error Handling**: Implement comprehensive error handling and retry logic
3. **Monitoring**: Set up monitoring and alerting for integration health
4. **Testing**: Maintain comprehensive test coverage
5. **Documentation**: Keep configuration and usage documentation updated
6. **Backup**: Regularly backup integration configuration and mappings

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the test suite for examples
3. Check GitHub API documentation
4. Create an issue in the project repository

---

*Last updated: 2024-01-15*
*Version: 1.0.0*