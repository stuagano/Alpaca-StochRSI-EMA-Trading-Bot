"""
GitHub Integration Module for BMAD Methodology

This module provides integration between BMAD (Build, Measure, Analyze, Document) 
methodology and GitHub Projects/Wikis for enhanced project management and documentation.

Core Features:
- GitHub Projects ↔ BMAD Epics mapping
- GitHub Issues ↔ BMAD Stories mapping  
- GitHub Wikis integration for documentation
- Real-time synchronization via webhooks
- Comprehensive configuration and monitoring
"""

__version__ = "1.0.0"
__author__ = "BMAD Integration Team"

from .github_api_client import GitHubAPIClient
from .sync_service import GitHubSyncService
from .models import GitHubProject, GitHubIssue, GitHubWiki, BMadEpicMapping, BMadStoryMapping

__all__ = [
    "GitHubAPIClient",
    "GitHubSyncService", 
    "GitHubProject",
    "GitHubIssue",
    "GitHubWiki",
    "BMadEpicMapping",
    "BMadStoryMapping"
]