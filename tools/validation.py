"""
Validation Tools

MCP tools for validating Eliza code and diagnosing errors.
"""

from mcp.types import Tool
from typing import Dict, Any
from validation.static import validate_and_report, validate_code


# Tool definitions
VALIDATION_TOOLS = [
    Tool(
        name="validate_eliza_code",
        description="""Validate Eliza code WITHOUT executing it. Catches errors before runtime.

CHECKS:
- Python syntax errors
- Wrong field names (funcNameKey vs name)
- Invalid model names (must have openai-, bnym-, google- prefix)
- Architectural violations (PYTHON_STATIC trying to send email)
- JavaScript nugget syntax and ez* function usage

Returns issues found + auto-fixed code if possible.""",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Code to validate"},
                "code_type": {
                    "type": "string",
                    "enum": ["python", "nugget", "auto"],
                    "description": "Code type (auto-detected if not specified)"
                }
            },
            "required": ["code"]
        }
    ),
    Tool(
        name="diagnose_error",
        description="""Get fix for common Eliza errors.

COMMON ERRORS AND FIXES:
- "No access to initiative ELZ-00000" → Use your personal initiative ELZI-{your_userid}
- "Model not found" → Add prefix openai-, bnym-, or google- to model name
- "Page size must be greater than zero" → Use offset/limit NOT pageNumber/pageSize
- "Agent name is required" → Use 'name' field NOT 'agentName'
- "Sorry, something went wrong" (REASON strategy) → Use openai-gpt-4.1-mini-ptu model""",
        inputSchema={
            "type": "object",
            "properties": {
                "error_message": {
                    "type": "string",
                    "description": "The exact error message you received from Eliza"
                }
            },
            "required": ["error_message"]
        }
    )
]


# Tool implementations
def handle_validate_eliza_code(args: Dict[str, Any]) -> str:
    """Validate Eliza code and return report."""
    code = args.get("code", "")
    code_type = args.get("code_type")

    if code_type == "auto":
        code_type = None

    return validate_and_report(code, code_type)


def diagnose_error(args: Dict[str, Any]) -> str:
    """Diagnose common Eliza errors and provide fixes."""
    error = args.get("error_message", "").lower()

    diagnoses = [
        {
            "patterns": ["initiative", "elz-00000", "access"],
            "diagnosis": "Initiative ID Error",
            "fix": """The default initiative ELZ-00000 doesn't work for most users.

**Solution**: Use your personal initiative ID format: `ELZI-{{userid}}`

Example:
```python
eliza.session = eliza.Session.connect(
    env='QA',
    jwt_token=jwt_token,
    initiative_id='ELZI-XFMLC5G'  # Replace with YOUR userid
)
```

To find your initiative, load an existing agent from Workbench and check `agent.initiative_id`."""
        },
        {
            "patterns": ["model", "not found", "invalid model"],
            "diagnosis": "Invalid Model Name",
            "fix": """Eliza requires prefixed model names.

**Wrong**: `gpt-4`, `llama`, `gemini`
**Correct**: `openai-gpt-4`, `bnym-llama-3.3-70b-instruct`, `google-gemini-1.5-pro`

Common models:
- `openai-gpt-4.1-mini-ptu` (recommended for REASON strategy)
- `bnym-llama-3.3-70b-instruct` (on-prem)
- `openai-gpt-4o`"""
        },
        {
            "patterns": ["page", "size", "pagesize", "pagenumber"],
            "diagnosis": "Pagination Error",
            "fix": """Eliza uses offset/limit, NOT pageNumber/pageSize.

**Wrong**:
```python
{"pageNumber": 1, "pageSize": 10}
```

**Correct**:
```python
{"offset": 0, "limit": 10}
```"""
        },
        {
            "patterns": ["agent", "name", "required", "agentname"],
            "diagnosis": "Agent Field Name Error",
            "fix": """Use SDK field names, not API field names.

**Wrong**: `agentName`, `agentDescription`
**Correct**: `agent_name`, `agent_description`

```python
agent = Agent(
    agent_name='My Agent',        # NOT agentName
    agent_description='...',      # NOT agentDescription
    ...
)
```"""
        },
        {
            "patterns": ["sorry", "something went wrong", "reason"],
            "diagnosis": "REASON Strategy Model Error",
            "fix": """REASON strategy (function calling) requires a compatible model.

**Solution**: Use `openai-gpt-4.1-mini-ptu`

```python
agent = Agent(
    retriever_strategy='REASON',
    llm_model='openai-gpt-4.1-mini-ptu',  # Required for function calling
    ...
)
```

The `bnym-llama` models may not support tool calling in all configurations."""
        },
        {
            "patterns": ["funcnamekey", "name", "function"],
            "diagnosis": "Function Field Name Error",
            "fix": """Use correct field names for function definitions.

**Wrong**: `name`, `description`, `parameters`
**Correct**: `funcNameKey`, `label`, `params`

```python
function_def = {
    "funcNameKey": "my_function",  # NOT "name"
    "label": "My Function",        # NOT "description"
    "params": [...],               # NOT "parameters"
    ...
}
```"""
        },
        {
            "patterns": ["to", "array", "mail", "email"],
            "diagnosis": "ezMail Format Error",
            "fix": """ezMail requires 'to' field to be an array.

**Wrong**:
```javascript
ezMail(JSON.stringify({to: "user@example.com", ...}))
```

**Correct**:
```javascript
ezMail(JSON.stringify({to: ["user@example.com"], ...}))
```"""
        }
    ]

    for d in diagnoses:
        if any(p in error for p in d["patterns"]):
            return f"""## {d["diagnosis"]}

{d["fix"]}"""

    return f"""## Unknown Error

Error message: {args.get("error_message", "")}

Common troubleshooting:
1. Check JWT token is valid and not expired
2. Verify initiative_id format: ELZI-{{{{userid}}}}
3. Ensure model name has correct prefix (openai-, bnym-, google-)
4. Use offset/limit not pageNumber/pageSize
5. For REASON strategy, use openai-gpt-4.1-mini-ptu

If error persists, check the Eliza Workbench logs or contact support."""