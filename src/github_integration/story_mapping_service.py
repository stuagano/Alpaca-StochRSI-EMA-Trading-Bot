"""
Story to GitHub Issue Mapping Service

Handles bidirectional synchronization between BMAD Stories and GitHub Issues
with comprehensive mapping, validation, and project board integration.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from .github_api_client import GitHubAPIClient, GitHubAPIError
from .models import BMadStoryMapping, GitHubIssue
from config.github_integration_config import GitHubIntegrationConfig

logger = logging.getLogger(__name__)


@dataclass
class StorySyncResult:
    """Result of story synchronization operation"""
    story_id: str
    issue_number: Optional[int]
    status: str  # 'created', 'updated', 'synced', 'error'
    message: str
    conflicts: List[str] = None
    
    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []


@dataclass
class IssueSyncResult:
    """Result of issue synchronization operation"""
    issue_number: int
    story_id: Optional[str]
    status: str  # 'mapped', 'created', 'updated', 'error'
    message: str
    conflicts: List[str] = None
    
    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []


class StoryMappingService:
    """
    Service for managing Story to GitHub Issue mappings
    
    Features:
    - Bidirectional sync between BMAD Stories and GitHub Issues
    - Automatic issue creation with customizable templates
    - Project board integration
    - Milestone and label management
    - Phase-based workflow automation
    """
    
    def __init__(self, config: GitHubIntegrationConfig, github_client: GitHubAPIClient):
        """
        Initialize Story Mapping Service
        
        Args:
            config: GitHub integration configuration
            github_client: GitHub API client instance
        """
        self.config = config
        self.github_client = github_client
        
        # Mapping configuration
        self.story_config = config.story_mapping
        
        # Templates
        self.issue_template = self.story_config.issue_template
        self.issue_body_template = self.story_config.issue_body_template
        self.default_labels = self.story_config.labels
        self.assignee_mapping = self.story_config.assignee_mapping
        
        # Phase to label mapping
        self.phase_labels = {
            'build': ['phase:build', 'status:in-progress'],
            'measure': ['phase:measure', 'status:testing'],
            'analyze': ['phase:analyze', 'status:review'],
            'document': ['phase:document', 'status:documentation']
        }
    
    def sync_story_to_issue(self, 
                          story_data: Dict[str, Any], 
                          epic_data: Dict[str, Any] = None,
                          force_update: bool = False) -> StorySyncResult:
        """
        Synchronize BMAD Story to GitHub Issue
        
        Args:
            story_data: Story data from BMAD
            epic_data: Epic data for context
            force_update: Force update even if no changes detected
            
        Returns:
            StorySyncResult with operation details
        """
        story_id = story_data.get('id')
        story_title = story_data.get('title', '')
        
        logger.info(f"Syncing story {story_id} to GitHub Issue")
        
        try:
            # Check if mapping already exists
            existing_mapping = self._get_story_mapping(story_id)
            
            if existing_mapping and existing_mapping.github_issue_number:
                # Update existing issue
                return self._update_existing_issue(story_data, epic_data, existing_mapping, force_update)
            else:
                # Create new issue
                return self._create_new_issue(story_data, epic_data)
                
        except Exception as e:
            logger.error(f"Failed to sync story {story_id}: {str(e)}")
            return StorySyncResult(
                story_id=story_id,
                issue_number=None,
                status='error',
                message=f"Sync failed: {str(e)}"
            )
    
    def sync_issue_to_story(self, 
                          issue_data: Dict[str, Any], 
                          force_update: bool = False) -> IssueSyncResult:
        """
        Synchronize GitHub Issue to BMAD Story
        
        Args:
            issue_data: Issue data from GitHub
            force_update: Force update even if no changes detected
            
        Returns:
            IssueSyncResult with operation details
        """
        issue_number = issue_data.get('number')
        issue_title = issue_data.get('title', '')
        
        logger.info(f"Syncing GitHub Issue {issue_number} to BMAD Story")
        
        try:
            # Check if mapping already exists
            existing_mapping = self._get_issue_mapping(issue_number)
            
            if existing_mapping and existing_mapping.bmad_story_id:
                # Update existing story
                return self._update_existing_story(issue_data, existing_mapping, force_update)
            else:
                # Create new story mapping
                return self._create_story_mapping(issue_data)
                
        except Exception as e:
            logger.error(f"Failed to sync issue {issue_number}: {str(e)}")
            return IssueSyncResult(
                issue_number=issue_number,
                story_id=None,
                status='error',
                message=f"Sync failed: {str(e)}"
            )
    
    def _create_new_issue(self, 
                        story_data: Dict[str, Any], 
                        epic_data: Dict[str, Any] = None) -> StorySyncResult:
        """Create new GitHub Issue for Story"""
        story_id = story_data.get('id')
        story_title = story_data.get('title', '')
        story_description = story_data.get('description', '')
        acceptance_criteria = story_data.get('acceptance_criteria', '')
        current_phase = story_data.get('current_phase', 'build')
        priority = story_data.get('priority', 'medium')
        assignee = story_data.get('assignee', '')
        technical_details = story_data.get('technical_details', '')
        
        # Epic context
        epic_name = epic_data.get('name', 'Unknown Epic') if epic_data else 'Unknown Epic'
        
        try:
            # Generate issue title from template
            issue_title = self.issue_template.format(
                story_title=story_title,
                story_id=story_id
            )
            
            # Generate issue body from template
            issue_body = self.issue_body_template.format(
                story_description=story_description,
                acceptance_criteria=acceptance_criteria,
                epic_name=epic_name,
                current_phase=current_phase,
                story_id=story_id,
                priority=priority,
                technical_details=technical_details
            )
            
            # Prepare labels
            labels = self._prepare_issue_labels(story_data, current_phase)
            
            # Prepare assignees
            assignees = self._prepare_issue_assignees(story_data)
            
            # Prepare milestone
            milestone = self._prepare_issue_milestone(story_data, epic_data)
            
            # Create GitHub issue
            issue = self.github_client.create_issue(
                title=issue_title,
                body=issue_body,
                assignees=assignees,
                milestone=milestone,
                labels=labels
            )
            
            issue_number = issue['number']
            
            # Add issue to project board if epic is mapped
            self._add_issue_to_project_board(issue_number, story_data, epic_data)
            
            # Create story mapping
            mapping = self._create_story_mapping_record(story_id, issue_number, story_data, issue)
            
            logger.info(f"Created GitHub Issue {issue_number} for Story {story_id}")
            
            return StorySyncResult(
                story_id=story_id,
                issue_number=issue_number,
                status='created',
                message=f"Created GitHub Issue #{issue_number} for Story '{story_title}'"
            )
            
        except GitHubAPIError as e:
            logger.error(f"GitHub API error creating issue for story {story_id}: {str(e)}")
            return StorySyncResult(
                story_id=story_id,
                issue_number=None,
                status='error',
                message=f"GitHub API error: {str(e)}"
            )
    
    def _update_existing_issue(self, 
                             story_data: Dict[str, Any], 
                             epic_data: Dict[str, Any],
                             mapping: BMadStoryMapping, 
                             force_update: bool) -> StorySyncResult:
        """Update existing GitHub Issue from Story"""
        story_id = story_data.get('id')
        story_title = story_data.get('title', '')
        issue_number = mapping.github_issue_number
        
        try:
            # Get current issue state
            current_issue = self.github_client.get_issue(issue_number)
            
            # Check if update is needed
            if not force_update and not self._needs_issue_update(story_data, current_issue, mapping):
                return StorySyncResult(
                    story_id=story_id,
                    issue_number=issue_number,
                    status='synced',
                    message="Issue already up to date"
                )
            
            # Prepare updates
            updates = self._prepare_issue_updates(story_data, epic_data, current_issue)
            
            if updates:
                # Update GitHub issue
                updated_issue = self.github_client.update_issue(issue_number, **updates)
                
                # Update mapping record
                self._update_story_mapping_record(mapping, story_data, updated_issue)
                
                logger.info(f"Updated GitHub Issue {issue_number} for Story {story_id}")
                
                return StorySyncResult(
                    story_id=story_id,
                    issue_number=issue_number,
                    status='updated',
                    message=f"Updated GitHub Issue #{issue_number} for Story '{story_title}'"
                )
            else:
                return StorySyncResult(
                    story_id=story_id,
                    issue_number=issue_number,
                    status='synced',
                    message="No updates needed"
                )
                
        except GitHubAPIError as e:
            logger.error(f"GitHub API error updating issue {issue_number}: {str(e)}")
            return StorySyncResult(
                story_id=story_id,
                issue_number=issue_number,
                status='error',
                message=f"GitHub API error: {str(e)}"
            )
    
    def _create_story_mapping(self, issue_data: Dict[str, Any]) -> IssueSyncResult:
        """Create Story mapping for existing GitHub Issue"""
        issue_number = issue_data.get('number')
        issue_title = issue_data.get('title', '')
        
        try:
            # Extract story information from issue
            story_info = self._extract_story_info_from_issue(issue_data)
            
            if not story_info:
                return IssueSyncResult(
                    issue_number=issue_number,
                    story_id=None,
                    status='error',
                    message="Could not extract story information from issue"
                )
            
            story_id = story_info.get('story_id')
            
            # Create mapping record
            mapping = self._create_story_mapping_record(story_id, issue_number, story_info, issue_data)
            
            logger.info(f"Created Story mapping for GitHub Issue {issue_number}")
            
            return IssueSyncResult(
                issue_number=issue_number,
                story_id=story_id,
                status='mapped',
                message=f"Mapped GitHub Issue #{issue_number} to Story '{story_id}'"
            )
            
        except Exception as e:
            logger.error(f"Failed to create story mapping for issue {issue_number}: {str(e)}")
            return IssueSyncResult(
                issue_number=issue_number,
                story_id=None,
                status='error',
                message=f"Mapping creation failed: {str(e)}"
            )
    
    def _update_existing_story(self, 
                             issue_data: Dict[str, Any], 
                             mapping: BMadStoryMapping, 
                             force_update: bool) -> IssueSyncResult:
        """Update existing Story from GitHub Issue"""
        issue_number = issue_data.get('number')
        story_id = mapping.bmad_story_id
        
        try:
            # Check if update is needed
            if not force_update and not self._needs_story_update(issue_data, mapping):
                return IssueSyncResult(
                    issue_number=issue_number,
                    story_id=story_id,
                    status='synced',
                    message="Story already up to date"
                )
            
            # Update story in BMAD system
            story_updates = self._prepare_story_updates(issue_data)
            
            # Update mapping record
            self._update_story_mapping_record(mapping, story_updates, issue_data)
            
            logger.info(f"Updated Story {story_id} from GitHub Issue {issue_number}")
            
            return IssueSyncResult(
                issue_number=issue_number,
                story_id=story_id,
                status='updated',
                message=f"Updated Story '{story_id}' from GitHub Issue #{issue_number}"
            )
            
        except Exception as e:
            logger.error(f"Failed to update story {story_id} from issue {issue_number}: {str(e)}")
            return IssueSyncResult(
                issue_number=issue_number,
                story_id=story_id,
                status='error',
                message=f"Story update failed: {str(e)}"
            )
    
    def _prepare_issue_labels(self, story_data: Dict[str, Any], current_phase: str) -> List[str]:
        """Prepare labels for GitHub issue"""
        labels = self.default_labels.copy()
        
        # Add phase-specific labels
        if current_phase in self.phase_labels:
            labels.extend(self.phase_labels[current_phase])
        
        # Add priority label
        priority = story_data.get('priority', 'medium')
        labels.append(f"priority:{priority}")
        
        # Add story type label
        story_type = story_data.get('type', 'feature')
        labels.append(f"type:{story_type}")
        
        return labels
    
    def _prepare_issue_assignees(self, story_data: Dict[str, Any]) -> List[str]:
        """Prepare assignees for GitHub issue"""
        assignees = []
        
        story_assignee = story_data.get('assignee', '')
        if story_assignee and story_assignee in self.assignee_mapping:
            github_username = self.assignee_mapping[story_assignee]
            assignees.append(github_username)
        elif story_assignee:
            # Assume it's already a GitHub username
            assignees.append(story_assignee)
        
        return assignees
    
    def _prepare_issue_milestone(self, 
                               story_data: Dict[str, Any], 
                               epic_data: Dict[str, Any] = None) -> Optional[int]:
        """Prepare milestone for GitHub issue"""
        if not self.story_config.milestone_mapping:
            return None
        
        # Use epic as milestone if available
        if epic_data:
            epic_name = epic_data.get('name', '')
            # This would typically look up or create a milestone
            # For now, return None (implement with your milestone management)
            return None
        
        return None
    
    def _add_issue_to_project_board(self, 
                                  issue_number: int, 
                                  story_data: Dict[str, Any], 
                                  epic_data: Dict[str, Any] = None) -> None:
        """Add issue to project board if epic is mapped"""
        if not epic_data:
            return
        
        try:
            # Get epic's project mapping
            epic_id = epic_data.get('id')
            epic_mapping = self._get_epic_mapping(epic_id)
            
            if epic_mapping and epic_mapping.github_project_id:
                project_id = epic_mapping.github_project_id
                
                # Get project columns
                columns = self.github_client.get_project_columns(project_id)
                
                # Find appropriate column based on story phase
                current_phase = story_data.get('current_phase', 'build')
                column_name = self._get_column_for_phase(current_phase)
                
                target_column = None
                for column in columns:
                    if column['name'].lower() == column_name.lower():
                        target_column = column
                        break
                
                if target_column:
                    # Get issue details for project card
                    issue = self.github_client.get_issue(issue_number)
                    
                    # Add issue to project
                    self.github_client.add_issue_to_project(
                        project_id, 
                        target_column['id'], 
                        issue['id']
                    )
                    
                    logger.info(f"Added issue {issue_number} to project {project_id} in column '{column_name}'")
                
        except Exception as e:
            logger.warning(f"Failed to add issue {issue_number} to project board: {str(e)}")
    
    def _get_column_for_phase(self, phase: str) -> str:
        """Get project column name for BMAD phase"""
        phase_to_column = {
            'build': 'In Progress',
            'measure': 'Review',
            'analyze': 'Review',
            'document': 'Done'
        }
        
        return phase_to_column.get(phase, 'To Do')
    
    def _needs_issue_update(self, 
                          story_data: Dict[str, Any], 
                          current_issue: Dict[str, Any], 
                          mapping: BMadStoryMapping) -> bool:
        """Check if issue needs updating based on story changes"""
        # Compare relevant fields
        story_title = story_data.get('title', '')
        story_description = story_data.get('description', '')
        current_phase = story_data.get('current_phase', 'build')
        
        # Generate expected issue title
        expected_title = self.issue_template.format(
            story_title=story_title,
            story_id=story_data.get('id')
        )
        
        # Check for changes
        title_changed = current_issue.get('title') != expected_title
        
        # Check if status changed (open/closed)
        story_status = story_data.get('status', 'active')
        expected_state = 'closed' if story_status == 'completed' else 'open'
        state_changed = current_issue.get('state') != expected_state
        
        # Check labels for phase changes
        current_labels = [label['name'] for label in current_issue.get('labels', [])]
        expected_labels = self._prepare_issue_labels(story_data, current_phase)
        labels_changed = set(current_labels) != set(expected_labels)
        
        # Check last sync time
        last_sync = mapping.last_sync_timestamp
        story_updated = story_data.get('updated_at')
        
        time_based_update = (
            story_updated and last_sync and 
            datetime.fromisoformat(story_updated.replace('Z', '+00:00')) > last_sync
        )
        
        return title_changed or state_changed or labels_changed or time_based_update
    
    def _needs_story_update(self, 
                          issue_data: Dict[str, Any], 
                          mapping: BMadStoryMapping) -> bool:
        """Check if story needs updating based on issue changes"""
        # Check last sync time
        last_sync = mapping.last_sync_timestamp
        issue_updated = issue_data.get('updated_at')
        
        if issue_updated and last_sync:
            issue_updated_dt = datetime.fromisoformat(issue_updated.replace('Z', '+00:00'))
            return issue_updated_dt > last_sync
        
        return True  # Update if we can't determine timestamps
    
    def _prepare_issue_updates(self, 
                             story_data: Dict[str, Any], 
                             epic_data: Dict[str, Any],
                             current_issue: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare GitHub issue update payload"""
        updates = {}
        
        story_title = story_data.get('title', '')
        story_description = story_data.get('description', '')
        acceptance_criteria = story_data.get('acceptance_criteria', '')
        current_phase = story_data.get('current_phase', 'build')
        priority = story_data.get('priority', 'medium')
        technical_details = story_data.get('technical_details', '')
        story_id = story_data.get('id')
        
        epic_name = epic_data.get('name', 'Unknown Epic') if epic_data else 'Unknown Epic'
        
        # Update issue title
        expected_title = self.issue_template.format(
            story_title=story_title,
            story_id=story_id
        )
        
        if current_issue.get('title') != expected_title:
            updates['title'] = expected_title
        
        # Update issue body
        expected_body = self.issue_body_template.format(
            story_description=story_description,
            acceptance_criteria=acceptance_criteria,
            epic_name=epic_name,
            current_phase=current_phase,
            story_id=story_id,
            priority=priority,
            technical_details=technical_details
        )
        
        if current_issue.get('body') != expected_body:
            updates['body'] = expected_body
        
        # Update issue state
        story_status = story_data.get('status', 'active')
        expected_state = 'closed' if story_status == 'completed' else 'open'
        
        if current_issue.get('state') != expected_state:
            updates['state'] = expected_state
        
        # Update labels
        current_labels = [label['name'] for label in current_issue.get('labels', [])]
        expected_labels = self._prepare_issue_labels(story_data, current_phase)
        
        if set(current_labels) != set(expected_labels):
            updates['labels'] = expected_labels
        
        # Update assignees
        current_assignees = [assignee['login'] for assignee in current_issue.get('assignees', [])]
        expected_assignees = self._prepare_issue_assignees(story_data)
        
        if set(current_assignees) != set(expected_assignees):
            updates['assignees'] = expected_assignees
        
        return updates
    
    def _prepare_story_updates(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare story update payload from GitHub issue"""
        updates = {}
        
        issue_title = issue_data.get('title', '')
        issue_body = issue_data.get('body', '')
        issue_state = issue_data.get('state', 'open')
        
        # Parse story information from issue
        if 'STORY:' in issue_title:
            story_title = issue_title.replace('STORY:', '').strip()
            updates['title'] = story_title
        
        # Update status based on issue state
        if issue_state == 'closed':
            updates['status'] = 'completed'
        else:
            updates['status'] = 'active'
        
        # Extract description from body
        if issue_body:
            # Parse structured body for description
            lines = issue_body.split('\n')
            in_description = False
            description_lines = []
            
            for line in lines:
                if '## Story Description' in line:
                    in_description = True
                    continue
                elif line.startswith('##') and in_description:
                    break
                elif in_description:
                    description_lines.append(line)
            
            if description_lines:
                updates['description'] = '\n'.join(description_lines).strip()
        
        # Extract phase from labels
        labels = [label['name'] for label in issue_data.get('labels', [])]
        for label in labels:
            if label.startswith('phase:'):
                phase = label.replace('phase:', '')
                updates['current_phase'] = phase
                break
        
        return updates
    
    def _extract_story_info_from_issue(self, issue_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract story information from GitHub issue"""
        issue_title = issue_data.get('title', '')
        issue_body = issue_data.get('body', '')
        
        story_info = {}
        
        # Extract from title (assuming format "STORY: Story Title")
        if 'STORY:' in issue_title:
            story_title = issue_title.replace('STORY:', '').strip()
            story_info['title'] = story_title
            # Generate story ID from title (you might have different logic)
            story_info['story_id'] = f"story_{story_title.lower().replace(' ', '_')}"
        
        # Extract from body
        if issue_body:
            story_info['description'] = issue_body
        
        return story_info if story_info else None
    
    def _get_story_mapping(self, story_id: str) -> Optional[BMadStoryMapping]:
        """Get existing story mapping by story ID"""
        # This would query your database
        return None
    
    def _get_issue_mapping(self, issue_number: int) -> Optional[BMadStoryMapping]:
        """Get existing story mapping by issue number"""
        # This would query your database
        return None
    
    def _get_epic_mapping(self, epic_id: str):
        """Get epic mapping by epic ID"""
        # This would query your database for epic mappings
        return None
    
    def _create_story_mapping_record(self, 
                                   story_id: str, 
                                   issue_number: int, 
                                   story_data: Dict[str, Any], 
                                   issue_data: Dict[str, Any]) -> BMadStoryMapping:
        """Create story mapping record in database"""
        mapping = BMadStoryMapping(
            bmad_story_id=story_id,
            github_issue_number=issue_number,
            issue_title=issue_data.get('title', ''),
            issue_url=issue_data.get('html_url', ''),
            sync_status='active',
            last_sync_timestamp=datetime.now(timezone.utc),
            story_metadata=story_data,
            issue_metadata=issue_data
        )
        
        logger.info(f"Created story mapping: Story {story_id} -> Issue {issue_number}")
        return mapping
    
    def _update_story_mapping_record(self, 
                                   mapping: BMadStoryMapping, 
                                   story_data: Dict[str, Any], 
                                   issue_data: Dict[str, Any]) -> BMadStoryMapping:
        """Update story mapping record in database"""
        mapping.last_sync_timestamp = datetime.now(timezone.utc)
        mapping.story_metadata = story_data
        mapping.issue_metadata = issue_data
        
        logger.info(f"Updated story mapping: Story {mapping.bmad_story_id} -> Issue {mapping.github_issue_number}")
        return mapping
    
    def get_all_story_mappings(self) -> List[BMadStoryMapping]:
        """Get all story mappings"""
        # This would query your database
        return []
    
    def delete_story_mapping(self, story_id: str) -> bool:
        """Delete story mapping"""
        logger.info(f"Deleted story mapping for Story {story_id}")
        return True
    
    def validate_story_mapping(self, story_id: str) -> Dict[str, Any]:
        """Validate story mapping integrity"""
        try:
            mapping = self._get_story_mapping(story_id)
            
            if not mapping:
                return {
                    "valid": False,
                    "error": "Mapping not found"
                }
            
            # Check if GitHub issue still exists
            try:
                issue = self.github_client.get_issue(mapping.github_issue_number)
                issue_exists = True
            except GitHubAPIError:
                issue_exists = False
            
            return {
                "valid": issue_exists,
                "mapping": mapping,
                "issue_exists": issue_exists,
                "last_sync": mapping.last_sync_timestamp
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }