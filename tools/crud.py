"""
CRUD MCP Tools

MCP tools for read, update, and delete operations on agents, nuggets, and functions.
All tools perform validation before making API calls.

TIER 2 TOOLS: These are READ/EXECUTE operations that support lazy credential initialization.
They use resolve_workspace_path() and ensure_credentials() for smart credential handling.

TOOLS:
- Agent: get_agent, update_agent, delete_agent, list_agents
- Nugget: get_nugget, update_nugget, delete_nugget, list_nuggets
- Function: get_function, delete_function, list_functions
"""

from mcp.types import Tool
from typing import Dict, Any, List, Tuple, Optional
import json

from api.client import get_client
from validation import (
    validate_common_inputs,
    validate_agent_id,
    format_validation_errors,
)
from tools.workflow_state import (
    resolve_workspace_path,
    ensure_credentials,
)


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

CRUD_TOOLS: List[Tool] = [
    # -------------------------------------------------------------------------
    # AGENT CRUD
    # -------------------------------------------------------------------------
    Tool(
        name="get_agent",
        description="""Get agent details by ID.

Returns agent configuration including: name, description, model, retrieverStrategy,
controlFlags, systemPrompt, and created/updated timestamps.

USE THIS WHEN: User wants to view agent configuration or verify agent exists.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent to retrieve"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id"]
        }
    ),
    Tool(
        name="update_agent",
        description="""Update agent configuration.

UPDATABLE FIELDS:
- name: Agent display name
- description: Agent description
- systemPrompt: System prompt (instructions for the agent)
- model: LLM model name (use get_valid_values for options)
- controlFlags: List of control flags
- retrieverStrategy: RAG strategy (STANDARD, REASON, etc.)

USE THIS WHEN: User wants to modify agent settings, update prompts, or change model.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent to update"
                },
                "updates": {
                    "type": "object",
                    "description": "Fields to update (name, description, systemPrompt, model, controlFlags, retrieverStrategy)",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "systemPrompt": {"type": "string"},
                        "model": {"type": "string"},
                        "controlFlags": {"type": "array", "items": {"type": "string"}},
                        "retrieverStrategy": {"type": "string"}
                    }
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id", "updates"]
        }
    ),
    Tool(
        name="delete_agent",
        description="""Delete an agent permanently.

WARNING: This action is irreversible. All nuggets and functions on the agent will also be deleted.

USE THIS WHEN: User explicitly requests agent deletion.
REQUIRES: confirm=true to prevent accidental deletion.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent to delete"
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to confirm deletion"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id", "confirm"]
        }
    ),
    Tool(
        name="list_agents",
        description="""List all agents for the current user.

Returns a paginated list of agents with their IDs, names, and basic info.

USE THIS WHEN: User wants to see their agents or find an agent by name.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "description": "Pagination offset"
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Number of results to return"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token"]
        }
    ),

    # -------------------------------------------------------------------------
    # NUGGET CRUD
    # -------------------------------------------------------------------------
    Tool(
        name="get_nugget",
        description="""Get nugget details including code.

Returns the nugget's label, description, code, and configuration.

USE THIS WHEN: User wants to view nugget code or verify nugget configuration.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "nugget_id": {
                    "type": "string",
                    "description": "ID of the nugget to retrieve"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id", "nugget_id"]
        }
    ),
    Tool(
        name="update_nugget",
        description="""Update nugget code or configuration.

UPDATABLE FIELDS:
- label: Nugget display name
- description: What the nugget does
- call: Code block with @type, language, and code

USE THIS WHEN: User wants to modify nugget code, fix bugs, or update behavior.
NOTE: For major changes, consider using create_nugget to generate new code.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "nugget_id": {
                    "type": "string",
                    "description": "ID of the nugget to update"
                },
                "updates": {
                    "type": "object",
                    "description": "Fields to update (label, description, call)",
                    "properties": {
                        "label": {"type": "string"},
                        "description": {"type": "string"},
                        "call": {
                            "type": "object",
                            "properties": {
                                "@type": {"type": "string", "enum": ["code"]},
                                "language": {"type": "string", "enum": ["JavaScript"]},
                                "code": {"type": "string"}
                            }
                        }
                    }
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id", "nugget_id", "updates"]
        }
    ),
    Tool(
        name="delete_nugget",
        description="""Delete a nugget from an agent.

WARNING: This also removes any functions that reference this nugget.

USE THIS WHEN: User explicitly requests nugget deletion.
REQUIRES: confirm=true to prevent accidental deletion.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "nugget_id": {
                    "type": "string",
                    "description": "ID of the nugget to delete"
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to confirm deletion"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id", "nugget_id", "confirm"]
        }
    ),
    Tool(
        name="list_nuggets",
        description="""List all nuggets on an agent.

Returns a paginated list of nuggets with their IDs, labels, and descriptions.

USE THIS WHEN: User wants to see available nuggets or find a nugget by name.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "description": "Pagination offset"
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Number of results to return"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id"]
        }
    ),

    # -------------------------------------------------------------------------
    # FUNCTION CRUD
    # -------------------------------------------------------------------------
    Tool(
        name="get_function",
        description="""Get function details by ID.

Returns the function's name, label, prompt, parameters, and type.

USE THIS WHEN: User wants to view function configuration.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "function_id": {
                    "type": "string",
                    "description": "ID of the function to retrieve"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id", "function_id"]
        }
    ),
    Tool(
        name="delete_function",
        description="""Delete a function from an agent.

NOTE: The underlying nugget remains; only the function binding is removed.

USE THIS WHEN: User wants to remove a function but keep the nugget code.
REQUIRES: confirm=true to prevent accidental deletion.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "function_id": {
                    "type": "string",
                    "description": "ID of the function to delete"
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to confirm deletion"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id", "function_id", "confirm"]
        }
    ),
    Tool(
        name="list_functions",
        description="""List all functions on an agent.

Returns a list of functions with their IDs, names, labels, and types.

USE THIS WHEN: User wants to see available functions on an agent.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "Eliza JWT token for authentication"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "default": "QA",
                    "description": "Environment"
                }
            },
            "required": ["jwt_token", "agent_id"]
        }
    ),
]


# =============================================================================
# TOOL HANDLERS
# =============================================================================

def _validate_and_get_client(args: Dict[str, Any], require_agent: bool = True) -> Tuple[Optional[Any], Optional[str]]:
    """
    Common validation and client creation with smart credential handling.

    Uses resolve_workspace_path() and ensure_credentials() for lazy initialization.
    If jwt_token is provided directly, it can work without workspace state.

    Returns:
        Tuple[ElizaClient, None] on success
        Tuple[None, str] on validation failure (error message)
    """
    jwt_token = args.get("jwt_token", "")
    agent_id = args.get("agent_id", "")
    env = args.get("env", "QA")

    # Try to resolve workspace and use ensure_credentials for lazy init
    resolved_workspace, ws_error = resolve_workspace_path(args)

    # ENFORCE workspace path - must have .eliza/ tracking
    if ws_error:
        return None, json.dumps({
            "status": "WORKSPACE_REQUIRED",
            "error": ws_error,
            "fix": "Provide workspace_path parameter pointing to your project directory. "
                   "Example: workspace_path='/path/to/your/project'. "
                   "Or run eliza_workflow(action='start') first to initialize credentials."
        })

    if resolved_workspace:
        # Workspace found - use ensure_credentials for lazy init
        success, creds, cred_error = ensure_credentials(
            resolved_workspace,
            jwt_token=jwt_token if jwt_token else None,
            agent_id=agent_id if agent_id else None,
            env=env
        )

        if success:
            # Use credentials returned by ensure_credentials (centralized reading)
            jwt_token = creds.get("jwt_token") or jwt_token
            agent_id = agent_id or creds.get("agent_id", "")
            env = creds.get("env", env)
        else:
            # ensure_credentials failed - return specific error instead of generic validation
            return None, json.dumps({
                "status": "CREDENTIALS_REQUIRED",
                "error": cred_error,
                "fix": "Provide jwt_token parameter, or run eliza_workflow(action='start') first to initialize credentials."
            })

    # Validate inputs
    if require_agent:
        validation = validate_common_inputs(jwt_token, agent_id, env)
    else:
        # For list_agents, we don't need agent_id
        from validation import validate_jwt_token, validate_env
        jwt_result = validate_jwt_token(jwt_token)
        env_result = validate_env(env)
        validation = type('ValidationResult', (), {
            'valid': jwt_result.valid and env_result.valid,
            'errors': jwt_result.errors + env_result.errors,
            'warnings': jwt_result.warnings + env_result.warnings
        })()

    if not validation.valid:
        # Add helpful message about workspace/credentials
        error_msg = format_validation_errors(validation)
        if not jwt_token:
            error_msg += "\n\nTIP: Provide jwt_token directly, or run eliza_workflow(action='start') to initialize credentials."
        return None, error_msg

    # Create client
    client = get_client(jwt_token, env)
    return client, None


def _format_api_error(error_dict: Dict) -> str:
    """Format API error response as readable string."""
    error = error_dict.get("error", "Unknown error")
    fix = error_dict.get("fix", "")
    details = error_dict.get("details", "")

    result = f"ERROR: {error}"
    if fix:
        result += f"\nFIX: {fix}"
    if details and isinstance(details, dict):
        result += f"\nDETAILS: {json.dumps(details, indent=2)}"
    elif details:
        result += f"\nDETAILS: {details}"

    return result


# -------------------------------------------------------------------------
# AGENT HANDLERS
# -------------------------------------------------------------------------

def handle_get_agent(args: Dict[str, Any]) -> str:
    """Get agent details."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]
    success, result = client.get_agent(agent_id)

    if not success:
        return _format_api_error(result)

    # Format agent details
    return f"""AGENT DETAILS

ID: {result.get('agentId', agent_id)}
Name: {result.get('name', 'N/A')}
Description: {result.get('description', 'N/A')}
Model: {result.get('model', 'N/A')}
Strategy: {result.get('retrieverStrategy', 'N/A')}
Control Flags: {', '.join(result.get('controlFlags', [])) or 'None'}
Created: {result.get('createdAt', 'N/A')}
Updated: {result.get('updatedAt', 'N/A')}

System Prompt:
{result.get('systemPrompt', 'N/A')}"""


def handle_update_agent(args: Dict[str, Any]) -> str:
    """Update agent configuration."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]
    updates = args.get("updates", {})

    if not updates:
        return "ERROR: No updates provided. Specify at least one field to update."

    success, result = client.update_agent(agent_id, updates)

    if not success:
        return _format_api_error(result)

    return f"""AGENT UPDATED SUCCESSFULLY

Agent ID: {agent_id}
Updated fields: {', '.join(updates.keys())}"""


def handle_delete_agent(args: Dict[str, Any]) -> str:
    """Delete an agent."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]
    confirm = args.get("confirm", False)

    if not confirm:
        return """DELETE CANCELLED

You must set confirm=true to delete an agent.
WARNING: This action is irreversible. All nuggets and functions will be deleted."""

    success, result = client.delete_agent(agent_id)

    if not success:
        return _format_api_error(result)

    return f"""AGENT DELETED SUCCESSFULLY

Agent ID: {agent_id}
All associated nuggets and functions have been removed."""


def handle_list_agents(args: Dict[str, Any]) -> str:
    """List all agents."""
    client, error = _validate_and_get_client(args, require_agent=False)
    if error:
        return f"VALIDATION FAILED\n{error}"

    offset = args.get("offset", 0)
    limit = args.get("limit", 20)

    success, result = client.list_agents(offset, limit)

    if not success:
        return _format_api_error(result)

    # Format agent list
    agents = result.get("agents", result.get("data", []))
    if not agents:
        return "No agents found."

    lines = [f"AGENTS (showing {len(agents)} results)\n"]
    for agent in agents:
        lines.append(f"- {agent.get('name', 'Unnamed')}")
        lines.append(f"  ID: {agent.get('agentId', 'N/A')}")
        lines.append(f"  Strategy: {agent.get('retrieverStrategy', 'N/A')}")
        lines.append("")

    return "\n".join(lines)


# -------------------------------------------------------------------------
# NUGGET HANDLERS
# -------------------------------------------------------------------------

def handle_get_nugget(args: Dict[str, Any]) -> str:
    """Get nugget details."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]
    nugget_id = args.get("nugget_id", "")

    if not nugget_id:
        return "ERROR: nugget_id is required"

    success, result = client.get_nugget(agent_id, nugget_id)

    if not success:
        return _format_api_error(result)

    # Extract code from call block
    call = result.get("call", {})
    code = call.get("code", "N/A") if isinstance(call, dict) else "N/A"

    return f"""NUGGET DETAILS

ID: {result.get('nuggetId', nugget_id)}
Label: {result.get('label', 'N/A')}
Description: {result.get('description', 'N/A')}
Language: {call.get('language', 'JavaScript') if isinstance(call, dict) else 'JavaScript'}

CODE:
```javascript
{code}
```"""


def handle_update_nugget(args: Dict[str, Any]) -> str:
    """Update nugget code or configuration."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]
    nugget_id = args.get("nugget_id", "")
    updates = args.get("updates", {})

    if not nugget_id:
        return "ERROR: nugget_id is required"

    if not updates:
        return "ERROR: No updates provided. Specify label, description, or call to update."

    success, result = client.update_nugget(agent_id, nugget_id, updates)

    if not success:
        return _format_api_error(result)

    return f"""NUGGET UPDATED SUCCESSFULLY

Agent ID: {agent_id}
Nugget ID: {nugget_id}
Updated fields: {', '.join(updates.keys())}"""


def handle_delete_nugget(args: Dict[str, Any]) -> str:
    """Delete a nugget."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]
    nugget_id = args.get("nugget_id", "")
    confirm = args.get("confirm", False)

    if not nugget_id:
        return "ERROR: nugget_id is required"

    if not confirm:
        return """DELETE CANCELLED

You must set confirm=true to delete a nugget.
WARNING: This will also remove any functions that reference this nugget."""

    success, result = client.delete_nugget(agent_id, nugget_id)

    if not success:
        return _format_api_error(result)

    return f"""NUGGET DELETED SUCCESSFULLY

Agent ID: {agent_id}
Nugget ID: {nugget_id}"""


def handle_list_nuggets(args: Dict[str, Any]) -> str:
    """List nuggets on an agent."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]
    offset = args.get("offset", 0)
    limit = args.get("limit", 20)

    success, result = client.list_nuggets(agent_id, offset, limit)

    if not success:
        return _format_api_error(result)

    # Format nugget list
    nuggets = result.get("nuggets", result.get("data", []))
    if not nuggets:
        return f"No nuggets found on agent {agent_id}."

    lines = [f"NUGGETS ON AGENT {agent_id} (showing {len(nuggets)} results)\n"]
    for nugget in nuggets:
        lines.append(f"- {nugget.get('label', 'Unnamed')}")
        lines.append(f"  ID: {nugget.get('nuggetId', 'N/A')}")
        lines.append(f"  Description: {nugget.get('description', 'N/A')[:100]}")
        lines.append("")

    return "\n".join(lines)


# -------------------------------------------------------------------------
# FUNCTION HANDLERS
# -------------------------------------------------------------------------

def handle_get_function(args: Dict[str, Any]) -> str:
    """Get function details."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]
    function_id = args.get("function_id", "")

    if not function_id:
        return "ERROR: function_id is required"

    success, result = client.get_function(agent_id, function_id)

    if not success:
        return _format_api_error(result)

    # Format parameters
    params = result.get("params", [])
    params_str = ""
    if params:
        for p in params:
            params_str += f"\n  - {p.get('paramNameKey', 'N/A')} ({p.get('paramType', 'string')}): {p.get('paramDescription', 'N/A')}"
    else:
        params_str = "\n  (none)"

    return f"""FUNCTION DETAILS

ID: {result.get('functionId', function_id)}
Name: {result.get('funcNameKey', 'N/A')}
Label: {result.get('label', 'N/A')}
Type: {result.get('functionType', 'N/A')}
Prompt: {result.get('prompt', 'N/A')}

Parameters:{params_str}"""


def handle_delete_function(args: Dict[str, Any]) -> str:
    """Delete a function."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]
    function_id = args.get("function_id", "")
    confirm = args.get("confirm", False)

    if not function_id:
        return "ERROR: function_id is required"

    if not confirm:
        return """DELETE CANCELLED

You must set confirm=true to delete a function.
NOTE: The underlying nugget will remain; only the function binding is removed."""

    success, result = client.delete_function(agent_id, function_id)

    if not success:
        return _format_api_error(result)

    return f"""FUNCTION DELETED SUCCESSFULLY

Agent ID: {agent_id}
Function ID: {function_id}
NOTE: The underlying nugget (if any) still exists."""


def handle_list_functions(args: Dict[str, Any]) -> str:
    """List functions on an agent."""
    client, error = _validate_and_get_client(args)
    if error:
        return f"VALIDATION FAILED\n{error}"

    agent_id = args["agent_id"]

    success, result = client.list_functions(agent_id)

    if not success:
        return _format_api_error(result)

    # Format function list
    functions = result.get("functions", result.get("data", result if isinstance(result, list) else []))
    if not functions:
        return f"No functions found on agent {agent_id}."

    lines = [f"FUNCTIONS ON AGENT {agent_id} (showing {len(functions)} results)\n"]
    for func in functions:
        lines.append(f"- {func.get('label', 'Unnamed')}")
        lines.append(f"  ID: {func.get('functionId', 'N/A')}")
        lines.append(f"  Name: {func.get('funcNameKey', 'N/A')}")
        lines.append(f"  Type: {func.get('functionType', 'N/A')}")
        lines.append("")

    return "\n".join(lines)
