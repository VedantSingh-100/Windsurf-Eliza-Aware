Great question! Here's how the system is structured so you can customize it:

  How to Customize Meta-Tools

  1. Always-Visible Tools (loaded upfront)

  Edit server.py around line 103-104:

  # Currently:
  LAZY_MODE_TOOLS = WORKFLOW_TOOLS + META_TOOLS

  To add more always-visible tools:
  from tools.validation import VALIDATION_TOOLS  # Example: make validation always visible

  LAZY_MODE_TOOLS = WORKFLOW_TOOLS + META_TOOLS + VALIDATION_TOOLS

  Or pick specific tools:
  from tools.nuggets import NUGGET_TOOLS

  # Cherry-pick specific tools to always show
  ALWAYS_VISIBLE = [
      t for t in NUGGET_TOOLS if t['name'] == 'search_ez_functions'
  ]
  LAZY_MODE_TOOLS = WORKFLOW_TOOLS + META_TOOLS + ALWAYS_VISIBLE

  2. Discoverable Tools (in hierarchy)

  Edit tools/hierarchy.py:

  Category Tree (lines 24-100):
  CATEGORY_TREE = {
      "workflow": {
          "description": "...",
          "tools": ["eliza_workflow"]  # Tools in this category
      },
      "create": {
          "subcategories": {
              "agents": {
                  "tools": ["create_rag_agent", "create_function_agent"]
              },
              # Add/remove/move tools here
          }
      },
      # Add new categories here
  }

  Tool Registry (lines 110+):
  TOOL_REGISTRY = {
      "tool_name": ToolInfo(
          name="tool_name",
          brief="One-line description for discovery",  # Shown in "brief" mode
          category="create/agents",  # Category path
          is_async=False  # Whether handler is async
      ),
      # Add/remove tools here
  }

  3. Quick Examples

  Move search_ez_functions to always-visible:
  # In server.py
  from tools.nuggets import NUGGET_TOOLS

  SEARCH_TOOL = [t for t in NUGGET_TOOLS if t['name'] == 'search_ez_functions']
  LAZY_MODE_TOOLS = WORKFLOW_TOOLS + META_TOOLS + SEARCH_TOOL

  Add a new category:
  # In tools/hierarchy.py
  CATEGORY_TREE = {
      # ... existing categories ...
      "my_category": {
          "description": "My custom tools",
          "subcategories": {},
          "tools": ["my_tool_1", "my_tool_2"]
      }
  }

  Remove a tool from discovery:
  # Just remove it from TOOL_REGISTRY and CATEGORY_TREE
  # It will still work in legacy mode but won't show in discover_tools

  4. File Summary

  | What to Change          | Where                                      |
  |-------------------------|--------------------------------------------|
  | Always-visible tools    | server.py:103-104                          |
  | Category structure      | tools/hierarchy.py → CATEGORY_TREE         |
  | Tool brief descriptions | tools/hierarchy.py → TOOL_REGISTRY         |
  | Tool execution routing  | tools/meta/executor.py → _HANDLER_REGISTRY |

  Would you like me to make any specific changes - like making certain tools always visible or reorganizing the categories?