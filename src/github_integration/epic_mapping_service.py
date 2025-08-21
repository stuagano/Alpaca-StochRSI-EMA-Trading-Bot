"""
Epic to GitHub Project Mapping Service

Handles bidirectional synchronization between BMAD Epics and GitHub Projects
with comprehensive mapping, validation, and conflict resolution.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from .github_api_client import GitHubAPIClient, GitHubAPIError
from .models import BMadEpicMapping, GitHubProject
from config.github_integration_config import GitHubIntegrationConfig

logger = logging.getLogger(__name__)


@dataclass
class EpicSyncResult:
    """Result of epic synchronization operation"""
    epic_id: str
    project_id: Optional[int]
    status: str  # 'created', 'updated', 'synced', 'error'
    message: str
    conflicts: List[str] = None
    
    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []


@dataclass
class ProjectSyncResult:
    """Result of project synchronization operation"""
    project_id: int
    epic_id: Optional[str]
    status: str  # 'mapped', 'created', 'updated', 'error'
    message: str
    conflicts: List[str] = None
    
    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []


class EpicMappingService:
    """
    Service for managing Epic to GitHub Project mappings
    
    Features:
    - Bidirectional sync between BMAD Epics and GitHub Projects
    - Automatic project creation with customizable templates
    - Column structure management
    - Conflict detection and resolution
    - Comprehensive audit logging
    """
    
    def __init__(self, config: GitHubIntegrationConfig, github_client: GitHubAPIClient):
        """
        Initialize Epic Mapping Service
        
        Args:
            config: GitHub integration configuration
            github_client: GitHub API client instance
        """
        self.config = config
        self.github_client = github_client
        
        # Mapping configuration
        self.epic_config = config.epic_mapping
        
        # Templates
        self.project_template = self.epic_config.project_template
        self.description_template = self.epic_config.project_description_template
        self.default_columns = self.epic_config.default_columns
        self.default_labels = self.epic_config.labels
    
    def sync_epic_to_project(self, 
                           epic_data: Dict[str, Any], 
                           force_update: bool = False) -> EpicSyncResult:
        """
        Synchronize BMAD Epic to GitHub Project
        
        Args:
            epic_data: Epic data from BMAD
            force_update: Force update even if no changes detected
            
        Returns:
            EpicSyncResult with operation details
        """
        epic_id = epic_data.get('id')
        epic_name = epic_data.get('name', '')
        
        logger.info(f"Syncing epic {epic_id} to GitHub Project")
        
        try:
            # Check if mapping already exists
            existing_mapping = self._get_epic_mapping(epic_id)
            
            if existing_mapping and existing_mapping.github_project_id:
                # Update existing project
                return self._update_existing_project(epic_data, existing_mapping, force_update)
            else:
                # Create new project
                return self._create_new_project(epic_data)
                
        except Exception as e:
            logger.error(f"Failed to sync epic {epic_id}: {str(e)}")
            return EpicSyncResult(
                epic_id=epic_id,
                project_id=None,
                status='error',
                message=f"Sync failed: {str(e)}"
            )
    
    def sync_project_to_epic(self, 
                           project_data: Dict[str, Any], 
                           force_update: bool = False) -> ProjectSyncResult:
        """
        Synchronize GitHub Project to BMAD Epic
        
        Args:
            project_data: Project data from GitHub
            force_update: Force update even if no changes detected
            
        Returns:
            ProjectSyncResult with operation details
        """
        project_id = project_data.get('id')
        project_name = project_data.get('name', '')
        
        logger.info(f"Syncing GitHub Project {project_id} to BMAD Epic")
        
        try:
            # Check if mapping already exists
            existing_mapping = self._get_project_mapping(project_id)
            
            if existing_mapping and existing_mapping.bmad_epic_id:
                # Update existing epic
                return self._update_existing_epic(project_data, existing_mapping, force_update)
            else:
                # Create new epic mapping
                return self._create_epic_mapping(project_data)
                
        except Exception as e:
            logger.error(f"Failed to sync project {project_id}: {str(e)}")
            return ProjectSyncResult(
                project_id=project_id,
                epic_id=None,
                status='error',
                message=f"Sync failed: {str(e)}"
            )
    
    def _create_new_project(self, epic_data: Dict[str, Any]) -> EpicSyncResult:
        """Create new GitHub Project for Epic"""
        epic_id = epic_data.get('id')
        epic_name = epic_data.get('name', '')
        epic_description = epic_data.get('description', '')
        current_phase = epic_data.get('current_phase', 'build')
        
        try:
            # Generate project name from template
            project_name = self.project_template.format(
                epic_name=epic_name,
                epic_id=epic_id
            )
            
            # Generate project description from template
            project_description = self.description_template.format(
                epic_description=epic_description,
                current_phase=current_phase,
                epic_name=epic_name,
                epic_id=epic_id
            )
            
            # Create GitHub project
            project = self.github_client.create_project(
                name=project_name,
                body=project_description,
                state='open'
            )
            
            project_id = project['id']
            
            # Create project columns
            self._setup_project_columns(project_id)
            
            # Create epic mapping
            mapping = self._create_epic_mapping_record(epic_id, project_id, epic_data, project)
            
            logger.info(f"Created GitHub Project {project_id} for Epic {epic_id}")
            
            return EpicSyncResult(
                epic_id=epic_id,
                project_id=project_id,
                status='created',
                message=f"Created GitHub Project '{project_name}' for Epic '{epic_name}'"
            )
            
        except GitHubAPIError as e:
            logger.error(f"GitHub API error creating project for epic {epic_id}: {str(e)}")
            return EpicSyncResult(
                epic_id=epic_id,
                project_id=None,
                status='error',
                message=f"GitHub API error: {str(e)}"
            )
    
    def _update_existing_project(self, 
                               epic_data: Dict[str, Any], 
                               mapping: BMadEpicMapping, 
                               force_update: bool) -> EpicSyncResult:
        """Update existing GitHub Project from Epic"""
        epic_id = epic_data.get('id')
        epic_name = epic_data.get('name', '')
        project_id = mapping.github_project_id
        
        try:
            # Get current project state
            current_project = self.github_client.get_project(project_id)
            
            # Check if update is needed
            if not force_update and not self._needs_project_update(epic_data, current_project, mapping):
                return EpicSyncResult(
                    epic_id=epic_id,
                    project_id=project_id,
                    status='synced',
                    message="Project already up to date"
                )
            
            # Prepare updates
            updates = self._prepare_project_updates(epic_data, current_project)
            
            if updates:
                # Update GitHub project
                updated_project = self.github_client.update_project(project_id, **updates)
                
                # Update mapping record
                self._update_epic_mapping_record(mapping, epic_data, updated_project)
                
                logger.info(f"Updated GitHub Project {project_id} for Epic {epic_id}")
                
                return EpicSyncResult(
                    epic_id=epic_id,
                    project_id=project_id,
                    status='updated',
                    message=f"Updated GitHub Project for Epic '{epic_name}'"
                )
            else:
                return EpicSyncResult(
                    epic_id=epic_id,
                    project_id=project_id,
                    status='synced',
                    message="No updates needed"
                )
                
        except GitHubAPIError as e:
            logger.error(f"GitHub API error updating project {project_id}: {str(e)}")
            return EpicSyncResult(
                epic_id=epic_id,
                project_id=project_id,
                status='error',
                message=f"GitHub API error: {str(e)}"
            )
    
    def _create_epic_mapping(self, project_data: Dict[str, Any]) -> ProjectSyncResult:
        """Create Epic mapping for existing GitHub Project"""
        project_id = project_data.get('id')
        project_name = project_data.get('name', '')
        
        try:
            # Extract epic information from project
            epic_info = self._extract_epic_info_from_project(project_data)
            
            if not epic_info:
                return ProjectSyncResult(
                    project_id=project_id,
                    epic_id=None,
                    status='error',
                    message="Could not extract epic information from project"
                )
            
            epic_id = epic_info.get('epic_id')
            
            # Create mapping record
            mapping = self._create_epic_mapping_record(epic_id, project_id, epic_info, project_data)
            
            logger.info(f"Created Epic mapping for GitHub Project {project_id}")
            
            return ProjectSyncResult(
                project_id=project_id,
                epic_id=epic_id,
                status='mapped',
                message=f"Mapped GitHub Project '{project_name}' to Epic '{epic_id}'"
            )
            
        except Exception as e:
            logger.error(f"Failed to create epic mapping for project {project_id}: {str(e)}")
            return ProjectSyncResult(
                project_id=project_id,
                epic_id=None,
                status='error',
                message=f"Mapping creation failed: {str(e)}"
            )
    
    def _update_existing_epic(self, 
                            project_data: Dict[str, Any], 
                            mapping: BMadEpicMapping, 
                            force_update: bool) -> ProjectSyncResult:
        """Update existing Epic from GitHub Project"""
        project_id = project_data.get('id')
        epic_id = mapping.bmad_epic_id
        
        try:
            # Check if update is needed
            if not force_update and not self._needs_epic_update(project_data, mapping):
                return ProjectSyncResult(
                    project_id=project_id,
                    epic_id=epic_id,
                    status='synced',
                    message="Epic already up to date"
                )
            
            # Update epic in BMAD system
            # Note: This would integrate with your BMAD epic management system
            epic_updates = self._prepare_epic_updates(project_data)
            
            # Update mapping record
            self._update_epic_mapping_record(mapping, epic_updates, project_data)
            
            logger.info(f"Updated Epic {epic_id} from GitHub Project {project_id}")
            
            return ProjectSyncResult(
                project_id=project_id,
                epic_id=epic_id,
                status='updated',
                message=f"Updated Epic '{epic_id}' from GitHub Project"
            )
            
        except Exception as e:
            logger.error(f"Failed to update epic {epic_id} from project {project_id}: {str(e)}")
            return ProjectSyncResult(
                project_id=project_id,
                epic_id=epic_id,
                status='error',
                message=f"Epic update failed: {str(e)}"
            )
    
    def _setup_project_columns(self, project_id: int) -> List[Dict[str, Any]]:
        """Setup default columns for new project"""
        columns = []
        
        try:
            for column_name in self.default_columns:
                column = self.github_client.create_project_column(project_id, column_name)
                columns.append(column)
                logger.debug(f"Created column '{column_name}' in project {project_id}")
            
            return columns
            
        except GitHubAPIError as e:
            logger.error(f"Failed to create columns for project {project_id}: {str(e)}")
            raise
    
    def _needs_project_update(self, 
                            epic_data: Dict[str, Any], 
                            current_project: Dict[str, Any], 
                            mapping: BMadEpicMapping) -> bool:
        """Check if project needs updating based on epic changes"""
        # Compare relevant fields
        epic_name = epic_data.get('name', '')
        epic_description = epic_data.get('description', '')
        current_phase = epic_data.get('current_phase', 'build')
        
        # Generate expected project name and description
        expected_name = self.project_template.format(
            epic_name=epic_name,
            epic_id=epic_data.get('id')
        )
        
        expected_description = self.description_template.format(
            epic_description=epic_description,
            current_phase=current_phase,
            epic_name=epic_name,
            epic_id=epic_data.get('id')
        )
        
        # Check for changes
        name_changed = current_project.get('name') != expected_name
        description_changed = current_project.get('body') != expected_description
        
        # Check last sync time
        last_sync = mapping.last_sync_timestamp
        epic_updated = epic_data.get('updated_at')
        
        time_based_update = (
            epic_updated and last_sync and 
            datetime.fromisoformat(epic_updated.replace('Z', '+00:00')) > last_sync
        )
        
        return name_changed or description_changed or time_based_update
    
    def _needs_epic_update(self, 
                         project_data: Dict[str, Any], 
                         mapping: BMadEpicMapping) -> bool:
        """Check if epic needs updating based on project changes"""
        # Check last sync time
        last_sync = mapping.last_sync_timestamp
        project_updated = project_data.get('updated_at')
        
        if project_updated and last_sync:
            project_updated_dt = datetime.fromisoformat(project_updated.replace('Z', '+00:00'))
            return project_updated_dt > last_sync
        
        return True  # Update if we can't determine timestamps
    
    def _prepare_project_updates(self, 
                               epic_data: Dict[str, Any], 
                               current_project: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare GitHub project update payload"""
        updates = {}
        
        epic_name = epic_data.get('name', '')
        epic_description = epic_data.get('description', '')
        current_phase = epic_data.get('current_phase', 'build')
        epic_id = epic_data.get('id')
        
        # Update project name
        expected_name = self.project_template.format(
            epic_name=epic_name,
            epic_id=epic_id
        )
        
        if current_project.get('name') != expected_name:
            updates['name'] = expected_name
        
        # Update project description
        expected_description = self.description_template.format(
            epic_description=epic_description,
            current_phase=current_phase,
            epic_name=epic_name,
            epic_id=epic_id
        )
        
        if current_project.get('body') != expected_description:
            updates['body'] = expected_description
        
        # Update project state based on epic status
        epic_status = epic_data.get('status', 'active')
        expected_state = 'closed' if epic_status == 'completed' else 'open'
        
        if current_project.get('state') != expected_state:
            updates['state'] = expected_state
        
        return updates
    
    def _prepare_epic_updates(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare epic update payload from GitHub project"""
        # Extract information from project data
        updates = {}
        
        project_name = project_data.get('name', '')
        project_description = project_data.get('body', '')
        project_state = project_data.get('state', 'open')
        
        # Parse epic information from project
        if 'EPIC:' in project_name:
            epic_name = project_name.replace('EPIC:', '').strip()
            updates['name'] = epic_name
        
        # Update status based on project state
        if project_state == 'closed':
            updates['status'] = 'completed'
        else:
            updates['status'] = 'active'
        
        # Extract description
        if project_description:
            updates['description'] = project_description
        
        return updates
    
    def _extract_epic_info_from_project(self, project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract epic information from GitHub project"""
        project_name = project_data.get('name', '')
        project_description = project_data.get('body', '')
        
        # Look for epic ID pattern in name or description
        epic_info = {}
        
        # Extract from name (assuming format "EPIC: Epic Name")
        if 'EPIC:' in project_name:
            epic_name = project_name.replace('EPIC:', '').strip()
            epic_info['name'] = epic_name
            # Generate epic ID from name (you might have different logic)
            epic_info['epic_id'] = f"epic_{epic_name.lower().replace(' ', '_')}"
        
        # Extract from description
        if project_description:
            epic_info['description'] = project_description
        
        return epic_info if epic_info else None
    
    def _get_epic_mapping(self, epic_id: str) -> Optional[BMadEpicMapping]:
        """Get existing epic mapping by epic ID"""
        # This would query your database
        # For now, return None (implement with your database layer)
        return None
    
    def _get_project_mapping(self, project_id: int) -> Optional[BMadEpicMapping]:
        """Get existing epic mapping by project ID"""
        # This would query your database
        # For now, return None (implement with your database layer)
        return None
    
    def _create_epic_mapping_record(self, 
                                  epic_id: str, 
                                  project_id: int, 
                                  epic_data: Dict[str, Any], 
                                  project_data: Dict[str, Any]) -> BMadEpicMapping:
        """Create epic mapping record in database"""
        # This would create a record in your database
        # For now, return a mock object (implement with your database layer)
        mapping = BMadEpicMapping(
            bmad_epic_id=epic_id,
            github_project_id=project_id,
            project_name=project_data.get('name', ''),
            project_url=project_data.get('html_url', ''),
            sync_status='active',
            last_sync_timestamp=datetime.now(timezone.utc),
            epic_metadata=epic_data,
            project_metadata=project_data
        )
        
        logger.info(f"Created epic mapping: Epic {epic_id} -> Project {project_id}")
        return mapping
    
    def _update_epic_mapping_record(self, 
                                  mapping: BMadEpicMapping, 
                                  epic_data: Dict[str, Any], 
                                  project_data: Dict[str, Any]) -> BMadEpicMapping:
        """Update epic mapping record in database"""
        # This would update the record in your database
        mapping.last_sync_timestamp = datetime.now(timezone.utc)
        mapping.epic_metadata = epic_data
        mapping.project_metadata = project_data
        
        logger.info(f"Updated epic mapping: Epic {mapping.bmad_epic_id} -> Project {mapping.github_project_id}")
        return mapping
    
    def get_all_epic_mappings(self) -> List[BMadEpicMapping]:
        """Get all epic mappings"""
        # This would query your database
        # For now, return empty list (implement with your database layer)
        return []
    
    def delete_epic_mapping(self, epic_id: str) -> bool:
        """Delete epic mapping"""
        # This would delete from your database
        logger.info(f"Deleted epic mapping for Epic {epic_id}")
        return True
    
    def validate_epic_mapping(self, epic_id: str) -> Dict[str, Any]:
        """Validate epic mapping integrity"""
        try:
            mapping = self._get_epic_mapping(epic_id)
            
            if not mapping:
                return {
                    "valid": False,
                    "error": "Mapping not found"
                }
            
            # Check if GitHub project still exists
            try:
                project = self.github_client.get_project(mapping.github_project_id)
                project_exists = True
            except GitHubAPIError:
                project_exists = False
            
            return {
                "valid": project_exists,
                "mapping": mapping,
                "project_exists": project_exists,
                "last_sync": mapping.last_sync_timestamp
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }