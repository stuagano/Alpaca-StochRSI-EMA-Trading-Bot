"""
Tests for GitHub Integration with BMAD

Comprehensive test suite for GitHub Projects and Wikis integration
with mock GitHub API responses and validation.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

# Import the components we're testing
from src.github_integration.github_api_client import GitHubAPIClient, GitHubAPIError
from src.github_integration.epic_mapping_service import EpicMappingService
from src.github_integration.story_mapping_service import StoryMappingService
from src.github_integration.wiki_integration_service import WikiIntegrationService
from config.github_integration_config import GitHubIntegrationConfig, GitHubConfigManager


@pytest.fixture
def mock_config():
    """Create mock GitHub integration configuration"""
    config = Mock()
    config.enabled = True
    config.version = "1.0.0"
    
    # Authentication config
    config.authentication = Mock()
    config.authentication.token = "test_token"
    config.authentication.webhook_secret = "test_secret"
    
    # Repository config
    config.repository = Mock()
    config.repository.owner = "test_owner"
    config.repository.name = "test_repo"
    config.repository.wiki_enabled = True
    config.repository.projects_enabled = True
    
    # Epic mapping config
    config.epic_mapping = Mock()
    config.epic_mapping.enabled = True
    config.epic_mapping.auto_create_projects = True
    config.epic_mapping.project_template = "EPIC: {epic_name}"
    config.epic_mapping.project_description_template = "Epic: {epic_description}"
    config.epic_mapping.default_columns = ["To Do", "In Progress", "Done"]
    config.epic_mapping.labels = ["epic", "bmad"]
    
    # Story mapping config
    config.story_mapping = Mock()
    config.story_mapping.enabled = True
    config.story_mapping.auto_create_issues = True
    config.story_mapping.issue_template = "STORY: {story_title}"
    config.story_mapping.issue_body_template = "Story: {story_description}"
    config.story_mapping.labels = ["story", "bmad"]
    config.story_mapping.assignee_mapping = {}
    config.story_mapping.milestone_mapping = True
    
    # Wiki integration config
    config.wiki_integration = Mock()
    config.wiki_integration.enabled = True
    config.wiki_integration.auto_update = True
    config.wiki_integration.epic_page_template = "Epic-{epic_id}-{epic_name}"
    config.wiki_integration.story_page_template = "Story-{story_id}-{story_title}"
    config.wiki_integration.index_page = "BMAD-Project-Index"
    config.wiki_integration.epic_page_content_template = "# Epic: {epic_name}\n{epic_description}"
    config.wiki_integration.story_page_content_template = "# Story: {story_title}\n{story_description}"
    
    # Synchronization config
    config.synchronization = Mock()
    config.synchronization.enabled = True
    config.synchronization.real_time_webhook = True
    
    # Quality gates config
    config.quality_gates = Mock()
    config.quality_gates.enabled = True
    
    # Monitoring config
    config.monitoring = Mock()
    config.monitoring.enabled = True
    config.monitoring.metrics_collection = True
    
    return config


@pytest.fixture
def mock_github_client():
    """Create mock GitHub API client"""
    client = Mock(spec=GitHubAPIClient)
    
    # Mock authentication
    client.authenticated_user = {"login": "test_user"}
    client.test_connection.return_value = True
    
    # Mock projects
    client.get_projects.return_value = []
    client.create_project.return_value = {
        "id": 123,
        "name": "Test Project",
        "html_url": "https://github.com/test/repo/projects/123"
    }
    client.get_project.return_value = {
        "id": 123,
        "name": "Test Project",
        "body": "Test Description"
    }
    
    # Mock issues
    client.get_issues.return_value = []
    client.create_issue.return_value = {
        "number": 456,
        "title": "Test Issue",
        "html_url": "https://github.com/test/repo/issues/456"
    }
    client.get_issue.return_value = {
        "number": 456,
        "title": "Test Issue",
        "body": "Test Body"
    }
    
    # Mock wiki
    client.get_wiki_pages.return_value = []
    client.create_or_update_wiki_page.return_value = {
        "title": "Test Page",
        "html_url": "https://github.com/test/repo/wiki/Test-Page"
    }
    
    # Mock webhooks
    client.verify_webhook_signature.return_value = True
    
    return client


@pytest.fixture
def sample_epic_data():
    """Sample epic data for testing"""
    return {
        "id": "epic_123",
        "name": "User Authentication System",
        "description": "Implement comprehensive user authentication",
        "current_phase": "build",
        "status": "active",
        "progress_percentage": 45,
        "start_date": "2024-01-01",
        "target_completion": "2024-03-01",
        "updated_at": "2024-01-15T10:00:00Z"
    }


@pytest.fixture
def sample_story_data():
    """Sample story data for testing"""
    return {
        "id": "story_456",
        "title": "Login Form Implementation",
        "description": "Create login form with validation",
        "epic_id": "epic_123",
        "current_phase": "build",
        "status": "in_progress",
        "priority": "high",
        "assignee": "developer1",
        "acceptance_criteria": "User can login with valid credentials",
        "updated_at": "2024-01-15T12:00:00Z"
    }


class TestGitHubAPIClient:
    """Test GitHub API client functionality"""
    
    @patch('requests.Session')
    def test_client_initialization(self, mock_session):
        """Test GitHub API client initialization"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "test_user"}
        mock_session.return_value.request.return_value = mock_response
        
        client = GitHubAPIClient(
            token="test_token",
            owner="test_owner",
            repo="test_repo"
        )
        
        assert client.token == "test_token"
        assert client.owner == "test_owner"
        assert client.repo == "test_repo"
        assert client.authenticated_user == {"login": "test_user"}
    
    @patch('requests.Session')
    def test_authentication_error(self, mock_session):
        """Test authentication error handling"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_session.return_value.request.return_value = mock_response
        
        with pytest.raises(Exception):  # Should raise authentication error
            GitHubAPIClient(
                token="invalid_token",
                owner="test_owner",
                repo="test_repo"
            )
    
    def test_rate_limit_handling(self, mock_github_client):
        """Test rate limit handling"""
        # Mock rate limit exceeded
        mock_github_client._request.side_effect = Exception("Rate limit exceeded")
        
        with pytest.raises(Exception):
            mock_github_client.get_projects()


class TestEpicMappingService:
    """Test Epic to GitHub Project mapping service"""
    
    def test_sync_epic_to_project_create_new(self, mock_config, mock_github_client, sample_epic_data):
        """Test creating new GitHub project for epic"""
        service = EpicMappingService(mock_config, mock_github_client)
        service._get_epic_mapping = Mock(return_value=None)
        service._setup_project_columns = Mock(return_value=[])
        service._create_epic_mapping_record = Mock()
        
        result = service.sync_epic_to_project(sample_epic_data)
        
        assert result.status == 'created'
        assert result.epic_id == "epic_123"
        assert result.project_id == 123
        mock_github_client.create_project.assert_called_once()
    
    def test_sync_epic_to_project_update_existing(self, mock_config, mock_github_client, sample_epic_data):
        """Test updating existing GitHub project for epic"""
        service = EpicMappingService(mock_config, mock_github_client)
        
        # Mock existing mapping
        mock_mapping = Mock()
        mock_mapping.github_project_id = 123
        service._get_epic_mapping = Mock(return_value=mock_mapping)
        service._needs_project_update = Mock(return_value=True)
        service._prepare_project_updates = Mock(return_value={"name": "Updated Name"})
        service._update_epic_mapping_record = Mock()
        
        result = service.sync_epic_to_project(sample_epic_data, force_update=True)
        
        assert result.status == 'updated'
        assert result.epic_id == "epic_123"
        mock_github_client.update_project.assert_called_once()
    
    def test_sync_epic_to_project_already_synced(self, mock_config, mock_github_client, sample_epic_data):
        """Test epic already synced scenario"""
        service = EpicMappingService(mock_config, mock_github_client)
        
        mock_mapping = Mock()
        mock_mapping.github_project_id = 123
        service._get_epic_mapping = Mock(return_value=mock_mapping)
        service._needs_project_update = Mock(return_value=False)
        
        result = service.sync_epic_to_project(sample_epic_data)
        
        assert result.status == 'synced'
        assert result.epic_id == "epic_123"


class TestStoryMappingService:
    """Test Story to GitHub Issue mapping service"""
    
    def test_sync_story_to_issue_create_new(self, mock_config, mock_github_client, sample_story_data, sample_epic_data):
        """Test creating new GitHub issue for story"""
        service = StoryMappingService(mock_config, mock_github_client)
        service._get_story_mapping = Mock(return_value=None)
        service._add_issue_to_project_board = Mock()
        service._create_story_mapping_record = Mock()
        
        result = service.sync_story_to_issue(sample_story_data, sample_epic_data)
        
        assert result.status == 'created'
        assert result.story_id == "story_456"
        assert result.issue_number == 456
        mock_github_client.create_issue.assert_called_once()
    
    def test_sync_story_to_issue_update_existing(self, mock_config, mock_github_client, sample_story_data, sample_epic_data):
        """Test updating existing GitHub issue for story"""
        service = StoryMappingService(mock_config, mock_github_client)
        
        mock_mapping = Mock()
        mock_mapping.github_issue_number = 456
        service._get_story_mapping = Mock(return_value=mock_mapping)
        service._needs_issue_update = Mock(return_value=True)
        service._prepare_issue_updates = Mock(return_value={"title": "Updated Title"})
        service._update_story_mapping_record = Mock()
        
        result = service.sync_story_to_issue(sample_story_data, sample_epic_data, force_update=True)
        
        assert result.status == 'updated'
        assert result.story_id == "story_456"
        mock_github_client.update_issue.assert_called_once()
    
    def test_prepare_issue_labels(self, mock_config, mock_github_client, sample_story_data):
        """Test issue label preparation"""
        service = StoryMappingService(mock_config, mock_github_client)
        
        labels = service._prepare_issue_labels(sample_story_data, "build")
        
        assert "story" in labels
        assert "bmad" in labels
        assert "phase:build" in labels
        assert "priority:high" in labels
    
    def test_prepare_issue_assignees(self, mock_config, mock_github_client, sample_story_data):
        """Test issue assignee preparation"""
        service = StoryMappingService(mock_config, mock_github_client)
        
        assignees = service._prepare_issue_assignees(sample_story_data)
        
        assert "developer1" in assignees


class TestWikiIntegrationService:
    """Test GitHub Wiki integration service"""
    
    def test_sync_epic_documentation_create_new(self, mock_config, mock_github_client, sample_epic_data):
        """Test creating new wiki page for epic"""
        service = WikiIntegrationService(mock_config, mock_github_client)
        service._get_wiki_page = Mock(return_value=None)
        service._update_index_page = Mock()
        
        result = service.sync_epic_documentation(sample_epic_data)
        
        assert result.status == 'created'
        assert result.page_name.startswith('Epic-epic_123')
        mock_github_client.create_or_update_wiki_page.assert_called_once()
    
    def test_sync_story_documentation_create_new(self, mock_config, mock_github_client, sample_story_data, sample_epic_data):
        """Test creating new wiki page for story"""
        service = WikiIntegrationService(mock_config, mock_github_client)
        service._get_wiki_page = Mock(return_value=None)
        service._update_epic_story_references = Mock()
        
        result = service.sync_story_documentation(sample_story_data, sample_epic_data)
        
        assert result.status == 'created'
        assert result.page_name.startswith('Story-story_456')
        mock_github_client.create_or_update_wiki_page.assert_called_once()
    
    def test_generate_epic_page_name(self, mock_config, mock_github_client, sample_epic_data):
        """Test epic page name generation"""
        service = WikiIntegrationService(mock_config, mock_github_client)
        
        page_name = service._generate_epic_page_name(sample_epic_data)
        
        assert page_name == "Epic-epic_123-User-Authentication-System"
    
    def test_generate_story_page_name(self, mock_config, mock_github_client, sample_story_data):
        """Test story page name generation"""
        service = WikiIntegrationService(mock_config, mock_github_client)
        
        page_name = service._generate_story_page_name(sample_story_data)
        
        assert page_name == "Story-story_456-Login-Form-Implementation"
    
    def test_generate_epic_page_content(self, mock_config, mock_github_client, sample_epic_data):
        """Test epic page content generation"""
        service = WikiIntegrationService(mock_config, mock_github_client)
        
        content = service._generate_epic_page_content(sample_epic_data, [])
        
        assert "User Authentication System" in content
        assert "Implement comprehensive user authentication" in content
        assert "build" in content
    
    def test_generate_story_page_content(self, mock_config, mock_github_client, sample_story_data, sample_epic_data):
        """Test story page content generation"""
        service = WikiIntegrationService(mock_config, mock_github_client)
        
        content = service._generate_story_page_content(sample_story_data, sample_epic_data)
        
        assert "Login Form Implementation" in content
        assert "Create login form with validation" in content
        assert "User Authentication System" in content


class TestGitHubConfigManager:
    """Test GitHub configuration management"""
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open')
    def test_load_config_from_file(self, mock_open, mock_exists):
        """Test loading configuration from file"""
        mock_exists.return_value = True
        mock_config_data = {
            "authentication": {"token": "test_token"},
            "repository": {"owner": "test_owner", "name": "test_repo"},
            "epic_mapping": {},
            "story_mapping": {},
            "wiki_integration": {},
            "synchronization": {},
            "quality_gates": {},
            "monitoring": {}
        }
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_config_data)
        
        manager = GitHubConfigManager("test_config.json")
        config = manager.get_config()
        
        assert config.authentication.token == "test_token"
        assert config.repository.owner == "test_owner"
    
    def test_validate_config_valid(self, mock_config):
        """Test configuration validation with valid config"""
        manager = GitHubConfigManager()
        manager.config = mock_config
        
        errors = manager.validate_config()
        
        assert len(errors) == 0
    
    def test_validate_config_missing_token(self, mock_config):
        """Test configuration validation with missing token"""
        mock_config.authentication.token = ""
        
        manager = GitHubConfigManager()
        manager.config = mock_config
        
        errors = manager.validate_config()
        
        assert len(errors) > 0
        assert any("token is required" in error for error in errors)


class TestIntegrationScenarios:
    """Test full integration scenarios"""
    
    def test_full_epic_workflow(self, mock_config, mock_github_client, sample_epic_data):
        """Test complete epic synchronization workflow"""
        # Setup services
        epic_service = EpicMappingService(mock_config, mock_github_client)
        wiki_service = WikiIntegrationService(mock_config, mock_github_client)
        
        # Mock dependencies
        epic_service._get_epic_mapping = Mock(return_value=None)
        epic_service._setup_project_columns = Mock(return_value=[])
        epic_service._create_epic_mapping_record = Mock()
        wiki_service._get_wiki_page = Mock(return_value=None)
        wiki_service._update_index_page = Mock()
        
        # Execute workflow
        epic_result = epic_service.sync_epic_to_project(sample_epic_data)
        wiki_result = wiki_service.sync_epic_documentation(sample_epic_data)
        
        # Verify results
        assert epic_result.status == 'created'
        assert wiki_result.status == 'created'
        assert mock_github_client.create_project.called
        assert mock_github_client.create_or_update_wiki_page.called
    
    def test_full_story_workflow(self, mock_config, mock_github_client, sample_story_data, sample_epic_data):
        """Test complete story synchronization workflow"""
        # Setup services
        story_service = StoryMappingService(mock_config, mock_github_client)
        wiki_service = WikiIntegrationService(mock_config, mock_github_client)
        
        # Mock dependencies
        story_service._get_story_mapping = Mock(return_value=None)
        story_service._add_issue_to_project_board = Mock()
        story_service._create_story_mapping_record = Mock()
        wiki_service._get_wiki_page = Mock(return_value=None)
        wiki_service._update_epic_story_references = Mock()
        
        # Execute workflow
        story_result = story_service.sync_story_to_issue(sample_story_data, sample_epic_data)
        wiki_result = wiki_service.sync_story_documentation(sample_story_data, sample_epic_data)
        
        # Verify results
        assert story_result.status == 'created'
        assert wiki_result.status == 'created'
        assert mock_github_client.create_issue.called
        assert mock_github_client.create_or_update_wiki_page.called
    
    def test_error_handling_github_api_failure(self, mock_config, mock_github_client, sample_epic_data):
        """Test error handling when GitHub API fails"""
        mock_github_client.create_project.side_effect = Exception("API Error")
        
        epic_service = EpicMappingService(mock_config, mock_github_client)
        epic_service._get_epic_mapping = Mock(return_value=None)
        
        result = epic_service.sync_epic_to_project(sample_epic_data)
        
        assert result.status == 'error'
        assert "API Error" in result.message


class TestWebhookHandling:
    """Test webhook event processing"""
    
    def test_webhook_signature_verification(self, mock_github_client):
        """Test webhook signature verification"""
        payload = b'{"test": "data"}'
        secret = "test_secret"
        signature = "sha256=valid_signature"
        
        # Mock successful verification
        mock_github_client.verify_webhook_signature.return_value = True
        
        result = mock_github_client.verify_webhook_signature(payload, signature, secret)
        assert result is True
    
    def test_webhook_signature_verification_failure(self, mock_github_client):
        """Test webhook signature verification failure"""
        payload = b'{"test": "data"}'
        secret = "test_secret"
        signature = "sha256=invalid_signature"
        
        # Mock failed verification
        mock_github_client.verify_webhook_signature.return_value = False
        
        result = mock_github_client.verify_webhook_signature(payload, signature, secret)
        assert result is False


# Test utilities and fixtures for integration testing
@pytest.fixture
def integration_test_data():
    """Complete test data for integration scenarios"""
    return {
        "epics": [
            {
                "id": "epic_auth",
                "name": "Authentication System",
                "description": "User authentication and authorization",
                "current_phase": "build",
                "status": "active"
            },
            {
                "id": "epic_dashboard",
                "name": "User Dashboard",
                "description": "Main user interface dashboard",
                "current_phase": "measure",
                "status": "active"
            }
        ],
        "stories": [
            {
                "id": "story_login",
                "title": "Login Form",
                "description": "User login functionality",
                "epic_id": "epic_auth",
                "current_phase": "build",
                "status": "in_progress"
            },
            {
                "id": "story_register",
                "title": "Registration Form",
                "description": "User registration functionality",
                "epic_id": "epic_auth",
                "current_phase": "build",
                "status": "pending"
            }
        ]
    }


def test_integration_with_real_data(mock_config, mock_github_client, integration_test_data):
    """Test integration with realistic data set"""
    # This test would simulate a complete integration scenario
    # with multiple epics and stories
    
    epic_service = EpicMappingService(mock_config, mock_github_client)
    story_service = StoryMappingService(mock_config, mock_github_client)
    wiki_service = WikiIntegrationService(mock_config, mock_github_client)
    
    # Mock all database operations
    epic_service._get_epic_mapping = Mock(return_value=None)
    epic_service._setup_project_columns = Mock(return_value=[])
    epic_service._create_epic_mapping_record = Mock()
    
    story_service._get_story_mapping = Mock(return_value=None)
    story_service._add_issue_to_project_board = Mock()
    story_service._create_story_mapping_record = Mock()
    
    wiki_service._get_wiki_page = Mock(return_value=None)
    wiki_service._update_index_page = Mock()
    wiki_service._update_epic_story_references = Mock()
    
    results = []
    
    # Process all epics
    for epic in integration_test_data["epics"]:
        epic_result = epic_service.sync_epic_to_project(epic)
        wiki_result = wiki_service.sync_epic_documentation(epic)
        results.extend([epic_result, wiki_result])
    
    # Process all stories
    for story in integration_test_data["stories"]:
        # Find parent epic
        epic = next(e for e in integration_test_data["epics"] if e["id"] == story["epic_id"])
        
        story_result = story_service.sync_story_to_issue(story, epic)
        wiki_result = wiki_service.sync_story_documentation(story, epic)
        results.extend([story_result, wiki_result])
    
    # Verify all operations succeeded
    assert all(r.status in ['created', 'updated', 'synced'] for r in results)
    assert len(results) == 8  # 2 epics * 2 operations + 2 stories * 2 operations