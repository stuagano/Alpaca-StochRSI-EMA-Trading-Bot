"""
GitHub synchronization service for BMAD methodology.
Handles bidirectional sync between BMAD concepts and GitHub entities.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import (
    GitHubEpicMapping, GitHubStoryMapping, GitHubSyncLog,
    GitHubWebhookEvent, GitHubMilestone, SyncStatus, EntityType, OperationType
)
from .github_api_client import GitHubAPIClient, GitHubAPIError, GitHubRateLimitError


class SyncDirection(Enum):
    """Synchronization direction."""
    BMAD_TO_GITHUB = "bmad_to_github"
    GITHUB_TO_BMAD = "github_to_bmad"
    BIDIRECTIONAL = "bidirectional"


class SyncResult(Enum):
    """Synchronization result status."""
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    RATE_LIMITED = "rate_limited"


@dataclass
class SyncOperation:
    """Represents a synchronization operation."""
    entity_type: EntityType
    entity_id: str
    operation_type: OperationType
    direction: SyncDirection
    priority: int = 5  # 1-10, higher is more important
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class SyncStats:
    """Synchronization statistics."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    skipped_operations: int = 0
    rate_limited_operations: int = 0
    start_time: datetime = None
    end_time: datetime = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100
    
    @property
    def duration(self) -> timedelta:
        """Calculate sync duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return timedelta(0)


class GitHubSyncService:
    """
    Comprehensive synchronization service between BMAD and GitHub.
    Handles epics/projects, stories/issues, and wiki documentation sync.
    """
    
    def __init__(self, github_client: GitHubAPIClient, db_session: Session, config: Dict[str, Any]):
        """
        Initialize sync service.
        
        Args:
            github_client: GitHub API client
            db_session: Database session
            config: Configuration dictionary
        """
        self.github = github_client
        self.db = db_session
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Sync configuration
        self.batch_size = config.get('batch_size', 20)
        self.auto_sync = config.get('auto_sync', True)
        self.sync_interval = config.get('sync_interval', 300)  # 5 minutes
        
        # Repository info
        self.repo_owner = config['repository']['owner']
        self.repo_name = config['repository']['name']
        
        # Mapping configuration
        self.epic_mapping_config = config.get('mapping', {}).get('epic_to_project', {})
        self.story_mapping_config = config.get('mapping', {}).get('story_to_issue', {})
        
        # Operation queue
        self.sync_queue: List[SyncOperation] = []
        self.is_syncing = False
    
    def sync_epic_to_project(self, epic_id: str, epic_data: Dict[str, Any]) -> Tuple[SyncResult, Optional[str]]:
        """
        Sync a BMAD epic to GitHub project.
        
        Args:
            epic_id: BMAD epic identifier
            epic_data: Epic data dictionary
            
        Returns:
            Tuple of (sync_result, error_message)
        """
        try:
            # Check if mapping already exists
            mapping = self.db.query(GitHubEpicMapping).filter_by(bmad_epic_id=epic_id).first()
            
            if mapping and mapping.sync_status == SyncStatus.ACTIVE.value:
                # Update existing project
                return self._update_github_project(mapping, epic_data)
            else:
                # Create new project
                return self._create_github_project(epic_id, epic_data)
        
        except GitHubRateLimitError as e:
            self.logger.warning(f"Rate limited while syncing epic {epic_id}: {e}")
            return SyncResult.RATE_LIMITED, str(e)
        
        except GitHubAPIError as e:
            self.logger.error(f"GitHub API error syncing epic {epic_id}: {e}")
            self._log_sync_operation(OperationType.SYNC, EntityType.EPIC, epic_id, 
                                   status="error", error_message=str(e))
            return SyncResult.ERROR, str(e)
        
        except Exception as e:
            self.logger.error(f"Unexpected error syncing epic {epic_id}: {e}")
            return SyncResult.ERROR, str(e)
    
    def _create_github_project(self, epic_id: str, epic_data: Dict[str, Any]) -> Tuple[SyncResult, Optional[str]]:
        """Create a new GitHub project for an epic."""
        if not self.epic_mapping_config.get('auto_create', True):
            return SyncResult.SKIPPED, "Auto-create disabled for epics"
        
        # Generate project title and description
        title_pattern = self.epic_mapping_config.get('naming_pattern', 'Epic: {epic_name}')
        title = title_pattern.format(epic_name=epic_data.get('name', epic_id))
        
        desc_pattern = self.epic_mapping_config.get('description_template', 
                                                   'BMAD Epic: {epic_description}')
        description = desc_pattern.format(
            epic_description=epic_data.get('description', ''),
            epic_name=epic_data.get('name', epic_id)
        )
        
        # Create project via GitHub API
        project = self.github.create_project(
            owner=self.repo_owner,
            title=title,
            body=description
        )
        
        # Create database mapping
        mapping = GitHubEpicMapping(
            bmad_epic_id=epic_id,
            github_project_id=project.id,
            github_project_number=project.number,
            repository_owner=self.repo_owner,
            repository_name=self.repo_name,
            project_url=project.html_url,
            sync_status=SyncStatus.ACTIVE.value,
            last_synced=datetime.utcnow(),
            sync_metadata=epic_data
        )
        
        self.db.add(mapping)
        self.db.commit()
        
        # Log operation
        self._log_sync_operation(OperationType.CREATE, EntityType.EPIC, epic_id,
                               github_entity_id=project.id, status="success")
        
        self.logger.info(f"Created GitHub project {project.number} for epic {epic_id}")
        return SyncResult.SUCCESS, None
    
    def _update_github_project(self, mapping: GitHubEpicMapping, epic_data: Dict[str, Any]) -> Tuple[SyncResult, Optional[str]]:
        """Update an existing GitHub project."""
        # For now, we'll skip updates to avoid complexity with Projects v2 API
        # This can be enhanced later with GraphQL mutations
        mapping.last_synced = datetime.utcnow()
        mapping.sync_metadata = epic_data
        self.db.commit()
        
        self._log_sync_operation(OperationType.UPDATE, EntityType.EPIC, mapping.bmad_epic_id,
                               github_entity_id=mapping.github_project_id, status="success")
        
        return SyncResult.SUCCESS, None
    
    def sync_story_to_issue(self, story_id: str, story_data: Dict[str, Any], 
                           epic_id: Optional[str] = None) -> Tuple[SyncResult, Optional[str]]:
        """
        Sync a BMAD story to GitHub issue.
        
        Args:
            story_id: BMAD story identifier
            story_data: Story data dictionary
            epic_id: Associated epic ID
            
        Returns:
            Tuple of (sync_result, error_message)
        """
        try:
            # Check if mapping already exists
            mapping = self.db.query(GitHubStoryMapping).filter_by(bmad_story_id=story_id).first()
            
            if mapping and mapping.sync_status == SyncStatus.ACTIVE.value:
                # Update existing issue
                return self._update_github_issue(mapping, story_data)
            else:
                # Create new issue
                return self._create_github_issue(story_id, story_data, epic_id)
        
        except GitHubRateLimitError as e:
            self.logger.warning(f"Rate limited while syncing story {story_id}: {e}")
            return SyncResult.RATE_LIMITED, str(e)
        
        except GitHubAPIError as e:
            self.logger.error(f"GitHub API error syncing story {story_id}: {e}")
            self._log_sync_operation(OperationType.SYNC, EntityType.STORY, story_id,
                                   status="error", error_message=str(e))
            return SyncResult.ERROR, str(e)
        
        except Exception as e:
            self.logger.error(f"Unexpected error syncing story {story_id}: {e}")
            return SyncResult.ERROR, str(e)
    
    def _create_github_issue(self, story_id: str, story_data: Dict[str, Any], 
                           epic_id: Optional[str] = None) -> Tuple[SyncResult, Optional[str]]:
        """Create a new GitHub issue for a story."""
        if not self.story_mapping_config.get('auto_create', True):
            return SyncResult.SKIPPED, "Auto-create disabled for stories"
        
        # Prepare issue data
        title = story_data.get('title', f"Story: {story_id}")
        body = self._format_story_body(story_data)
        labels = self._get_story_labels(story_data)
        assignees = self._get_story_assignees(story_data)
        
        # Get milestone if epic mapping exists
        milestone_number = None
        if epic_id:
            milestone_number = self._get_or_create_milestone(epic_id, story_data.get('phase'))
        
        # Create issue via GitHub API
        issue = self.github.create_issue(
            owner=self.repo_owner,
            repo=self.repo_name,
            title=title,
            body=body,
            labels=labels,
            assignees=assignees,
            milestone=milestone_number
        )
        
        # Get epic mapping ID if available
        epic_mapping_id = None
        if epic_id:
            epic_mapping = self.db.query(GitHubEpicMapping).filter_by(bmad_epic_id=epic_id).first()
            if epic_mapping:
                epic_mapping_id = epic_mapping.id
        
        # Create database mapping
        mapping = GitHubStoryMapping(
            bmad_story_id=story_id,
            github_issue_id=issue.id,
            github_issue_number=issue.number,
            repository_owner=self.repo_owner,
            repository_name=self.repo_name,
            issue_url=issue.html_url,
            epic_mapping_id=epic_mapping_id,
            sync_status=SyncStatus.ACTIVE.value,
            last_synced=datetime.utcnow(),
            current_phase=story_data.get('phase'),
            labels=labels,
            assignees=assignees,
            milestone_id=str(milestone_number) if milestone_number else None
        )
        
        self.db.add(mapping)
        self.db.commit()
        
        # Log operation
        self._log_sync_operation(OperationType.CREATE, EntityType.STORY, story_id,
                               github_entity_id=issue.id, status="success")
        
        self.logger.info(f"Created GitHub issue #{issue.number} for story {story_id}")
        return SyncResult.SUCCESS, None
    
    def _update_github_issue(self, mapping: GitHubStoryMapping, story_data: Dict[str, Any]) -> Tuple[SyncResult, Optional[str]]:
        """Update an existing GitHub issue."""
        # Prepare update data
        title = story_data.get('title')
        body = self._format_story_body(story_data)
        labels = self._get_story_labels(story_data)
        assignees = self._get_story_assignees(story_data)
        state = "closed" if story_data.get('status') == 'done' else "open"
        
        # Update issue via GitHub API
        issue = self.github.update_issue(
            owner=self.repo_owner,
            repo=self.repo_name,
            issue_number=mapping.github_issue_number,
            title=title,
            body=body,
            state=state,
            labels=labels,
            assignees=assignees
        )
        
        # Update mapping
        mapping.last_synced = datetime.utcnow()
        mapping.current_phase = story_data.get('phase')
        mapping.labels = labels
        mapping.assignees = assignees
        self.db.commit()
        
        # Log operation
        self._log_sync_operation(OperationType.UPDATE, EntityType.STORY, mapping.bmad_story_id,
                               github_entity_id=mapping.github_issue_id, status="success")
        
        return SyncResult.SUCCESS, None
    
    def _format_story_body(self, story_data: Dict[str, Any]) -> str:
        """Format story data into GitHub issue body."""
        body_parts = []
        
        # Description
        if story_data.get('description'):
            body_parts.append(f"## Description\\n{story_data['description']}")
        
        # Acceptance criteria
        if story_data.get('acceptance_criteria'):
            body_parts.append("## Acceptance Criteria")
            for criterion in story_data['acceptance_criteria']:
                body_parts.append(f"- [ ] {criterion}")
        
        # BMAD phase information
        if story_data.get('phase'):
            body_parts.append(f"## BMAD Phase\\n**Current Phase:** {story_data['phase'].title()}")
        
        # Additional metadata
        if story_data.get('priority'):
            body_parts.append(f"**Priority:** {story_data['priority']}")
        
        if story_data.get('story_points'):
            body_parts.append(f"**Story Points:** {story_data['story_points']}")
        
        # BMAD footer
        body_parts.append("---")
        body_parts.append("*This issue was created and is managed by BMAD methodology.*")
        
        return "\\n\\n".join(body_parts)
    
    def _get_story_labels(self, story_data: Dict[str, Any]) -> List[str]:
        """Get GitHub labels for a story based on configuration."""
        labels = []
        label_mapping = self.story_mapping_config.get('label_mapping', {})
        
        # Add story label
        if label_mapping.get('story'):
            labels.append(label_mapping['story'])
        
        # Add phase label
        phase = story_data.get('phase')
        if phase and label_mapping.get(phase):
            labels.append(label_mapping[phase])
        
        # Add priority label
        priority = story_data.get('priority')
        if priority:
            labels.append(f"priority:{priority}")
        
        # Add custom labels
        if story_data.get('labels'):
            labels.extend(story_data['labels'])
        
        return labels
    
    def _get_story_assignees(self, story_data: Dict[str, Any]) -> List[str]:
        """Get GitHub assignees for a story based on configuration."""
        assignees = []
        assignee_mapping = self.story_mapping_config.get('assignee_mapping', {})
        
        # Map BMAD roles to GitHub usernames
        if story_data.get('assigned_to'):
            github_user = assignee_mapping.get(story_data['assigned_to'])
            if github_user:
                assignees.append(github_user)
        
        # Add custom assignees
        if story_data.get('assignees'):
            assignees.extend(story_data['assignees'])
        
        return assignees
    
    def _get_or_create_milestone(self, epic_id: str, phase: Optional[str] = None) -> Optional[int]:
        """Get or create a GitHub milestone for an epic phase."""
        if not phase:
            return None
        
        # Check if milestone mapping exists
        milestone_mapping = self.db.query(GitHubMilestone).filter_by(
            bmad_epic_id=epic_id,
            bmad_phase=phase
        ).first()
        
        if milestone_mapping:
            return milestone_mapping.github_milestone_number
        
        # Create new milestone
        try:
            pattern = self.config.get('mapping', {}).get('phase_to_milestone', {}).get('naming_pattern', 
                                                                                      '{epic_id} - {phase_name}')
            title = pattern.format(epic_id=epic_id, phase_name=phase.title())
            description = f"BMAD {phase.title()} phase for epic {epic_id}"
            
            milestone = self.github.create_milestone(
                owner=self.repo_owner,
                repo=self.repo_name,
                title=title,
                description=description
            )
            
            # Save mapping
            milestone_mapping = GitHubMilestone(
                bmad_epic_id=epic_id,
                bmad_phase=phase,
                github_milestone_id=str(milestone['id']),
                github_milestone_number=milestone['number'],
                repository_owner=self.repo_owner,
                repository_name=self.repo_name,
                milestone_url=milestone['html_url'],
                title=milestone['title'],
                description=milestone['description']
            )
            
            self.db.add(milestone_mapping)
            self.db.commit()
            
            return milestone['number']
        
        except GitHubAPIError as e:
            self.logger.error(f"Failed to create milestone for epic {epic_id}, phase {phase}: {e}")
            return None
    
    def process_webhook_event(self, event: GitHubWebhookEvent) -> bool:
        """
        Process a GitHub webhook event.
        
        Args:
            event: Webhook event to process
            
        Returns:
            True if processed successfully
        """
        try:
            payload = event.payload
            event_type = event.event_type
            action = event.action
            
            if event_type == "issues":
                return self._process_issue_webhook(payload, action)
            elif event_type == "projects_v2":
                return self._process_project_webhook(payload, action)
            else:
                self.logger.info(f"Ignoring webhook event type: {event_type}")
                return True
        
        except Exception as e:
            self.logger.error(f"Error processing webhook event {event.id}: {e}")
            event.error_message = str(e)
            self.db.commit()
            return False
    
    def _process_issue_webhook(self, payload: Dict[str, Any], action: str) -> bool:
        """Process GitHub issue webhook events."""
        issue_data = payload.get('issue', {})
        issue_id = str(issue_data.get('id'))
        issue_number = issue_data.get('number')
        
        # Find corresponding story mapping
        mapping = self.db.query(GitHubStoryMapping).filter_by(github_issue_id=issue_id).first()
        
        if not mapping:
            self.logger.info(f"No mapping found for GitHub issue #{issue_number}")
            return True
        
        # Update mapping based on action
        if action in ["edited", "labeled", "unlabeled", "assigned", "unassigned"]:
            mapping.labels = [label['name'] for label in issue_data.get('labels', [])]
            mapping.assignees = [assignee['login'] for assignee in issue_data.get('assignees', [])]
            mapping.last_synced = datetime.utcnow()
            
            # Log the sync
            self._log_sync_operation(OperationType.WEBHOOK, EntityType.STORY, mapping.bmad_story_id,
                                   github_entity_id=issue_id, status="success",
                                   response_data={"action": action, "issue_number": issue_number})
        
        elif action == "closed":
            # Mark story as completed in BMAD
            self.logger.info(f"GitHub issue #{issue_number} closed, story {mapping.bmad_story_id} should be marked complete")
            # Callback to BMAD system to mark story complete
            self._mark_bmad_story_complete(mapping.bmad_story_id)
        
        self.db.commit()
        return True
    
    def _process_project_webhook(self, payload: Dict[str, Any], action: str) -> bool:
        """Process GitHub project webhook events."""
        project_data = payload.get('projects_v2', {})
        project_id = project_data.get('id')
        
        # Find corresponding epic mapping
        mapping = self.db.query(GitHubEpicMapping).filter_by(github_project_id=project_id).first()
        
        if not mapping:
            self.logger.info(f"No mapping found for GitHub project {project_id}")
            return True
        
        # Update mapping
        if action in ["edited", "reopened", "closed"]:
            mapping.last_synced = datetime.utcnow()
            
            # Log the sync
            self._log_sync_operation(OperationType.WEBHOOK, EntityType.EPIC, mapping.bmad_epic_id,
                                   github_entity_id=project_id, status="success",
                                   response_data={"action": action})
        
        self.db.commit()
        return True
    
    def sync_full(self, force: bool = False) -> SyncStats:
        """
        Perform full synchronization between BMAD and GitHub.
        
        Args:
            force: Force sync even if recently synced
            
        Returns:
            Synchronization statistics
        """
        stats = SyncStats(start_time=datetime.utcnow())
        self.logger.info("Starting full synchronization")
        
        try:
            self.is_syncing = True
            
            # Sync epics to projects
            epic_stats = self._sync_all_epics(force)
            stats.total_operations += epic_stats.total_operations
            stats.successful_operations += epic_stats.successful_operations
            stats.failed_operations += epic_stats.failed_operations
            stats.skipped_operations += epic_stats.skipped_operations
            stats.rate_limited_operations += epic_stats.rate_limited_operations
            
            # Sync stories to issues
            story_stats = self._sync_all_stories(force)
            stats.total_operations += story_stats.total_operations
            stats.successful_operations += story_stats.successful_operations
            stats.failed_operations += story_stats.failed_operations
            stats.skipped_operations += story_stats.skipped_operations
            stats.rate_limited_operations += story_stats.rate_limited_operations
            
            # Process pending webhook events
            webhook_stats = self._process_pending_webhooks()
            stats.total_operations += webhook_stats.total_operations
            stats.successful_operations += webhook_stats.successful_operations
            stats.failed_operations += webhook_stats.failed_operations
            
        finally:
            self.is_syncing = False
            stats.end_time = datetime.utcnow()
        
        self.logger.info(f"Full sync completed: {stats.successful_operations}/{stats.total_operations} successful, "
                        f"{stats.success_rate:.1f}% success rate, duration: {stats.duration}")
        
        return stats
    
    def _sync_all_epics(self, force: bool = False) -> SyncStats:
        """Sync all epics that need updating."""
        stats = SyncStats()
        
        # Get epics from BMAD system and sync existing mappings
        self._sync_bmad_epics(force)
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.sync_interval)
        
        query = self.db.query(GitHubEpicMapping).filter(
            GitHubEpicMapping.sync_status == SyncStatus.ACTIVE.value
        )
        
        if not force:
            query = query.filter(
                or_(
                    GitHubEpicMapping.last_synced.is_(None),
                    GitHubEpicMapping.last_synced < cutoff_time
                )
            )
        
        mappings = query.all()
        stats.total_operations = len(mappings)
        
        for mapping in mappings:
            try:
                # Get epic data from BMAD system
                epic_data = mapping.sync_metadata or {}
                result, error = self.sync_epic_to_project(mapping.bmad_epic_id, epic_data)
                
                if result == SyncResult.SUCCESS:
                    stats.successful_operations += 1
                elif result == SyncResult.ERROR:
                    stats.failed_operations += 1
                elif result == SyncResult.SKIPPED:
                    stats.skipped_operations += 1
                elif result == SyncResult.RATE_LIMITED:
                    stats.rate_limited_operations += 1
            
            except Exception as e:
                self.logger.error(f"Error syncing epic {mapping.bmad_epic_id}: {e}")
                stats.failed_operations += 1
        
        return stats
    
    def _sync_all_stories(self, force: bool = False) -> SyncStats:
        """Sync all stories that need updating."""
        stats = SyncStats()
        
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.sync_interval)
        
        query = self.db.query(GitHubStoryMapping).filter(
            GitHubStoryMapping.sync_status == SyncStatus.ACTIVE.value
        )
        
        if not force:
            query = query.filter(
                or_(
                    GitHubStoryMapping.last_synced.is_(None),
                    GitHubStoryMapping.last_synced < cutoff_time
                )
            )
        
        mappings = query.all()
        stats.total_operations = len(mappings)
        
        for mapping in mappings:
            try:
                # Get story data from BMAD system
                story_data = self._get_bmad_story_data(mapping.bmad_story_id)
                epic_id = None
                if mapping.epic_mapping_id:
                    epic_mapping = self.db.query(GitHubEpicMapping).get(mapping.epic_mapping_id)
                    if epic_mapping:
                        epic_id = epic_mapping.bmad_epic_id
                
                result, error = self.sync_story_to_issue(mapping.bmad_story_id, story_data, epic_id)
                
                if result == SyncResult.SUCCESS:
                    stats.successful_operations += 1
                elif result == SyncResult.ERROR:
                    stats.failed_operations += 1
                elif result == SyncResult.SKIPPED:
                    stats.skipped_operations += 1
                elif result == SyncResult.RATE_LIMITED:
                    stats.rate_limited_operations += 1
            
            except Exception as e:
                self.logger.error(f"Error syncing story {mapping.bmad_story_id}: {e}")
                stats.failed_operations += 1
        
        return stats
    
    def _process_pending_webhooks(self) -> SyncStats:
        """Process pending webhook events."""
        stats = SyncStats()
        
        # Get unprocessed webhook events from the last hour
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        events = self.db.query(GitHubWebhookEvent).filter(
            and_(
                GitHubWebhookEvent.processed == False,
                GitHubWebhookEvent.received_at >= cutoff_time
            )
        ).order_by(GitHubWebhookEvent.received_at).limit(self.batch_size).all()
        
        stats.total_operations = len(events)
        
        for event in events:
            try:
                if self.process_webhook_event(event):
                    event.processed = True
                    event.processed_at = datetime.utcnow()
                    stats.successful_operations += 1
                else:
                    stats.failed_operations += 1
            
            except Exception as e:
                self.logger.error(f"Error processing webhook event {event.id}: {e}")
                event.error_message = str(e)
                stats.failed_operations += 1
        
        self.db.commit()
        return stats
    
    def _log_sync_operation(self, operation_type: OperationType, entity_type: EntityType,
                          entity_id: str, github_entity_id: Optional[str] = None,
                          status: str = "success", error_message: Optional[str] = None,
                          response_data: Optional[Dict[str, Any]] = None,
                          duration_ms: Optional[int] = None):
        """Log a synchronization operation."""
        log_entry = GitHubSyncLog(
            operation_type=operation_type.value,
            entity_type=entity_type.value,
            entity_id=entity_id,
            github_entity_id=github_entity_id,
            status=status,
            error_message=error_message,
            response_data=response_data,
            duration_ms=duration_ms
        )
        
        self.db.add(log_entry)
        self.db.commit()
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status."""
        # Get recent sync statistics
        recent_logs = self.db.query(GitHubSyncLog).filter(
            GitHubSyncLog.sync_timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).all()
        
        total_operations = len(recent_logs)
        successful_operations = len([log for log in recent_logs if log.status == "success"])
        failed_operations = len([log for log in recent_logs if log.status == "error"])
        
        # Get mapping counts
        epic_mappings = self.db.query(GitHubEpicMapping).filter_by(
            sync_status=SyncStatus.ACTIVE.value
        ).count()
        
        story_mappings = self.db.query(GitHubStoryMapping).filter_by(
            sync_status=SyncStatus.ACTIVE.value
        ).count()
        
        # Get pending webhook events
        pending_webhooks = self.db.query(GitHubWebhookEvent).filter_by(processed=False).count()
        
        return {
            "is_syncing": self.is_syncing,
            "last_24h_stats": {
                "total_operations": total_operations,
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "success_rate": (successful_operations / total_operations * 100) if total_operations > 0 else 0
            },
            "mappings": {
                "active_epic_mappings": epic_mappings,
                "active_story_mappings": story_mappings
            },
            "pending_webhooks": pending_webhooks,
            "config": {
                "auto_sync": self.auto_sync,
                "sync_interval": self.sync_interval,
                "batch_size": self.batch_size
            }
        }
    
    def _mark_bmad_story_complete(self, story_id: str) -> bool:
        """Mark a story as complete in the BMAD system."""
        try:
            # For now, this is a stub implementation
            # In a real implementation, this would call the BMAD API
            self.logger.info(f"Marking BMAD story {story_id} as complete")
            
            # Update local tracking if needed
            mapping = self.db.query(GitHubStoryMapping).filter_by(bmad_story_id=story_id).first()
            if mapping:
                mapping.last_synced = datetime.utcnow()
                if not mapping.sync_metadata:
                    mapping.sync_metadata = {}
                mapping.sync_metadata['completed_at'] = datetime.utcnow().isoformat()
                self.db.commit()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to mark BMAD story {story_id} complete: {e}")
            return False
    
    def _sync_bmad_epics(self, force: bool = False) -> None:
        """Sync epics from BMAD system."""
        try:
            # For now, this is a stub implementation
            # In a real implementation, this would fetch epics from BMAD API
            self.logger.info("Syncing epics from BMAD system")
            
            # Example: In a real implementation, you might do:
            # epics = bmad_client.get_active_epics()
            # for epic in epics:
            #     self._ensure_epic_mapping(epic)
            
        except Exception as e:
            self.logger.error(f"Failed to sync BMAD epics: {e}")
    
    def _get_bmad_story_data(self, story_id: str) -> Dict[str, Any]:
        """Get story data from BMAD system."""
        try:
            # For now, this is a stub implementation
            # In a real implementation, this would fetch from BMAD API
            self.logger.debug(f"Fetching BMAD story data for {story_id}")
            
            # Return default structure for now
            return {
                "title": f"Story {story_id}",
                "description": f"Auto-generated description for story {story_id}",
                "status": "active",
                "priority": "medium",
                "labels": ["bmad-sync"],
                "assignees": [],
                "metadata": {
                    "bmad_story_id": story_id,
                    "sync_timestamp": datetime.utcnow().isoformat()
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to get BMAD story data for {story_id}: {e}")
            return {
                "title": f"Story {story_id}",
                "description": "Error retrieving story data from BMAD",
                "status": "error"
            }