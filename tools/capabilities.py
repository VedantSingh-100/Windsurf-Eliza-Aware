"""
Capability Category Tools

Consolidated capability tools that group related ez* functions into categories.
Each category tool uses a sub_type parameter to specify the exact capability.

BEFORE: 28 individual tools (create_email_function, create_database_function, etc.)
AFTER: 6 category tools with sub_type parameter

This makes tool discovery easier for Windsurf while maintaining full functionality.
"""

from mcp.types import Tool
from typing import Dict, Any, List

# =============================================================================
# CATEGORY FUNCTION MAPPINGS
# Maps (category_tool, sub_type) -> list of ez* functions to use
# =============================================================================

CATEGORY_FUNCTION_MAP = {
    "create_communication_capability": {
        "email": ["ezMail"],
        "notification": ["ezNotify"],
        "chat": ["ezChat"],
        "confirmation": ["ezConfirm"],
        "teams_slack": ["ezComms"],
    },
    "create_integration_capability": {
        "rest_api": ["ezApi"],
        "database": ["ezSqlSelect"],
        "jira": ["ezJiraSupport"],
        "sharepoint": ["ezSharePoint"],
        "external_api": ["ezNexenApi"],
        "copilot": ["ezCopilotChat"],
    },
    "create_ai_capability": {
        "llm_chat": ["ezChatCompletions"],
        "image_analysis": ["ezImageToText"],
        "image_generation": ["ezTextToImage"],
        "video_generation": ["ezTextToVideo"],
        "text_to_speech": ["ezTextToSpeech"],
        "embeddings": ["ezEmbeddings"],
    },
    "create_automation_capability": {
        "browser": ["ezBrowser"],
        "desktop": ["ezComputer"],
        "python": ["ezPython"],
        "javascript": ["ezJavaScript"],
        "research": ["ezGenAISearch"],
    },
    "create_data_capability": {
        "session_save": ["ezSaveSessionData"],
        "session_get": ["ezGetSessionData"],
        "session_both": ["ezSaveSessionData", "ezGetSessionData"],
        "data_query": ["ezDataQuery"],
        "data_create": ["ezDataCreate"],
        "calculation": [],  # PYTHON_STATIC, no ez* functions
    },
    "create_interop_capability": {
        "agent_to_agent": ["ezA2A"],
        "nugget_call": ["ezNugget"],
        "function_call": ["ezFunction"],
        "mcp_server": ["ezMCP"],
        "agent_chat": ["ezChat"],
    },
}

# Search queries for each sub_type (used in guidance response)
SUBTYPE_SEARCH_QUERIES = {
    # Communication
    "email": "email mail send notification",
    "notification": "notify notification alert push",
    "chat": "chat message send",
    "confirmation": "confirm dialog approval user",
    "teams_slack": "teams slack comms messaging",
    # Integration
    "rest_api": "http rest api call",
    "database": "sql database query select",
    "jira": "jira ticket issue support",
    "sharepoint": "sharepoint document site",
    "external_api": "nexen api external authenticated",
    "copilot": "copilot chat query",
    # AI
    "llm_chat": "chat completions llm gpt",
    "image_analysis": "image ocr analyze vision text",
    "image_generation": "generate image text dalle",
    "video_generation": "generate video text",
    "text_to_speech": "text speech audio voice tts",
    "embeddings": "embeddings vector semantic",
    # Automation
    "browser": "browser automation web scraping",
    "desktop": "computer desktop click type rpa",
    "python": "python execute code dynamic",
    "javascript": "javascript execute code",
    "research": "deep research genai comprehensive",
    # Data
    "session_save": "session save data persist",
    "session_get": "session get data retrieve",
    "session_both": "session save get data",
    "data_query": "data query search find",
    "data_create": "data create insert new",
    "calculation": "calculate math date format local",
    # Interop
    "agent_to_agent": "a2a agent protocol inter",
    "nugget_call": "nugget call chain invoke",
    "function_call": "function call invoke",
    "mcp_server": "mcp protocol server tool",
    "agent_chat": "agent chat call delegate",
}

# =============================================================================
# CATEGORY TOOL DEFINITIONS
# =============================================================================

CATEGORY_TOOLS: List[Tool] = [
    # =========================================================================
    # 1. COMMUNICATION CAPABILITY
    # =========================================================================
    Tool(
        name="create_communication_capability",
        description="""Create functions for COMMUNICATION: email, notifications, chat, confirmations.

SUB-TYPES:
- email: Send emails (ezMail) - requires email address
- notification: Push notifications/alerts (ezNotify)
- chat: Chat messages (ezChat)
- confirmation: User confirmation dialogs (ezConfirm)
- teams_slack: Microsoft Teams/Slack messages (ezComms)

USE THIS WHEN: User wants to send messages, alerts, get user confirmation, or communicate.

EXAMPLE TRIGGERS:
- "send email" -> sub_type="email"
- "notify user" -> sub_type="notification"
- "ask for confirmation" -> sub_type="confirmation"
- "send teams message" -> sub_type="teams_slack"

DO NOT USE: For searching/research - use search_ez_functions instead.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "User's Eliza JWT token"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent to add capability to"
                },
                "sub_type": {
                    "type": "string",
                    "enum": ["email", "notification", "chat", "confirmation", "teams_slack"],
                    "description": "Which communication type to create"
                },
                "email_address": {
                    "type": "string",
                    "description": "Email address (required for email sub_type)"
                },
                "label": {
                    "type": "string",
                    "description": "Display name for the function"
                },
                "prompt": {
                    "type": "string",
                    "description": "When the LLM should use this function"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"],
                    "description": "Eliza environment (default: QA)"
                }
            },
            "required": ["jwt_token", "agent_id", "sub_type"]
        }
    ),

    # =========================================================================
    # 2. INTEGRATION CAPABILITY
    # =========================================================================
    Tool(
        name="create_integration_capability",
        description="""Create functions for INTEGRATIONS: APIs, databases, enterprise systems.

SUB-TYPES:
- rest_api: HTTP/REST API calls (ezApi)
- database: SQL database queries (ezSqlSelect) - requires data_source_name
- jira: Jira ticket operations (ezJiraSupport) - requires secrets
- sharepoint: SharePoint document access (ezSharePoint) - requires identity
- external_api: Authenticated external APIs (ezNexenApi) - requires secrets_path
- copilot: Copilot chat/queries (ezCopilotChat)

USE THIS WHEN: User wants to call APIs, query databases, or integrate with enterprise systems.

EXAMPLE TRIGGERS:
- "call API" -> sub_type="rest_api"
- "query database" -> sub_type="database"
- "create Jira ticket" -> sub_type="jira"
- "get SharePoint document" -> sub_type="sharepoint"

DO NOT USE: For LLM/AI capabilities - use create_ai_capability instead.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "User's Eliza JWT token"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "sub_type": {
                    "type": "string",
                    "enum": ["rest_api", "database", "jira", "sharepoint", "external_api", "copilot"],
                    "description": "Which integration type"
                },
                "data_source_name": {
                    "type": "string",
                    "description": "Database source name (for database sub_type)"
                },
                "secrets_path": {
                    "type": "string",
                    "description": "Path to secrets (for external_api sub_type)"
                },
                "endpoint_url": {
                    "type": "string",
                    "description": "API endpoint URL (for rest_api sub_type)"
                },
                "label": {
                    "type": "string",
                    "description": "Display name for the function"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"]
                }
            },
            "required": ["jwt_token", "agent_id", "sub_type"]
        }
    ),

    # =========================================================================
    # 3. AI CAPABILITY
    # =========================================================================
    Tool(
        name="create_ai_capability",
        description="""Create functions for AI/ML: LLM, vision, image generation, audio.

SUB-TYPES:
- llm_chat: LLM chat completions (ezChatCompletions) - for summarization, analysis, generation
- image_analysis: OCR, image description (ezImageToText)
- image_generation: Text-to-image (ezTextToImage)
- video_generation: Text-to-video (ezTextToVideo)
- text_to_speech: TTS audio generation (ezTextToSpeech)
- embeddings: Vector embeddings (ezEmbeddings)

USE THIS WHEN: User wants AI capabilities like summarization, image analysis, content generation.

EXAMPLE TRIGGERS:
- "summarize text" -> sub_type="llm_chat"
- "analyze image" -> sub_type="image_analysis"
- "generate image" -> sub_type="image_generation"
- "create embeddings" -> sub_type="embeddings"

DO NOT USE: For internet search - use search_ez_functions with "ezInternetSearch".""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "User's Eliza JWT token"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "sub_type": {
                    "type": "string",
                    "enum": ["llm_chat", "image_analysis", "image_generation", "video_generation", "text_to_speech", "embeddings"],
                    "description": "Which AI capability"
                },
                "model": {
                    "type": "string",
                    "description": "Model to use (e.g., openai-gpt-4o, bnym-llama-3.3-70b-instruct)"
                },
                "label": {
                    "type": "string",
                    "description": "Display name"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"]
                }
            },
            "required": ["jwt_token", "agent_id", "sub_type"]
        }
    ),

    # =========================================================================
    # 4. AUTOMATION CAPABILITY
    # =========================================================================
    Tool(
        name="create_automation_capability",
        description="""Create functions for AUTOMATION: browser, desktop, code execution, research.

SUB-TYPES:
- browser: Browser automation/web scraping (ezBrowser)
- desktop: Desktop automation/RPA - clicks, typing (ezComputer)
- python: Dynamic Python code execution (ezPython)
- javascript: Dynamic JavaScript execution (ezJavaScript)
- research: Deep/comprehensive research (ezGenAISearch)

USE THIS WHEN: User wants automation, web scraping, or dynamic code execution.

EXAMPLE TRIGGERS:
- "scrape website" -> sub_type="browser"
- "automate desktop" -> sub_type="desktop"
- "run Python code" -> sub_type="python"
- "deep research" -> sub_type="research"

STATUS NOTE: Some automation features may be limited in QA environment.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "User's Eliza JWT token"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "sub_type": {
                    "type": "string",
                    "enum": ["browser", "desktop", "python", "javascript", "research"],
                    "description": "Which automation type"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (for browser/desktop)"
                },
                "label": {
                    "type": "string",
                    "description": "Display name"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"]
                }
            },
            "required": ["jwt_token", "agent_id", "sub_type"]
        }
    ),

    # =========================================================================
    # 5. DATA CAPABILITY
    # =========================================================================
    Tool(
        name="create_data_capability",
        description="""Create functions for DATA: session persistence, data management, calculations.

SUB-TYPES:
- session_save: Save data to session (ezSaveSessionData)
- session_get: Get data from session (ezGetSessionData)
- session_both: Both save and get session data
- data_query: Query/search data records (ezDataQuery)
- data_create: Create new data records (ezDataCreate)
- calculation: Local calculations/math (PYTHON_STATIC - no external calls)

USE THIS WHEN: User wants to persist state, manage data, or do calculations.

EXAMPLE TRIGGERS:
- "remember user preference" -> sub_type="session_save"
- "get saved data" -> sub_type="session_get"
- "create data record" -> sub_type="data_create"
- "calculate total" -> sub_type="calculation"

NOTE: "calculation" creates PYTHON_STATIC function - cannot call external services.""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "User's Eliza JWT token"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "sub_type": {
                    "type": "string",
                    "enum": ["session_save", "session_get", "session_both", "data_query", "data_create", "calculation"],
                    "description": "Which data capability"
                },
                "calculation_description": {
                    "type": "string",
                    "description": "What to calculate (for calculation sub_type)"
                },
                "label": {
                    "type": "string",
                    "description": "Display name"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"]
                }
            },
            "required": ["jwt_token", "agent_id", "sub_type"]
        }
    ),

    # =========================================================================
    # 6. INTEROP CAPABILITY
    # =========================================================================
    Tool(
        name="create_interop_capability",
        description="""Create functions for INTER-SYSTEM communication: agent-to-agent, nugget chains, MCP.

SUB-TYPES:
- agent_to_agent: A2A protocol communication (ezA2A) - requires a2a_server_id
- nugget_call: Call another nugget (ezNugget) - requires target_nugget_id
- function_call: Invoke another function (ezFunction)
- mcp_server: Call MCP server tools (ezMCP) - requires mcp_server_id, mcp_tool_name
- agent_chat: Chat with another agent (ezChat) - requires target_agent_id

USE THIS WHEN: User wants multi-agent workflows, nugget chaining, or MCP integration.

EXAMPLE TRIGGERS:
- "call another agent" -> sub_type="agent_chat"
- "chain nuggets" -> sub_type="nugget_call"
- "use MCP tool" -> sub_type="mcp_server"
- "A2A protocol" -> sub_type="agent_to_agent"

REQUIRES: Additional IDs depending on sub_type (target agent, nugget, or MCP server).""",
        inputSchema={
            "type": "object",
            "properties": {
                "jwt_token": {
                    "type": "string",
                    "description": "User's Eliza JWT token"
                },
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent"
                },
                "sub_type": {
                    "type": "string",
                    "enum": ["agent_to_agent", "nugget_call", "function_call", "mcp_server", "agent_chat"],
                    "description": "Which interop type"
                },
                "target_agent_id": {
                    "type": "string",
                    "description": "Target agent UUID (for agent_chat)"
                },
                "target_nugget_id": {
                    "type": "string",
                    "description": "Target nugget UUID (for nugget_call)"
                },
                "mcp_server_id": {
                    "type": "string",
                    "description": "MCP server ID (for mcp_server)"
                },
                "mcp_tool_name": {
                    "type": "string",
                    "description": "MCP tool name (for mcp_server)"
                },
                "a2a_server_id": {
                    "type": "string",
                    "description": "A2A server ID (for agent_to_agent)"
                },
                "label": {
                    "type": "string",
                    "description": "Display name"
                },
                "env": {
                    "type": "string",
                    "enum": ["DEV", "TEST", "QA", "PROD"]
                }
            },
            "required": ["jwt_token", "agent_id", "sub_type"]
        }
    ),
]


# =============================================================================
# HANDLER
# =============================================================================

def handle_category_capability(tool_name: str, args: Dict[str, Any]) -> str:
    """
    Handle category capability tools.

    Returns guidance to use the search_ez_functions + create_nugget workflow,
    with the appropriate ez* functions pre-identified based on sub_type.
    """
    sub_type = args.get("sub_type", "unknown")
    agent_id = args.get("agent_id", "{AGENT_ID}")
    jwt_token = args.get("jwt_token")

    # Get the ez* functions for this category + sub_type
    category_map = CATEGORY_FUNCTION_MAP.get(tool_name, {})
    ez_functions = category_map.get(sub_type, [])
    search_query = SUBTYPE_SEARCH_QUERIES.get(sub_type, sub_type)

    # Special case: calculation uses PYTHON_STATIC, not nugget
    if sub_type == "calculation":
        return f"""For local calculations, create a PYTHON_STATIC function:

**Note**: PYTHON_STATIC functions CANNOT call external services (APIs, email, LLM).
They are for self-contained logic: math, date formatting, string manipulation.

**Workflow**:
1. Call `create_nugget` with function_type="PYTHON_STATIC"
2. Provide the calculation logic in the requirement

Example:
```
create_nugget(
    jwt_token="{jwt_token or '{YOUR_JWT}'}",
    agent_id="{agent_id}",
    requirement="Calculate the total price with tax",
    discovered_functions=[],  # No ez* functions needed
    skip_search=true  # No search needed for PYTHON_STATIC
)
```
"""

    if not ez_functions:
        return f"""Unknown sub_type "{sub_type}" for {tool_name}.

Please use search_ez_functions to discover the right functions:
```
search_ez_functions(query="{search_query}")
```
"""

    # Build the guidance response
    functions_str = ", ".join(f'"{f}"' for f in ez_functions)

    return f"""To create this {sub_type} capability, use the validated workflow:

**Step 1: Verify function signatures** (recommended)
```
search_ez_functions(query="{search_query}")
```

**Step 2: Create the nugget with discovered functions**
```
create_nugget(
    jwt_token="{jwt_token or '{YOUR_JWT}'}",
    agent_id="{agent_id}",
    requirement="Your specific requirement for {sub_type}",
    discovered_functions=[{functions_str}],
    skip_search=true  # Functions pre-identified
)
```

**Pre-identified ez* functions for {sub_type}**: {', '.join(ez_functions)}

This ensures the generated code uses correct function signatures and passes validation.
"""


# =============================================================================
# BACKWARDS COMPATIBILITY
# Legacy tool names map to category + sub_type
# =============================================================================

LEGACY_TOOL_MAPPING = {
    # Communication
    "create_email_function": ("create_communication_capability", "email"),
    "create_notification_function": ("create_communication_capability", "notification"),
    "create_confirmation_function": ("create_communication_capability", "confirmation"),
    "create_comms_function": ("create_communication_capability", "teams_slack"),
    # Integration
    "create_api_function": ("create_integration_capability", "rest_api"),
    "create_database_function": ("create_integration_capability", "database"),
    "create_jira_function": ("create_integration_capability", "jira"),
    "create_sharepoint_function": ("create_integration_capability", "sharepoint"),
    "create_external_api_function": ("create_integration_capability", "external_api"),
    "create_copilot_function": ("create_integration_capability", "copilot"),
    # AI
    "create_image_analysis_function": ("create_ai_capability", "image_analysis"),
    "create_image_generation_function": ("create_ai_capability", "image_generation"),
    "create_video_generation_function": ("create_ai_capability", "video_generation"),
    "create_tts_function": ("create_ai_capability", "text_to_speech"),
    "create_embeddings_function": ("create_ai_capability", "embeddings"),
    # Automation
    "create_browser_function": ("create_automation_capability", "browser"),
    "create_computer_function": ("create_automation_capability", "desktop"),
    "create_python_execution_function": ("create_automation_capability", "python"),
    "create_research_function": ("create_automation_capability", "research"),
    # Data
    "create_session_function": ("create_data_capability", "session_both"),
    "create_data_management_function": ("create_data_capability", "data_query"),
    "create_calculation_function": ("create_data_capability", "calculation"),
    # Interop
    "create_agent_call_function": ("create_interop_capability", "agent_chat"),
    "create_nugget_call_function": ("create_interop_capability", "nugget_call"),
    "create_a2a_function": ("create_interop_capability", "agent_to_agent"),
    "create_mcp_function": ("create_interop_capability", "mcp_server"),
    # Utility (map to closest category)
    "create_logging_function": ("create_data_capability", "calculation"),  # Use PYTHON_STATIC
    "create_sleep_function": ("create_data_capability", "calculation"),
    "create_secrets_function": ("create_integration_capability", "external_api"),
    "create_user_info_function": ("create_data_capability", "session_get"),
    "create_prompt_function": ("create_ai_capability", "llm_chat"),
    "create_experiments_function": ("create_data_capability", "data_query"),
}


def handle_legacy_capability_tool(tool_name: str, args: Dict[str, Any]) -> str:
    """
    Handle legacy tool names by mapping to new category tools.
    """
    if tool_name not in LEGACY_TOOL_MAPPING:
        return f"Unknown tool: {tool_name}. Use one of the category tools instead."

    new_tool, sub_type = LEGACY_TOOL_MAPPING[tool_name]
    args["sub_type"] = sub_type

    return handle_category_capability(new_tool, args)
