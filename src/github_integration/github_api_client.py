"""
GitHub API client for BMAD integration.
Provides a comprehensive interface to GitHub REST and GraphQL APIs.
"""

import json
import time
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class GitHubAPIError(Exception):
    """Base exception for GitHub API errors."""
    pass


class GitHubAuthenticationError(GitHubAPIError):
    """GitHub authentication error."""
    pass


class GitHubRateLimitError(GitHubAPIError):
    """GitHub rate limit exceeded error."""
    pass


class GitHubNotFoundError(GitHubAPIError):
    """GitHub resource not found error."""
    pass


@dataclass
class RateLimit:
    """GitHub API rate limit information."""
    limit: int
    remaining: int
    reset_time: datetime
    used: int


@dataclass
class GitHubRepository:
    """GitHub repository information."""
    owner: str
    name: str
    full_name: str
    private: bool
    html_url: str
    default_branch: str


@dataclass
class GitHubProject:
    """GitHub project information."""
    id: str
    number: int
    title: str
    body: str
    state: str
    html_url: str
    created_at: datetime
    updated_at: datetime


@dataclass
class GitHubIssue:
    """GitHub issue information."""
    id: str
    number: int
    title: str
    body: str
    state: str
    html_url: str
    labels: List[str]
    assignees: List[str]
    milestone: Optional[str]
    created_at: datetime
    updated_at: datetime


class GitHubAPIClient:
    """
    Comprehensive GitHub API client for BMAD integration.
    Supports both REST and GraphQL APIs with rate limiting and error handling.
    """
    
    BASE_URL = "https://api.github.com"
    GRAPHQL_URL = "https://api.github.com/graphql"
    
    def __init__(self, token: str, user_agent: str = "BMAD-GitHub-Integration/1.0"):
        """
        Initialize GitHub API client.
        
        Args:
            token: GitHub personal access token or app token
            user_agent: User agent string for API requests
        """
        self.token = token
        self.user_agent = user_agent
        self.logger = logging.getLogger(__name__)
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PATCH", "PUT"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "User-Agent": self.user_agent,
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        })
        
        # Rate limit tracking
        self._rate_limits = {}
        self._last_rate_limit_check = {}
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make a request to GitHub API with error handling and rate limiting.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object
            
        Raises:
            GitHubAPIError: For various API errors
        """
        try:
            # Check rate limits before making request
            self._check_rate_limits()
            
            response = self.session.request(method, url, **kwargs)
            
            # Update rate limit info
            self._update_rate_limits(response)
            
            # Handle rate limiting
            if response.status_code == 429:
                reset_time = int(response.headers.get('X-RateLimit-Reset', time.time() + 3600))
                wait_time = reset_time - int(time.time()) + 1
                raise GitHubRateLimitError(f"Rate limit exceeded. Reset at {reset_time}. Wait {wait_time} seconds.")
            
            # Handle authentication errors
            if response.status_code == 401:
                raise GitHubAuthenticationError("Invalid or expired GitHub token")
            
            # Handle forbidden errors
            if response.status_code == 403:
                error_msg = response.json().get('message', 'Forbidden')
                if 'rate limit' in error_msg.lower():
                    raise GitHubRateLimitError(error_msg)
                raise GitHubAPIError(f"Forbidden: {error_msg}")
            
            # Handle not found errors
            if response.status_code == 404:
                raise GitHubNotFoundError("Resource not found")
            
            # Handle validation errors
            if response.status_code == 422:
                error_data = response.json()
                raise GitHubAPIError(f"Validation error: {error_data}")
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            return response
            
        except requests.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise GitHubAPIError(f"Request failed: {e}")
    
    def _check_rate_limits(self):
        """Check if we're approaching rate limits."""
        current_time = time.time()
        
        for api_type, limit_info in self._rate_limits.items():
            if limit_info['remaining'] < 100:  # Conservative threshold
                reset_time = limit_info['reset_time'].timestamp()
                if current_time < reset_time:
                    wait_time = reset_time - current_time + 1
                    self.logger.warning(f"Approaching {api_type} rate limit. Waiting {wait_time} seconds.")
                    time.sleep(wait_time)
    
    def _update_rate_limits(self, response: requests.Response):
        """Update rate limit information from response headers."""
        headers = response.headers
        
        # Core API rate limits
        if 'X-RateLimit-Limit' in headers:
            self._rate_limits['core'] = {
                'limit': int(headers['X-RateLimit-Limit']),
                'remaining': int(headers['X-RateLimit-Remaining']),
                'reset_time': datetime.fromtimestamp(int(headers['X-RateLimit-Reset'])),
                'used': int(headers.get('X-RateLimit-Used', 0))
            }
        
        # Search API rate limits
        if 'X-RateLimit-Resource' in headers and headers['X-RateLimit-Resource'] == 'search':
            self._rate_limits['search'] = {
                'limit': int(headers['X-RateLimit-Limit']),
                'remaining': int(headers['X-RateLimit-Remaining']),
                'reset_time': datetime.fromtimestamp(int(headers['X-RateLimit-Reset']))
            }
    
    def get_rate_limits(self) -> Dict[str, RateLimit]:
        """Get current rate limit information."""
        url = f"{self.BASE_URL}/rate_limit"
        response = self._make_request("GET", url)
        data = response.json()
        
        rate_limits = {}
        for resource, info in data['resources'].items():
            rate_limits[resource] = RateLimit(
                limit=info['limit'],
                remaining=info['remaining'],
                reset_time=datetime.fromtimestamp(info['reset']),
                used=info['used']
            )
        
        return rate_limits
    
    def get_authenticated_user(self) -> Dict[str, Any]:
        """Get information about the authenticated user."""
        url = f"{self.BASE_URL}/user"
        response = self._make_request("GET", url)
        return response.json()
    
    def get_repository(self, owner: str, repo: str) -> GitHubRepository:
        """
        Get repository information.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            GitHubRepository object
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        response = self._make_request("GET", url)
        data = response.json()
        
        return GitHubRepository(
            owner=data['owner']['login'],
            name=data['name'],
            full_name=data['full_name'],
            private=data['private'],
            html_url=data['html_url'],
            default_branch=data['default_branch']
        )
    
    def list_repository_issues(self, owner: str, repo: str, 
                             state: str = "open", 
                             labels: Optional[List[str]] = None,
                             page: int = 1, 
                             per_page: int = 30) -> List[GitHubIssue]:
        """
        List repository issues.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            labels: Filter by labels
            page: Page number
            per_page: Items per page
            
        Returns:
            List of GitHubIssue objects
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
        params = {
            "state": state,
            "page": page,
            "per_page": per_page
        }
        
        if labels:
            params["labels"] = ",".join(labels)
        
        response = self._make_request("GET", url, params=params)
        data = response.json()
        
        issues = []
        for item in data:
            # Skip pull requests (they appear in issues API)
            if 'pull_request' in item:
                continue
                
            issues.append(GitHubIssue(
                id=str(item['id']),
                number=item['number'],
                title=item['title'],
                body=item['body'] or "",
                state=item['state'],
                html_url=item['html_url'],
                labels=[label['name'] for label in item['labels']],
                assignees=[assignee['login'] for assignee in item['assignees']],
                milestone=item['milestone']['title'] if item['milestone'] else None,
                created_at=datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(item['updated_at'].replace('Z', '+00:00'))
            ))
        
        return issues
    
    def create_issue(self, owner: str, repo: str, title: str, body: str = "",
                    labels: Optional[List[str]] = None,
                    assignees: Optional[List[str]] = None,
                    milestone: Optional[int] = None) -> GitHubIssue:
        """
        Create a new issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body
            labels: Issue labels
            assignees: Issue assignees
            milestone: Milestone number
            
        Returns:
            Created GitHubIssue object
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues"
        data = {
            "title": title,
            "body": body
        }
        
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        if milestone:
            data["milestone"] = milestone
        
        response = self._make_request("POST", url, json=data)
        item = response.json()
        
        return GitHubIssue(
            id=str(item['id']),
            number=item['number'],
            title=item['title'],
            body=item['body'] or "",
            state=item['state'],
            html_url=item['html_url'],
            labels=[label['name'] for label in item['labels']],
            assignees=[assignee['login'] for assignee in item['assignees']],
            milestone=item['milestone']['title'] if item['milestone'] else None,
            created_at=datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(item['updated_at'].replace('Z', '+00:00'))
        )
    
    def update_issue(self, owner: str, repo: str, issue_number: int,
                    title: Optional[str] = None,
                    body: Optional[str] = None,
                    state: Optional[str] = None,
                    labels: Optional[List[str]] = None,
                    assignees: Optional[List[str]] = None,
                    milestone: Optional[int] = None) -> GitHubIssue:
        """
        Update an existing issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            title: New title
            body: New body
            state: New state (open, closed)
            labels: New labels
            assignees: New assignees
            milestone: New milestone number
            
        Returns:
            Updated GitHubIssue object
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{issue_number}"
        data = {}
        
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None:
            data["state"] = state
        if labels is not None:
            data["labels"] = labels
        if assignees is not None:
            data["assignees"] = assignees
        if milestone is not None:
            data["milestone"] = milestone
        
        response = self._make_request("PATCH", url, json=data)
        item = response.json()
        
        return GitHubIssue(
            id=str(item['id']),
            number=item['number'],
            title=item['title'],
            body=item['body'] or "",
            state=item['state'],
            html_url=item['html_url'],
            labels=[label['name'] for label in item['labels']],
            assignees=[assignee['login'] for assignee in item['assignees']],
            milestone=item['milestone']['title'] if item['milestone'] else None,
            created_at=datetime.fromisoformat(item['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(item['updated_at'].replace('Z', '+00:00'))
        )
    
    def list_user_projects(self, state: str = "open", page: int = 1, per_page: int = 30) -> List[GitHubProject]:
        """
        List user projects (Projects v2).
        
        Args:
            state: Project state (open, closed, all)
            page: Page number
            per_page: Items per page
            
        Returns:
            List of GitHubProject objects
        """
        # Use GraphQL for Projects v2
        query = """
        query($first: Int!, $after: String, $states: [ProjectV2State!]) {
            viewer {
                projectsV2(first: $first, after: $after, states: $states) {
                    nodes {
                        id
                        number
                        title
                        shortDescription
                        readme
                        url
                        public
                        closed
                        createdAt
                        updatedAt
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
        }
        """
        
        variables = {
            "first": per_page,
            "states": [state.upper()] if state != "all" else None
        }
        
        response = self._make_graphql_request(query, variables)
        data = response['data']['viewer']['projectsV2']['nodes']
        
        projects = []
        for item in data:
            projects.append(GitHubProject(
                id=item['id'],
                number=item['number'],
                title=item['title'],
                body=item['shortDescription'] or "",
                state="open" if not item['closed'] else "closed",
                html_url=item['url'],
                created_at=datetime.fromisoformat(item['createdAt'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(item['updatedAt'].replace('Z', '+00:00'))
            ))
        
        return projects
    
    def create_project(self, owner: str, title: str, body: str = "", template: str = "basic") -> GitHubProject:
        """
        Create a new project (Projects v2).
        
        Args:
            owner: Project owner
            title: Project title
            body: Project description
            template: Project template
            
        Returns:
            Created GitHubProject object
        """
        # Use GraphQL for Projects v2
        mutation = """
        mutation($ownerId: ID!, $title: String!, $body: String) {
            createProjectV2(input: {ownerId: $ownerId, title: $title, shortDescription: $body}) {
                projectV2 {
                    id
                    number
                    title
                    shortDescription
                    url
                    public
                    closed
                    createdAt
                    updatedAt
                }
            }
        }
        """
        
        # Get owner ID
        owner_id = self._get_user_id(owner)
        
        variables = {
            "ownerId": owner_id,
            "title": title,
            "body": body
        }
        
        response = self._make_graphql_request(mutation, variables)
        item = response['data']['createProjectV2']['projectV2']
        
        return GitHubProject(
            id=item['id'],
            number=item['number'],
            title=item['title'],
            body=item['shortDescription'] or "",
            state="open" if not item['closed'] else "closed",
            html_url=item['url'],
            created_at=datetime.fromisoformat(item['createdAt'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(item['updatedAt'].replace('Z', '+00:00'))
        )
    
    def _make_graphql_request(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a GraphQL request to GitHub API.
        
        Args:
            query: GraphQL query string
            variables: Query variables
            
        Returns:
            Response data
        """
        headers = {
            "Accept": "application/vnd.github.v4+json"
        }
        
        data = {
            "query": query,
            "variables": variables
        }
        
        response = self._make_request("POST", self.GRAPHQL_URL, json=data, headers=headers)
        result = response.json()
        
        if 'errors' in result:
            raise GitHubAPIError(f"GraphQL errors: {result['errors']}")
        
        return result
    
    def _get_user_id(self, username: str) -> str:
        """Get GitHub user ID from username."""
        url = f"{self.BASE_URL}/users/{username}"
        response = self._make_request("GET", url)
        data = response.json()
        return data['node_id']
    
    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """
        Verify GitHub webhook signature.
        
        Args:
            payload: Webhook payload
            signature: GitHub signature header
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # GitHub sends signature with 'sha256=' prefix
        provided_signature = signature.replace('sha256=', '')
        
        return hmac.compare_digest(expected_signature, provided_signature)
    
    def create_webhook(self, owner: str, repo: str, url: str, secret: str, events: List[str]) -> Dict[str, Any]:
        """
        Create a repository webhook.
        
        Args:
            owner: Repository owner
            repo: Repository name
            url: Webhook URL
            secret: Webhook secret
            events: List of events to subscribe to
            
        Returns:
            Webhook data
        """
        api_url = f"{self.BASE_URL}/repos/{owner}/{repo}/hooks"
        data = {
            "config": {
                "url": url,
                "content_type": "json",
                "secret": secret
            },
            "events": events,
            "active": True
        }
        
        response = self._make_request("POST", api_url, json=data)
        return response.json()
    
    def list_milestones(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """List repository milestones."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/milestones"
        params = {"state": state}
        
        response = self._make_request("GET", url, params=params)
        return response.json()
    
    def create_milestone(self, owner: str, repo: str, title: str, 
                        description: str = "", due_on: Optional[str] = None) -> Dict[str, Any]:
        """Create a new milestone."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/milestones"
        data = {
            "title": title,
            "description": description
        }
        
        if due_on:
            data["due_on"] = due_on
        
        response = self._make_request("POST", url, json=data)
        return response.json()
    
    def create_status_check(self, owner: str, repo: str, sha: str, 
                           state: str, context: str, description: str,
                           target_url: Optional[str] = None) -> Dict[str, Any]:
        """Create a status check on a commit."""
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/statuses/{sha}"
        data = {
            "state": state,  # pending, success, error, failure
            "context": context,
            "description": description
        }
        
        if target_url:
            data["target_url"] = target_url
        
        response = self._make_request("POST", url, json=data)
        return response.json()


def create_github_client(token: str) -> GitHubAPIClient:
    """Create a configured GitHub API client."""
    return GitHubAPIClient(token)