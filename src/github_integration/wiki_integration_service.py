"""
GitHub Wiki Integration Service

Handles GitHub Wiki integration for BMAD documentation with automatic
page generation, updates, and structured content management.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from .github_api_client import GitHubAPIClient, GitHubAPIError
from config.github_integration_config import GitHubIntegrationConfig

logger = logging.getLogger(__name__)


@dataclass
class WikiSyncResult:
    """Result of wiki synchronization operation"""
    page_name: str
    page_url: Optional[str]
    status: str  # 'created', 'updated', 'synced', 'error'
    message: str
    conflicts: List[str] = None
    
    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []


class WikiIntegrationService:
    """
    Service for managing GitHub Wiki integration with BMAD
    
    Features:
    - Automatic epic and story documentation pages
    - Template-based content generation
    - Structured wiki organization
    - Cross-linking between pages
    - Version tracking and change management
    """
    
    def __init__(self, config: GitHubIntegrationConfig, github_client: GitHubAPIClient):
        """
        Initialize Wiki Integration Service
        
        Args:
            config: GitHub integration configuration
            github_client: GitHub API client instance
        """
        self.config = config
        self.github_client = github_client
        
        # Wiki configuration
        self.wiki_config = config.wiki_integration
        
        # Templates
        self.epic_page_template = self.wiki_config.epic_page_template
        self.story_page_template = self.wiki_config.story_page_template
        self.epic_content_template = self.wiki_config.epic_page_content_template
        self.story_content_template = self.wiki_config.story_page_content_template
        self.index_page = self.wiki_config.index_page
    
    def sync_epic_documentation(self, 
                              epic_data: Dict[str, Any], 
                              stories_data: List[Dict[str, Any]] = None,
                              force_update: bool = False) -> WikiSyncResult:
        """
        Synchronize epic documentation to GitHub Wiki
        
        Args:
            epic_data: Epic data from BMAD
            stories_data: Related stories data
            force_update: Force update even if no changes detected
            
        Returns:
            WikiSyncResult with operation details
        """
        epic_id = epic_data.get('id')
        epic_name = epic_data.get('name', '')
        
        logger.info(f"Syncing epic {epic_id} documentation to GitHub Wiki")
        
        try:
            # Generate page name
            page_name = self._generate_epic_page_name(epic_data)
            
            # Check if page exists
            existing_page = self._get_wiki_page(page_name)
            
            if existing_page and not force_update:
                # Check if update is needed
                if not self._needs_epic_page_update(epic_data, existing_page):
                    return WikiSyncResult(
                        page_name=page_name,
                        page_url=existing_page.get('html_url'),
                        status='synced',
                        message="Epic documentation already up to date"
                    )
            
            # Generate page content
            page_content = self._generate_epic_page_content(epic_data, stories_data)
            
            # Create or update page
            result = self._create_or_update_wiki_page(
                page_name, 
                page_content, 
                f"Updated epic documentation for {epic_name}"
            )
            
            # Update index page
            self._update_index_page()
            
            status = 'updated' if existing_page else 'created'
            action = 'Updated' if existing_page else 'Created'
            
            logger.info(f"{action} epic documentation page '{page_name}' for Epic {epic_id}")
            
            return WikiSyncResult(
                page_name=page_name,
                page_url=result.get('html_url'),
                status=status,
                message=f"{action} epic documentation page for '{epic_name}'"
            )
            
        except Exception as e:
            logger.error(f"Failed to sync epic documentation for {epic_id}: {str(e)}")
            return WikiSyncResult(
                page_name=page_name if 'page_name' in locals() else 'unknown',
                page_url=None,
                status='error',
                message=f"Documentation sync failed: {str(e)}"
            )
    
    def sync_story_documentation(self, 
                               story_data: Dict[str, Any], 
                               epic_data: Dict[str, Any] = None,
                               force_update: bool = False) -> WikiSyncResult:
        """
        Synchronize story documentation to GitHub Wiki
        
        Args:
            story_data: Story data from BMAD
            epic_data: Parent epic data for context
            force_update: Force update even if no changes detected
            
        Returns:
            WikiSyncResult with operation details
        """
        story_id = story_data.get('id')
        story_title = story_data.get('title', '')
        
        logger.info(f"Syncing story {story_id} documentation to GitHub Wiki")
        
        try:
            # Generate page name
            page_name = self._generate_story_page_name(story_data)
            
            # Check if page exists
            existing_page = self._get_wiki_page(page_name)
            
            if existing_page and not force_update:
                # Check if update is needed
                if not self._needs_story_page_update(story_data, existing_page):
                    return WikiSyncResult(
                        page_name=page_name,
                        page_url=existing_page.get('html_url'),
                        status='synced',
                        message="Story documentation already up to date"
                    )
            
            # Generate page content
            page_content = self._generate_story_page_content(story_data, epic_data)
            
            # Create or update page
            result = self._create_or_update_wiki_page(
                page_name, 
                page_content, 
                f"Updated story documentation for {story_title}"
            )
            
            # Update epic page to include this story
            if epic_data:
                self._update_epic_story_references(epic_data, story_data)
            
            status = 'updated' if existing_page else 'created'
            action = 'Updated' if existing_page else 'Created'
            
            logger.info(f"{action} story documentation page '{page_name}' for Story {story_id}")
            
            return WikiSyncResult(
                page_name=page_name,
                page_url=result.get('html_url'),
                status=status,
                message=f"{action} story documentation page for '{story_title}'"
            )
            
        except Exception as e:
            logger.error(f"Failed to sync story documentation for {story_id}: {str(e)}")
            return WikiSyncResult(
                page_name=page_name if 'page_name' in locals() else 'unknown',
                page_url=None,
                status='error',
                message=f"Documentation sync failed: {str(e)}"
            )
    
    def sync_all_documentation(self, 
                             epics_data: List[Dict[str, Any]], 
                             stories_data: List[Dict[str, Any]] = None) -> List[WikiSyncResult]:
        """
        Synchronize all BMAD documentation to GitHub Wiki
        
        Args:
            epics_data: List of all epic data
            stories_data: List of all story data
            
        Returns:
            List of WikiSyncResult for all operations
        """
        results = []
        
        logger.info("Starting full documentation sync to GitHub Wiki")
        
        try:
            # Group stories by epic
            stories_by_epic = {}
            if stories_data:
                for story in stories_data:
                    epic_id = story.get('epic_id')
                    if epic_id:
                        if epic_id not in stories_by_epic:
                            stories_by_epic[epic_id] = []
                        stories_by_epic[epic_id].append(story)
            
            # Sync epic documentation
            for epic in epics_data:
                epic_id = epic.get('id')
                epic_stories = stories_by_epic.get(epic_id, [])
                
                result = self.sync_epic_documentation(epic, epic_stories)
                results.append(result)
            
            # Sync standalone story documentation
            if stories_data:
                for story in stories_data:
                    epic_id = story.get('epic_id')
                    epic_data = None
                    
                    # Find parent epic
                    if epic_id:
                        epic_data = next((e for e in epics_data if e.get('id') == epic_id), None)
                    
                    result = self.sync_story_documentation(story, epic_data)
                    results.append(result)
            
            # Update index page
            self._update_index_page_comprehensive(epics_data, stories_data)
            
            logger.info(f"Completed full documentation sync: {len(results)} pages processed")
            
        except Exception as e:
            logger.error(f"Full documentation sync failed: {str(e)}")
            results.append(WikiSyncResult(
                page_name='sync_error',
                page_url=None,
                status='error',
                message=f"Full sync failed: {str(e)}"
            ))
        
        return results
    
    def _generate_epic_page_name(self, epic_data: Dict[str, Any]) -> str:
        """Generate wiki page name for epic"""
        epic_id = epic_data.get('id', '')
        epic_name = epic_data.get('name', '')
        
        # Sanitize name for wiki page
        sanitized_name = re.sub(r'[^a-zA-Z0-9_-]', '-', epic_name)
        
        page_name = self.epic_page_template.format(
            epic_id=epic_id,
            epic_name=sanitized_name
        )
        
        return page_name
    
    def _generate_story_page_name(self, story_data: Dict[str, Any]) -> str:
        """Generate wiki page name for story"""
        story_id = story_data.get('id', '')
        story_title = story_data.get('title', '')
        
        # Sanitize title for wiki page
        sanitized_title = re.sub(r'[^a-zA-Z0-9_-]', '-', story_title)
        
        page_name = self.story_page_template.format(
            story_id=story_id,
            story_title=sanitized_title
        )
        
        return page_name
    
    def _generate_epic_page_content(self, 
                                  epic_data: Dict[str, Any], 
                                  stories_data: List[Dict[str, Any]] = None) -> str:
        """Generate content for epic wiki page"""
        epic_name = epic_data.get('name', '')
        epic_description = epic_data.get('description', '')
        current_phase = epic_data.get('current_phase', 'build')
        progress_percentage = epic_data.get('progress_percentage', 0)
        start_date = epic_data.get('start_date', 'Not set')
        target_completion = epic_data.get('target_completion', 'Not set')
        technical_architecture = epic_data.get('technical_architecture', 'To be defined')
        success_metrics = epic_data.get('success_metrics', 'To be defined')
        dependencies = epic_data.get('dependencies', 'None identified')
        risk_assessment = epic_data.get('risk_assessment', 'To be completed')
        
        # Generate stories list
        stories_list = "No stories defined yet."
        if stories_data:
            story_items = []
            for story in stories_data:
                story_title = story.get('title', 'Untitled Story')
                story_id = story.get('id', '')
                story_status = story.get('status', 'pending')
                story_page_name = self._generate_story_page_name(story)
                
                status_emoji = {
                    'completed': '✅',
                    'in_progress': '🔄',
                    'pending': '⏳',
                    'blocked': '🚫'
                }.get(story_status, '📝')
                
                story_items.append(f"- {status_emoji} [{story_title}]({story_page_name}) (ID: {story_id})")
            
            stories_list = '\n'.join(story_items)
        
        # Format dates
        if isinstance(start_date, datetime):
            start_date = start_date.strftime('%Y-%m-%d')
        if isinstance(target_completion, datetime):
            target_completion = target_completion.strftime('%Y-%m-%d')
        
        last_updated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        
        content = self.epic_content_template.format(
            epic_name=epic_name,
            epic_description=epic_description,
            current_phase=current_phase,
            progress_percentage=progress_percentage,
            start_date=start_date,
            target_completion=target_completion,
            stories_list=stories_list,
            technical_architecture=technical_architecture,
            success_metrics=success_metrics,
            dependencies=dependencies,
            risk_assessment=risk_assessment,
            last_updated=last_updated
        )
        
        return content
    
    def _generate_story_page_content(self, 
                                   story_data: Dict[str, Any], 
                                   epic_data: Dict[str, Any] = None) -> str:
        """Generate content for story wiki page"""
        story_title = story_data.get('title', '')
        story_description = story_data.get('description', '')
        acceptance_criteria = story_data.get('acceptance_criteria', 'To be defined')
        technical_implementation = story_data.get('technical_implementation', 'To be planned')
        testing_strategy = story_data.get('testing_strategy', 'To be defined')
        definition_of_done = story_data.get('definition_of_done', 'To be defined')
        status = story_data.get('status', 'pending')
        assignee = story_data.get('assignee', 'Unassigned')
        current_phase = story_data.get('current_phase', 'build')
        
        # Epic context
        epic_name = 'No Epic'
        epic_wiki_link = ''
        if epic_data:
            epic_name = epic_data.get('name', 'Unknown Epic')
            epic_page_name = self._generate_epic_page_name(epic_data)
            epic_wiki_link = epic_page_name
        
        last_updated = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        
        content = self.story_content_template.format(
            story_title=story_title,
            story_description=story_description,
            epic_name=epic_name,
            epic_wiki_link=epic_wiki_link,
            acceptance_criteria=acceptance_criteria,
            technical_implementation=technical_implementation,
            testing_strategy=testing_strategy,
            definition_of_done=definition_of_done,
            status=status,
            assignee=assignee,
            current_phase=current_phase,
            last_updated=last_updated
        )
        
        return content
    
    def _get_wiki_page(self, page_name: str) -> Optional[Dict[str, Any]]:
        """Get existing wiki page"""
        try:
            page = self.github_client.get_wiki_page(page_name)
            return page
        except GitHubAPIError:
            return None
    
    def _create_or_update_wiki_page(self, 
                                  page_name: str, 
                                  content: str, 
                                  commit_message: str) -> Dict[str, Any]:
        """Create or update wiki page"""
        try:
            result = self.github_client.create_or_update_wiki_page(
                page_name=page_name,
                content=content,
                commit_message=commit_message
            )
            return result
        except GitHubAPIError as e:
            logger.error(f"Failed to create/update wiki page '{page_name}': {str(e)}")
            raise
    
    def _needs_epic_page_update(self, 
                              epic_data: Dict[str, Any], 
                              existing_page: Dict[str, Any]) -> bool:
        """Check if epic page needs updating"""
        # Compare last updated time
        epic_updated = epic_data.get('updated_at')
        page_updated = existing_page.get('updated_at')
        
        if epic_updated and page_updated:
            epic_updated_dt = datetime.fromisoformat(epic_updated.replace('Z', '+00:00'))
            page_updated_dt = datetime.fromisoformat(page_updated.replace('Z', '+00:00'))
            return epic_updated_dt > page_updated_dt
        
        return True  # Update if we can't determine timestamps
    
    def _needs_story_page_update(self, 
                               story_data: Dict[str, Any], 
                               existing_page: Dict[str, Any]) -> bool:
        """Check if story page needs updating"""
        # Compare last updated time
        story_updated = story_data.get('updated_at')
        page_updated = existing_page.get('updated_at')
        
        if story_updated and page_updated:
            story_updated_dt = datetime.fromisoformat(story_updated.replace('Z', '+00:00'))
            page_updated_dt = datetime.fromisoformat(page_updated.replace('Z', '+00:00'))
            return story_updated_dt > page_updated_dt
        
        return True  # Update if we can't determine timestamps
    
    def _update_index_page(self) -> None:
        """Update the main index page"""
        try:
            # Get all wiki pages
            pages = self.github_client.get_wiki_pages()
            
            # Generate index content
            index_content = self._generate_index_page_content(pages)
            
            # Update index page
            self._create_or_update_wiki_page(
                self.index_page,
                index_content,
                "Updated BMAD project index"
            )
            
            logger.info("Updated wiki index page")
            
        except Exception as e:
            logger.warning(f"Failed to update index page: {str(e)}")
    
    def _update_index_page_comprehensive(self, 
                                       epics_data: List[Dict[str, Any]], 
                                       stories_data: List[Dict[str, Any]] = None) -> None:
        """Update index page with comprehensive project overview"""
        try:
            index_content = self._generate_comprehensive_index_content(epics_data, stories_data)
            
            self._create_or_update_wiki_page(
                self.index_page,
                index_content,
                "Updated comprehensive BMAD project index"
            )
            
            logger.info("Updated comprehensive wiki index page")
            
        except Exception as e:
            logger.warning(f"Failed to update comprehensive index page: {str(e)}")
    
    def _generate_index_page_content(self, pages: List[Dict[str, Any]]) -> str:
        """Generate content for index page"""
        epic_pages = []
        story_pages = []
        other_pages = []
        
        # Categorize pages
        for page in pages:
            page_title = page.get('title', '')
            if page_title.startswith('Epic-'):
                epic_pages.append(page)
            elif page_title.startswith('Story-'):
                story_pages.append(page)
            else:
                other_pages.append(page)
        
        # Sort pages
        epic_pages.sort(key=lambda p: p.get('title', ''))
        story_pages.sort(key=lambda p: p.get('title', ''))
        other_pages.sort(key=lambda p: p.get('title', ''))
        
        content = f"""# BMAD Project Documentation Index

Welcome to the BMAD (Build, Measure, Analyze, Document) project documentation.

## Project Overview

This wiki contains comprehensive documentation for all epics and stories in our BMAD-managed project.

## Epics ({len(epic_pages)})

"""
        
        for page in epic_pages:
            page_title = page.get('title', '')
            content += f"- [{page_title}]({page_title})\n"
        
        content += f"\n## Stories ({len(story_pages)})\n\n"
        
        for page in story_pages:
            page_title = page.get('title', '')
            content += f"- [{page_title}]({page_title})\n"
        
        if other_pages:
            content += f"\n## Other Documentation ({len(other_pages)})\n\n"
            for page in other_pages:
                page_title = page.get('title', '')
                content += f"- [{page_title}]({page_title})\n"
        
        content += f"""

## Documentation Guidelines

### Epic Pages
Epic pages contain high-level project information including:
- Project overview and objectives
- Current phase and progress
- Associated stories
- Technical architecture
- Success metrics and dependencies

### Story Pages
Story pages contain detailed information about individual features:
- Story description and acceptance criteria
- Technical implementation details
- Testing strategy
- Definition of done

## BMAD Methodology

Our project follows the BMAD methodology:

1. **Build** - Development and implementation
2. **Measure** - Metrics collection and monitoring
3. **Analyze** - Data analysis and insights
4. **Document** - Knowledge capture and sharing

---

*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*
*Generated automatically by BMAD GitHub Integration*
"""
        
        return content
    
    def _generate_comprehensive_index_content(self, 
                                            epics_data: List[Dict[str, Any]], 
                                            stories_data: List[Dict[str, Any]] = None) -> str:
        """Generate comprehensive index page content"""
        # Calculate project statistics
        total_epics = len(epics_data)
        completed_epics = len([e for e in epics_data if e.get('status') == 'completed'])
        
        total_stories = len(stories_data) if stories_data else 0
        completed_stories = len([s for s in stories_data if s.get('status') == 'completed']) if stories_data else 0
        
        # Current phase distribution
        phase_counts = {}
        for epic in epics_data:
            phase = epic.get('current_phase', 'build')
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        content = f"""# BMAD Project Documentation Index

Welcome to the BMAD (Build, Measure, Analyze, Document) project documentation.

## Project Statistics

- **Total Epics**: {total_epics} ({completed_epics} completed)
- **Total Stories**: {total_stories} ({completed_stories} completed)
- **Overall Progress**: {round((completed_epics / total_epics * 100) if total_epics > 0 else 0, 1)}%

## Phase Distribution

"""
        
        for phase, count in phase_counts.items():
            percentage = round((count / total_epics * 100) if total_epics > 0 else 0, 1)
            content += f"- **{phase.title()}**: {count} epics ({percentage}%)\n"
        
        content += "\n## Active Epics\n\n"
        
        active_epics = [e for e in epics_data if e.get('status') != 'completed']
        for epic in active_epics:
            epic_name = epic.get('name', 'Untitled Epic')
            epic_phase = epic.get('current_phase', 'build')
            epic_progress = epic.get('progress_percentage', 0)
            page_name = self._generate_epic_page_name(epic)
            
            phase_emoji = {
                'build': '🔨',
                'measure': '📊',
                'analyze': '🔍',
                'document': '📝'
            }.get(epic_phase, '📋')
            
            content += f"- {phase_emoji} [{epic_name}]({page_name}) - {epic_phase.title()} ({epic_progress}%)\n"
        
        content += "\n## Completed Epics\n\n"
        
        completed_epic_list = [e for e in epics_data if e.get('status') == 'completed']
        for epic in completed_epic_list:
            epic_name = epic.get('name', 'Untitled Epic')
            page_name = self._generate_epic_page_name(epic)
            content += f"- ✅ [{epic_name}]({page_name})\n"
        
        content += f"""

## Recent Activity

### Recently Updated Epics
"""
        
        # Sort by last updated (most recent first)
        recent_epics = sorted(epics_data, 
                            key=lambda e: e.get('updated_at', ''), 
                            reverse=True)[:5]
        
        for epic in recent_epics:
            epic_name = epic.get('name', 'Untitled Epic')
            updated_at = epic.get('updated_at', 'Unknown')
            page_name = self._generate_epic_page_name(epic)
            content += f"- [{epic_name}]({page_name}) - {updated_at}\n"
        
        content += f"""

## BMAD Methodology

Our project follows the BMAD methodology for systematic development:

### 🔨 Build Phase
Development and implementation of features with focus on rapid prototyping and core functionality.

### 📊 Measure Phase  
Collection of performance metrics, quality indicators, and validation data.

### 🔍 Analyze Phase
Analysis of collected data, pattern recognition, and identification of improvement opportunities.

### 📝 Document Phase
Knowledge capture, lesson documentation, and sharing of insights for future reference.

## Navigation Tips

- **Epic Pages**: Click on epic names to view detailed epic documentation
- **Story Pages**: Access individual story documentation from epic pages
- **Search**: Use the wiki search to find specific topics or features
- **History**: View page history to track documentation changes

---

*Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*  
*Generated automatically by BMAD GitHub Integration*  
*Total pages documented: {total_epics + total_stories}*
"""
        
        return content
    
    def _update_epic_story_references(self, 
                                    epic_data: Dict[str, Any], 
                                    story_data: Dict[str, Any]) -> None:
        """Update epic page to reference new or updated story"""
        try:
            epic_page_name = self._generate_epic_page_name(epic_data)
            
            # Get all stories for this epic (this would typically come from your database)
            # For now, we'll just regenerate the epic page
            self.sync_epic_documentation(epic_data, [story_data], force_update=True)
            
        except Exception as e:
            logger.warning(f"Failed to update epic story references: {str(e)}")
    
    def get_wiki_statistics(self) -> Dict[str, Any]:
        """Get wiki documentation statistics"""
        try:
            pages = self.github_client.get_wiki_pages()
            
            epic_pages = [p for p in pages if p.get('title', '').startswith('Epic-')]
            story_pages = [p for p in pages if p.get('title', '').startswith('Story-')]
            other_pages = [p for p in pages if not (
                p.get('title', '').startswith('Epic-') or 
                p.get('title', '').startswith('Story-')
            )]
            
            return {
                'total_pages': len(pages),
                'epic_pages': len(epic_pages),
                'story_pages': len(story_pages),
                'other_pages': len(other_pages),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get wiki statistics: {str(e)}")
            return {
                'error': str(e),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }