"""
Standardized API response builders.

Provides consistent response formatting across all API endpoints.
"""

from typing import Any, Dict, Optional
from flask import jsonify


def success_response(
    data: Any,
    message: Optional[str] = None,
    **extra_fields
) -> tuple:
    """
    Create a standardized success response.

    Args:
        data: The response data
        message: Optional success message
        extra_fields: Additional fields to include in response

    Returns:
        Tuple of (response, status_code)
    """
    response = {'data': data, 'success': True}

    if message:
        response['message'] = message

    response.update(extra_fields)

    return jsonify(response), 200


def error_response(
    message: str,
    status_code: int = 500,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> tuple:
    """
    Create a standardized error response.

    Args:
        message: Error message
        status_code: HTTP status code
        error_code: Optional error code for client handling
        details: Optional additional error details

    Returns:
        Tuple of (response, status_code)
    """
    response = {
        'error': message,
        'success': False,
    }

    if error_code:
        response['error_code'] = error_code

    if details:
        response['details'] = details

    return jsonify(response), status_code


def service_unavailable(service_name: str) -> tuple:
    """
    Create a service unavailable response.

    Args:
        service_name: Name of the unavailable service

    Returns:
        Tuple of (response, 503)
    """
    return error_response(
        message=f'{service_name} not initialized',
        status_code=503,
        error_code='SERVICE_UNAVAILABLE'
    )


def validation_error(message: str, field: Optional[str] = None) -> tuple:
    """
    Create a validation error response.

    Args:
        message: Validation error message
        field: Optional field name that failed validation

    Returns:
        Tuple of (response, 400)
    """
    details = {'field': field} if field else None
    return error_response(
        message=message,
        status_code=400,
        error_code='VALIDATION_ERROR',
        details=details
    )


def not_found(resource: str, identifier: Optional[str] = None) -> tuple:
    """
    Create a not found response.

    Args:
        resource: Type of resource not found
        identifier: Optional resource identifier

    Returns:
        Tuple of (response, 404)
    """
    if identifier:
        message = f'{resource} with id {identifier} not found'
    else:
        message = f'{resource} not found'

    return error_response(
        message=message,
        status_code=404,
        error_code='NOT_FOUND'
    )


def paginated_response(
    data: list,
    total: int,
    page: int,
    per_page: int,
    **extra_fields
) -> tuple:
    """
    Create a paginated response.

    Args:
        data: List of items for current page
        total: Total number of items
        page: Current page number
        per_page: Items per page
        extra_fields: Additional fields to include

    Returns:
        Tuple of (response, status_code)
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    response = {
        'data': data,
        'success': True,
        'pagination': {
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        }
    }

    response.update(extra_fields)

    return jsonify(response), 200
