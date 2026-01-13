# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Eliza MCP Server** - a Python-based Model Context Protocol server for the Eliza AI platform. It generates and validates code for Eliza agents, nuggets (JavaScript), and functions, connecting to BNY's CogEngine API.

## Build & Test Commands

```bash
# Run all tests
python scripts/run_tests.py

# Run specific test categories
python scripts/run_tests.py unit         # Fast, no API calls
python scripts/run_tests.py integration  # Requires API access
python scripts/run_tests.py hooks        # Hook script tests
python scripts/run_tests.py coverage     # With coverage report

# Start MCP server
python server.py
```

## Architecture

### Mandatory Workflow System

**Critical:** All Eliza tasks MUST go through `eliza_workflow` tool. This is enforced by `.windsurfrules` and hook scripts.

**Workflow Phases (11 steps):**
1. `INIT` → `CHECK_CREDENTIALS` → `REQUEST_CREDENTIALS` → `WRITE_ENV_FILE`
2. `DETECT_INTENT` → `SEARCH_FUNCTIONS` → `CREATE_ARTIFACT`
3. `STATIC_VALIDATION` → `READY_TO_WRITE` → `RUNTIME_VALIDATION` → `COMPLETE`

**State persists in:** `.eliza/workflow_state.json`

### 46 MCP Tools (Consolidated)

| Category | Tools |
|----------|-------|
| Workflow | `eliza_workflow` (MANDATORY orchestrator) |
| Agents | `create_rag_agent`, `create_function_agent` |
| Nuggets | `search_ez_functions`, `create_nugget` |
| Documents | `create_document_upload` |
| Validation | `validate_eliza_code`, `diagnose_error` |
| Reference | `get_api_endpoint`, `get_valid_values` |
| Capabilities | 6 category tools (Communication, Integration, AI, Automation, Data, Interop) |
| CRUD | 11 tools for Agent/Nugget/Function operations |
| Operations | 19 category tools (75 API endpoints - see below) |

### Operation Tools (Standalone - No workflow required)

These tools expose 75 API endpoints via a category+operation pattern:

**Original 7 Operation Tools:**
| Tool | Operations | Use for |
|------|------------|---------|
| `chat_operations` | chat, query, bulk, bulk_extended | Chat/query agents |
| `analytics_operations` | activity, users, analytics, all_users, history, top_questions | Usage analytics |
| `a2a_operations` | register, register_to_agent, list, delete | A2A server management |
| `nugget_execution` | call, call_dynamic, call_bulk, search | Execute existing nuggets |
| `document_extended` | get, download, download_figure, get_metadata, create_metadata, update_metadata, reindex | Extended doc operations |
| `chunk_operations` | update, delete, create_virtual | Chunk management |
| `system_operations` | get_models, get_chunking_strategies, get_agent_users, get_initiatives | System info |

**New 12 Operation Tools:**
| Tool | Operations | Use for |
|------|------------|---------|
| `agent_crud` | create, get, update, delete, list, disable | Agent CRUD operations |
| `nugget_crud` | create, get, update, delete | Nugget CRUD operations |
| `function_crud` | add, get, delete, list | Function CRUD operations |
| `document_crud` | list, search, delete, upload, upload_index | Document CRUD operations |
| `identity_operations` | add, delete | Agent identity management |
| `access_operations` | add_agent_access, remove_agent_access, add_auth_access, remove_auth_access | Access control |
| `ideas_operations` | get_ideas, vote, delete, upvote | Ideas and voting |
| `hashes_operations` | list, create, get, delete | Merkle DAG hashes |
| `index_operations` | search, search_cosmosdb | Vector index search |
| `promotion_operations` | promote, import | Agent promotion/import |
| `advanced_operations` | back_testing, computer_use, call_resource | Advanced features |
| `discovery_operations` | by_control_flag, by_app_id, datasources | Agent discovery |

**When to use:** Operations are for USING existing artifacts (chat, execute, query). Use `eliza_workflow` for CREATING new artifacts (nuggets, agents, functions).

**Scalable architecture:** Add new endpoints by updating `tools/registry/tool_registry.py` - no new handler code needed.

### Key Directories

- `tools/` - All 46 MCP tool implementations, `workflow.py` is the orchestrator
- `tools/registry/` - Scalable tool registry and category router for operation tools
- `tools/operations/` - Operation tool exports (19 handlers)
- `validation/` - AST-based code validation (no execution), input validators
- `codegen/` - JavaScript nugget generator with security sanitization
- `search/` - EZ function registry (`index.py`) and BM25-style search
- `api/` - ElizaClient for CogEngine HTTP calls (75 methods, 19 categories)
- `scripts/` - Hook scripts and test runner

### Hook System

Pre/post-write hooks (`.windsurf/hooks.json`) enforce workflow completion and validate code before/after writes. Hooks can block file writes (exit code 2) if validation fails.

### EZ* Function Registry

`search/index.py` contains ~50+ ez* function definitions (signatures, descriptions, keywords, examples). This is the authoritative source for function discovery.

### CogEngine Environments

DEV, TEST, QA, PROD environments available via `api/client.py`. Uses SSL certificate handling for internal BNY certs.

## Development Rules (from .windsurfrules)

1. **ALWAYS call `eliza_workflow` FIRST** for any Eliza task
2. **NEVER write Eliza code directly** - follow the workflow
3. **On validation failure** - call `eliza_workflow(action='retry')`, not manual fixes
4. **Maximum 3 retry attempts** - then reset workflow
5. **Recognize Eliza tasks** - anything involving agents, nuggets, ez* functions, capabilities

## Code Validation

`validation/static.py` performs AST-based validation:
- Python/JavaScript syntax errors
- Field name correctness (funcNameKey vs name)
- Model name prefixes (openai-, bnym-, google-)
- Ez* function usage patterns

Returns severity, message, line number, and suggested fix.

## Security Features

- All user inputs sanitized before JavaScript generation (escapes, length limits)
- JWT format validation (not signature)
- Workflow enforcement prevents bypassing validation
- Hook blocking for invalid code
