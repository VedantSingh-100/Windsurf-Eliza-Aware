"""
Operations module - Category-based API operation tools.

This module provides 19 consolidated operation tools that expose 75 API endpoints.
Each tool routes to multiple client methods via the operation parameter.

Tools (Original 7):
- chat_operations: Chat with agents (4 operations)
- analytics_operations: Agent analytics and activity (6 operations)
- a2a_operations: Agent-to-Agent server management (4 operations)
- nugget_execution: Execute nuggets (4 operations)
- document_extended: Extended document operations (7 operations)
- chunk_operations: Document chunk management (3 operations)
- system_operations: System info (4 operations)

Tools (New 12):
- agent_crud: Agent CRUD operations (6 operations)
- nugget_crud: Nugget CRUD operations (4 operations)
- function_crud: Function CRUD operations (4 operations)
- document_crud: Document CRUD operations (5 operations)
- identity_operations: Agent identity management (2 operations)
- access_operations: Access control (4 operations)
- ideas_operations: Ideas and voting (4 operations)
- hashes_operations: Merkle DAG hashes (4 operations)
- index_operations: Vector index search (2 operations)
- promotion_operations: Agent promotion/import (2 operations)
- advanced_operations: Back-testing, computer use (3 operations)
- discovery_operations: Agent discovery (3 operations)

These tools are STANDALONE - they don't go through eliza_workflow.
They reuse credentials from workflow state when available.
"""

from tools.registry.category_router import (
    OPERATION_TOOLS,
    CATEGORY_HANDLERS,
    handle_category_operation,
    # Original 7 handlers
    handle_chat_operations,
    handle_analytics_operations,
    handle_a2a_operations,
    handle_nugget_execution,
    handle_document_extended,
    handle_chunk_operations,
    handle_system_operations,
    # New 12 handlers
    handle_agent_crud,
    handle_nugget_crud,
    handle_function_crud,
    handle_document_crud,
    handle_identity_operations,
    handle_access_operations,
    handle_ideas_operations,
    handle_hashes_operations,
    handle_index_operations,
    handle_promotion_operations,
    handle_advanced_operations,
    handle_discovery_operations,
)

__all__ = [
    "OPERATION_TOOLS",
    "CATEGORY_HANDLERS",
    "handle_category_operation",
    # Original 7 handlers
    "handle_chat_operations",
    "handle_analytics_operations",
    "handle_a2a_operations",
    "handle_nugget_execution",
    "handle_document_extended",
    "handle_chunk_operations",
    "handle_system_operations",
    # New 12 handlers
    "handle_agent_crud",
    "handle_nugget_crud",
    "handle_function_crud",
    "handle_document_crud",
    "handle_identity_operations",
    "handle_access_operations",
    "handle_ideas_operations",
    "handle_hashes_operations",
    "handle_index_operations",
    "handle_promotion_operations",
    "handle_advanced_operations",
    "handle_discovery_operations",
]
