"""
GitHub Integration API Routes for BMAD

Provides REST API endpoints for GitHub Projects and Wikis integration
with comprehensive configuration, synchronization, and monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from flask import Blueprint, request, jsonify, current_app
from functools import wraps

# Import our GitHub integration components
from src.github_integration.github_api_client import GitHubAPIClient, GitHubAPIError
from src.github_integration.sync_service import GitHubSyncService
from config.github_integration_config import get_github_config, GitHubConfigManager

logger = logging.getLogger(__name__)

# Create blueprint
github_bp = Blueprint('github_integration', __name__, url_prefix='/api/github')


def handle_api_errors(f):
    """Decorator to handle API errors consistently"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except GitHubAPIError as e:
            logger.error(f"GitHub API error in {f.__name__}: {str(e)}")
            return jsonify({
                "error": "GitHub API Error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            return jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    return decorated_function


def require_github_enabled(f):
    """Decorator to check if GitHub integration is enabled"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = get_github_config()
        if not config.enabled:
            return jsonify({
                "error": "GitHub Integration Disabled",
                "message": "GitHub integration is not enabled in configuration",
                "timestamp": datetime.utcnow().isoformat()
            }), 403
        return f(*args, **kwargs)
    return decorated_function


# Configuration Management Endpoints

@github_bp.route('/config', methods=['GET'])
@handle_api_errors
def get_configuration():
    """Get GitHub integration configuration"""
    config = get_github_config()
    
    # Sanitize sensitive data
    config_dict = {
        "version": config.version,
        "enabled": config.enabled,
        "repository": {
            "owner": config.repository.owner,
            "name": config.repository.name,
            "default_branch": config.repository.default_branch,
            "wiki_enabled": config.repository.wiki_enabled,
            "projects_enabled": config.repository.projects_enabled
        },
        "epic_mapping": {
            "enabled": config.epic_mapping.enabled,
            "auto_create_projects": config.epic_mapping.auto_create_projects,
            "default_columns": config.epic_mapping.default_columns,
            "labels": config.epic_mapping.labels
        },
        "story_mapping": {
            "enabled": config.story_mapping.enabled,
            "auto_create_issues": config.story_mapping.auto_create_issues,
            "labels": config.story_mapping.labels,
            "milestone_mapping": config.story_mapping.milestone_mapping
        },
        "wiki_integration": {
            "enabled": config.wiki_integration.enabled,
            "auto_update": config.wiki_integration.auto_update,
            "index_page": config.wiki_integration.index_page
        },
        "synchronization": {
            "enabled": config.synchronization.enabled,
            "bidirectional": config.synchronization.bidirectional,
            "real_time_webhook": config.synchronization.real_time_webhook,
            "batch_sync_interval": config.synchronization.batch_sync_interval
        },
        "quality_gates": {
            "enabled": config.quality_gates.enabled,
            "require_epic_approval": config.quality_gates.require_epic_approval,
            "require_story_validation": config.quality_gates.require_story_validation,
            "auto_close_completed": config.quality_gates.auto_close_completed
        },
        "monitoring": {
            "enabled": config.monitoring.enabled,
            "metrics_collection": config.monitoring.metrics_collection,
            "log_level": config.monitoring.log_level,
            "health_check_interval": config.monitoring.health_check_interval
        },
        "last_sync": config.last_sync,
        "sync_statistics": config.sync_statistics
    }
    
    return jsonify({
        "status": "success",
        "data": config_dict,
        "timestamp": datetime.utcnow().isoformat()
    })


@github_bp.route('/config', methods=['PUT'])
@handle_api_errors
def update_configuration():
    """Update GitHub integration configuration"""
    try:
        updates = request.get_json()
        if not updates:
            return jsonify({
                "error": "Bad Request",
                "message": "No configuration updates provided",
                "timestamp": datetime.utcnow().isoformat()
            }), 400
        
        config_manager = GitHubConfigManager()
        config_manager.update_config(updates)
        
        return jsonify({
            "status": "success",
            "message": "Configuration updated successfully",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to update configuration: {str(e)}")
        return jsonify({
            "error": "Configuration Update Failed",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@github_bp.route('/config/validate', methods=['POST'])
@handle_api_errors
def validate_configuration():
    """Validate GitHub integration configuration"""
    config_manager = GitHubConfigManager()
    validation_errors = config_manager.validate_config()
    
    return jsonify({
        "status": "success" if not validation_errors else "validation_failed",
        "valid": len(validation_errors) == 0,
        "errors": validation_errors,
        "timestamp": datetime.utcnow().isoformat()
    })


@github_bp.route('/config/test', methods=['POST'])
@handle_api_errors
def test_configuration():
    """Test GitHub integration configuration"""
    config_manager = GitHubConfigManager()
    test_results = config_manager.test_configuration()
    
    return jsonify({
        "status": "success",
        "data": test_results,
        "timestamp": datetime.utcnow().isoformat()
    })


# Status and Health Endpoints

@github_bp.route('/status', methods=['GET'])
@handle_api_errors
def get_integration_status():
    """Get GitHub integration status"""
    config = get_github_config()
    
    status_data = {
        "enabled": config.enabled,
        "version": config.version,
        "last_sync": config.last_sync,
        "sync_statistics": config.sync_statistics,
        "components": {
            "epic_mapping": config.epic_mapping.enabled,
            "story_mapping": config.story_mapping.enabled,
            "wiki_integration": config.wiki_integration.enabled,
            "real_time_sync": config.synchronization.real_time_webhook,
            "monitoring": config.monitoring.enabled
        }
    }
    
    return jsonify({
        "status": "success",
        "data": status_data,
        "timestamp": datetime.utcnow().isoformat()
    })


@github_bp.route('/health', methods=['GET'])
@handle_api_errors
@require_github_enabled
def health_check():
    """GitHub integration health check"""
    config = get_github_config()
    
    try:
        # Initialize GitHub client for health check
        client = GitHubAPIClient(
            token=config.authentication.token,
            owner=config.repository.owner,
            repo=config.repository.name
        )
        
        # Test connection
        connection_ok = client.test_connection()
        
        # Get rate limit status
        rate_limit = client.get_rate_limit_status()
        
        health_data = {
            "connection": connection_ok,
            "authentication": connection_ok,
            "rate_limit": {
                "remaining": rate_limit.get("resources", {}).get("core", {}).get("remaining", 0),
                "limit": rate_limit.get("resources", {}).get("core", {}).get("limit", 5000),
                "reset": rate_limit.get("resources", {}).get("core", {}).get("reset", 0)
            },
            "repository_access": connection_ok,
            "last_check": datetime.utcnow().isoformat()
        }
        
        return jsonify({
            "status": "healthy" if connection_ok else "unhealthy",
            "data": health_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503


# Projects Management Endpoints

@github_bp.route('/projects', methods=['GET'])
@handle_api_errors
@require_github_enabled
def get_projects():
    """Get GitHub projects"""
    config = get_github_config()
    
    client = GitHubAPIClient(
        token=config.authentication.token,
        owner=config.repository.owner,
        repo=config.repository.name
    )
    
    projects = client.get_projects()
    
    return jsonify({
        "status": "success",
        "data": projects,
        "count": len(projects),
        "timestamp": datetime.utcnow().isoformat()
    })


@github_bp.route('/projects', methods=['POST'])
@handle_api_errors
@require_github_enabled
def create_project():
    """Create GitHub project"""
    config = get_github_config()
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "Project name is required",
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    
    client = GitHubAPIClient(
        token=config.authentication.token,
        owner=config.repository.owner,
        repo=config.repository.name
    )
    
    project = client.create_project(
        name=data['name'],
        body=data.get('description', ''),
        state=data.get('state', 'open')
    )
    
    return jsonify({
        "status": "success",
        "data": project,
        "timestamp": datetime.utcnow().isoformat()
    }), 201


@github_bp.route('/projects/<int:project_id>', methods=['GET'])
@handle_api_errors
@require_github_enabled
def get_project(project_id: int):
    """Get specific GitHub project"""
    config = get_github_config()
    
    client = GitHubAPIClient(
        token=config.authentication.token,
        owner=config.repository.owner,
        repo=config.repository.name
    )
    
    project = client.get_project(project_id)
    
    return jsonify({
        "status": "success",
        "data": project,
        "timestamp": datetime.utcnow().isoformat()
    })


# Issues Management Endpoints

@github_bp.route('/issues', methods=['GET'])
@handle_api_errors
@require_github_enabled
def get_issues():
    """Get GitHub issues with filters"""
    config = get_github_config()
    
    # Extract query parameters
    state = request.args.get('state', 'open')
    labels = request.args.getlist('labels')
    assignee = request.args.get('assignee')
    milestone = request.args.get('milestone')
    
    client = GitHubAPIClient(
        token=config.authentication.token,
        owner=config.repository.owner,
        repo=config.repository.name
    )
    
    issues = client.get_issues(
        state=state,
        labels=labels if labels else None,
        assignee=assignee,
        milestone=milestone
    )
    
    return jsonify({
        "status": "success",
        "data": issues,
        "count": len(issues),
        "filters": {
            "state": state,
            "labels": labels,
            "assignee": assignee,
            "milestone": milestone
        },
        "timestamp": datetime.utcnow().isoformat()
    })


@github_bp.route('/issues', methods=['POST'])
@handle_api_errors
@require_github_enabled
def create_issue():
    """Create GitHub issue"""
    config = get_github_config()
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({
            "error": "Bad Request",
            "message": "Issue title is required",
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    
    client = GitHubAPIClient(
        token=config.authentication.token,
        owner=config.repository.owner,
        repo=config.repository.name
    )
    
    issue = client.create_issue(
        title=data['title'],
        body=data.get('body', ''),
        assignees=data.get('assignees'),
        milestone=data.get('milestone'),
        labels=data.get('labels')
    )
    
    return jsonify({
        "status": "success",
        "data": issue,
        "timestamp": datetime.utcnow().isoformat()
    }), 201


@github_bp.route('/issues/<int:issue_number>', methods=['GET'])
@handle_api_errors
@require_github_enabled
def get_issue(issue_number: int):
    """Get specific GitHub issue"""
    config = get_github_config()
    
    client = GitHubAPIClient(
        token=config.authentication.token,
        owner=config.repository.owner,
        repo=config.repository.name
    )
    
    issue = client.get_issue(issue_number)
    
    return jsonify({
        "status": "success",
        "data": issue,
        "timestamp": datetime.utcnow().isoformat()
    })


# Synchronization Endpoints

@github_bp.route('/sync/manual', methods=['POST'])
@handle_api_errors
@require_github_enabled
def manual_sync():
    """Trigger manual synchronization"""
    config = get_github_config()
    data = request.get_json() or {}
    
    sync_type = data.get('type', 'full')  # full, epics, stories, wiki
    force = data.get('force', False)
    
    try:
        sync_service = GitHubSyncService(config)
        
        if sync_type == 'epics':
            results = sync_service.sync_epics_to_projects(force=force)
        elif sync_type == 'stories':
            results = sync_service.sync_stories_to_issues(force=force)
        elif sync_type == 'wiki':
            results = sync_service.sync_wiki_documentation(force=force)
        else:  # full sync
            results = sync_service.full_sync(force=force)
        
        return jsonify({
            "status": "success",
            "message": f"Manual {sync_type} sync completed",
            "data": results,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Manual sync failed: {str(e)}")
        return jsonify({
            "error": "Sync Failed",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@github_bp.route('/sync/status', methods=['GET'])
@handle_api_errors
@require_github_enabled
def get_sync_status():
    """Get synchronization status"""
    config = get_github_config()
    
    try:
        sync_service = GitHubSyncService(config)
        status = sync_service.get_sync_status()
        
        return jsonify({
            "status": "success",
            "data": status,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get sync status: {str(e)}")
        return jsonify({
            "error": "Status Retrieval Failed",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@github_bp.route('/sync/history', methods=['GET'])
@handle_api_errors
@require_github_enabled
def get_sync_history():
    """Get synchronization history"""
    config = get_github_config()
    
    # Extract query parameters
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    sync_type = request.args.get('type')
    
    try:
        sync_service = GitHubSyncService(config)
        history = sync_service.get_sync_history(
            limit=limit,
            offset=offset,
            sync_type=sync_type
        )
        
        return jsonify({
            "status": "success",
            "data": history,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": len(history)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get sync history: {str(e)}")
        return jsonify({
            "error": "History Retrieval Failed",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


# Webhook Endpoints

@github_bp.route('/webhook', methods=['POST'])
@handle_api_errors
def handle_webhook():
    """Handle GitHub webhook events"""
    config = get_github_config()
    
    if not config.enabled or not config.synchronization.real_time_webhook:
        return jsonify({
            "error": "Webhooks Disabled",
            "message": "Real-time webhooks are not enabled",
            "timestamp": datetime.utcnow().isoformat()
        }), 403
    
    # Verify webhook signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        return jsonify({
            "error": "Missing Signature",
            "message": "Webhook signature is required",
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    
    payload = request.get_data()
    
    try:
        client = GitHubAPIClient(
            token=config.authentication.token,
            owner=config.repository.owner,
            repo=config.repository.name
        )
        
        if not client.verify_webhook_signature(
            payload, 
            signature, 
            config.authentication.webhook_secret
        ):
            return jsonify({
                "error": "Invalid Signature",
                "message": "Webhook signature verification failed",
                "timestamp": datetime.utcnow().isoformat()
            }), 403
        
        # Process webhook event
        event_type = request.headers.get('X-GitHub-Event')
        payload_data = request.get_json()
        
        sync_service = GitHubSyncService(config)
        result = sync_service.process_webhook_event(event_type, payload_data)
        
        return jsonify({
            "status": "success",
            "message": f"Webhook event {event_type} processed",
            "data": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}")
        return jsonify({
            "error": "Webhook Processing Failed",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


# Metrics and Monitoring Endpoints

@github_bp.route('/metrics', methods=['GET'])
@handle_api_errors
@require_github_enabled
def get_metrics():
    """Get GitHub integration metrics"""
    config = get_github_config()
    
    if not config.monitoring.metrics_collection:
        return jsonify({
            "error": "Metrics Disabled",
            "message": "Metrics collection is not enabled",
            "timestamp": datetime.utcnow().isoformat()
        }), 403
    
    try:
        sync_service = GitHubSyncService(config)
        metrics = sync_service.get_metrics()
        
        return jsonify({
            "status": "success",
            "data": metrics,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        return jsonify({
            "error": "Metrics Retrieval Failed",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


# Error handlers
@github_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint was not found",
        "timestamp": datetime.utcnow().isoformat()
    }), 404


@github_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method Not Allowed",
        "message": "The requested method is not allowed for this endpoint",
        "timestamp": datetime.utcnow().isoformat()
    }), 405