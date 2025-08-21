"""
Database models for GitHub integration with BMAD methodology.
Provides SQLAlchemy models for mapping BMAD concepts to GitHub entities.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from enum import Enum

Base = declarative_base()


class SyncStatus(Enum):
    """Synchronization status enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


class OperationType(Enum):
    """GitHub operation type enumeration."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SYNC = "sync"
    WEBHOOK = "webhook"


class EntityType(Enum):
    """Entity type enumeration."""
    EPIC = "epic"
    STORY = "story"
    WIKI = "wiki"
    PROJECT = "project"
    ISSUE = "issue"


class GitHubEpicMapping(Base):
    """Maps BMAD epics to GitHub projects."""
    
    __tablename__ = 'github_epic_mapping'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    bmad_epic_id = Column(String(50), nullable=False, index=True)
    github_project_id = Column(String(50), nullable=False, index=True)
    github_project_number = Column(Integer)
    repository_owner = Column(String(100), nullable=False)
    repository_name = Column(String(100), nullable=False)
    project_url = Column(String(500))
    sync_status = Column(String(20), default=SyncStatus.ACTIVE.value)
    last_synced = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Configuration data
    auto_sync_enabled = Column(Boolean, default=True)
    sync_metadata = Column(JSON)
    
    # Relationships
    stories = relationship("GitHubStoryMapping", back_populates="epic")
    sync_logs = relationship("GitHubSyncLog", 
                           foreign_keys="GitHubSyncLog.epic_mapping_id",
                           back_populates="epic_mapping")
    
    def __repr__(self):
        return f"<GitHubEpicMapping(bmad_epic_id='{self.bmad_epic_id}', github_project_id='{self.github_project_id}')>"


class GitHubStoryMapping(Base):
    """Maps BMAD stories to GitHub issues."""
    
    __tablename__ = 'github_story_mapping'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    bmad_story_id = Column(String(50), nullable=False, index=True)
    github_issue_id = Column(String(50), nullable=False, index=True)
    github_issue_number = Column(Integer, nullable=False)
    repository_owner = Column(String(100), nullable=False)
    repository_name = Column(String(100), nullable=False)
    issue_url = Column(String(500))
    epic_mapping_id = Column(Integer, ForeignKey('github_epic_mapping.id'))
    sync_status = Column(String(20), default=SyncStatus.ACTIVE.value)
    last_synced = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Story metadata
    current_phase = Column(String(20))  # build, measure, analyze, document
    labels = Column(JSON)  # GitHub labels applied
    assignees = Column(JSON)  # GitHub assignees
    milestone_id = Column(String(50))  # GitHub milestone ID
    
    # Relationships
    epic = relationship("GitHubEpicMapping", back_populates="stories")
    sync_logs = relationship("GitHubSyncLog",
                           foreign_keys="GitHubSyncLog.story_mapping_id", 
                           back_populates="story_mapping")
    
    def __repr__(self):
        return f"<GitHubStoryMapping(bmad_story_id='{self.bmad_story_id}', github_issue_number={self.github_issue_number})>"


class GitHubSyncLog(Base):
    """Logs all GitHub synchronization operations."""
    
    __tablename__ = 'github_sync_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_type = Column(String(50), nullable=False)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(String(50), nullable=False, index=True)
    github_entity_id = Column(String(50), index=True)
    status = Column(String(20), nullable=False)  # success, error, pending
    error_message = Column(Text)
    response_data = Column(JSON)
    sync_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    retry_count = Column(Integer, default=0)
    
    # Foreign keys for relationships
    epic_mapping_id = Column(Integer, ForeignKey('github_epic_mapping.id'))
    story_mapping_id = Column(Integer, ForeignKey('github_story_mapping.id'))
    
    # Performance metrics
    duration_ms = Column(Integer)  # Operation duration in milliseconds
    api_calls_count = Column(Integer, default=1)
    rate_limit_remaining = Column(Integer)
    
    # Relationships
    epic_mapping = relationship("GitHubEpicMapping", back_populates="sync_logs")
    story_mapping = relationship("GitHubStoryMapping", back_populates="sync_logs")
    
    def __repr__(self):
        return f"<GitHubSyncLog(operation='{self.operation_type}', entity='{self.entity_type}:{self.entity_id}', status='{self.status}')>"


class GitHubAuthToken(Base):
    """Stores GitHub authentication tokens securely."""
    
    __tablename__ = 'github_auth_tokens'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    token_hash = Column(String(256), nullable=False)  # SHA-256 hash of token
    token_scope = Column(String(200))  # API scopes
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Token metadata
    github_user_id = Column(String(50))
    github_username = Column(String(100))
    api_rate_limit = Column(Integer, default=5000)
    
    def __repr__(self):
        return f"<GitHubAuthToken(user_id='{self.user_id}', active={self.is_active})>"


class GitHubIntegrationConfig(Base):
    """Stores GitHub integration configuration settings."""
    
    __tablename__ = 'github_integration_config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), nullable=False, unique=True, index=True)
    config_value = Column(Text)
    config_type = Column(String(20), default='string')  # string, json, boolean, integer
    is_encrypted = Column(Boolean, default=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(50))
    
    def __repr__(self):
        return f"<GitHubIntegrationConfig(key='{self.config_key}', type='{self.config_type}')>"


class GitHubWebhookEvent(Base):
    """Stores incoming GitHub webhook events."""
    
    __tablename__ = 'github_webhook_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(50), unique=True, index=True)  # GitHub delivery ID
    event_type = Column(String(50), nullable=False, index=True)  # issues, projects, etc.
    action = Column(String(50))  # opened, closed, edited, etc.
    repository_full_name = Column(String(200), index=True)
    payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime)
    received_at = Column(DateTime, default=datetime.utcnow, index=True)
    error_message = Column(Text)
    
    # Validation
    signature_valid = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<GitHubWebhookEvent(event_type='{self.event_type}', action='{self.action}', processed={self.processed})>"


class GitHubRateLimit(Base):
    """Tracks GitHub API rate limit usage."""
    
    __tablename__ = 'github_rate_limits'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_type = Column(String(20), nullable=False, index=True)  # rest, graphql, search
    user_id = Column(String(50), index=True)
    limit_total = Column(Integer, nullable=False)
    limit_remaining = Column(Integer, nullable=False)
    limit_reset_time = Column(DateTime, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Usage statistics
    requests_made = Column(Integer, default=0)
    burst_usage = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<GitHubRateLimit(api_type='{self.api_type}', remaining={self.limit_remaining}/{self.limit_total})>"


class GitHubMilestone(Base):
    """Maps BMAD phases to GitHub milestones."""
    
    __tablename__ = 'github_milestones'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    bmad_epic_id = Column(String(50), nullable=False, index=True)
    bmad_phase = Column(String(20), nullable=False)  # build, measure, analyze, document
    github_milestone_id = Column(String(50), nullable=False, index=True)
    github_milestone_number = Column(Integer)
    repository_owner = Column(String(100), nullable=False)
    repository_name = Column(String(100), nullable=False)
    milestone_url = Column(String(500))
    state = Column(String(20), default='open')  # open, closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Milestone metadata
    title = Column(String(255))
    description = Column(Text)
    due_date = Column(DateTime)
    completion_percentage = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<GitHubMilestone(epic='{self.bmad_epic_id}', phase='{self.bmad_phase}', milestone_id='{self.github_milestone_id}')>"


class GitHubQualityGate(Base):
    """Maps BMAD quality gates to GitHub status checks."""
    
    __tablename__ = 'github_quality_gates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    bmad_phase = Column(String(20), nullable=False, index=True)
    github_check_name = Column(String(100), nullable=False)
    repository_owner = Column(String(100), nullable=False)
    repository_name = Column(String(100), nullable=False)
    is_required = Column(Boolean, default=True)
    auto_check = Column(Boolean, default=True)
    check_context = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Gate configuration
    threshold_config = Column(JSON)
    validation_rules = Column(JSON)
    
    def __repr__(self):
        return f"<GitHubQualityGate(phase='{self.bmad_phase}', check='{self.github_check_name}')>"


# Database indexes for performance optimization
from sqlalchemy import Index

# Composite indexes for common queries
Index('idx_epic_mapping_repo', GitHubEpicMapping.repository_owner, GitHubEpicMapping.repository_name)
Index('idx_story_mapping_repo', GitHubStoryMapping.repository_owner, GitHubStoryMapping.repository_name)
Index('idx_sync_log_entity_type_status', GitHubSyncLog.entity_type, GitHubSyncLog.status)
Index('idx_sync_log_timestamp_status', GitHubSyncLog.sync_timestamp, GitHubSyncLog.status)
Index('idx_webhook_event_type_processed', GitHubWebhookEvent.event_type, GitHubWebhookEvent.processed)
Index('idx_rate_limit_api_user', GitHubRateLimit.api_type, GitHubRateLimit.user_id)
Index('idx_milestone_epic_phase', GitHubMilestone.bmad_epic_id, GitHubMilestone.bmad_phase)


def create_database_schema(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)


def drop_database_schema(engine):
    """Drop all database tables."""
    Base.metadata.drop_all(engine)