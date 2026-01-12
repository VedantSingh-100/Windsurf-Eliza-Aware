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

### 27 MCP Tools (Consolidated)

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

### Key Directories

- `tools/` - All 27 MCP tool implementations, `workflow.py` is the orchestrator
- `validation/` - AST-based code validation (no execution), input validators
- `codegen/` - JavaScript nugget generator with security sanitization
- `search/` - EZ function registry (`index.py`) and BM25-style search
- `api/` - ElizaClient for CogEngine HTTP calls
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
