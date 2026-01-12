#!/usr/bin/env python3
"""
Workflow Debugger - Real End-to-End Flow Testing

This is NOT a unit test. This is a debugging tool that:
1. Takes a real user query
2. Runs it through the ENTIRE workflow (not mocked components)
3. Logs EVERYTHING that happens at each step
4. Shows exactly where failures occur
5. Uses real credentials if available

Usage:
    python tests/workflow_debugger.py "create a newsletter agent"
    python tests/workflow_debugger.py --jwt YOUR_JWT --agent-id YOUR_AGENT_ID "send emails"

The output shows:
- Every function called
- Every API endpoint hit
- Every file written
- Every validation run
- Every error encountered
"""

import asyncio
import argparse
import os
import sys
import json
import tempfile
import shutil
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LogLevel(Enum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


@dataclass
class FlowStep:
    """A single step in the workflow."""
    timestamp: datetime
    step_name: str
    level: LogLevel
    message: str
    data: Optional[Dict] = None
    duration_ms: float = 0
    error: Optional[str] = None


class WorkflowDebugger:
    """
    Real workflow debugger that traces the entire flow.

    This runs the ACTUAL workflow code, not mocks.
    """

    def __init__(
        self,
        jwt_token: Optional[str] = None,
        agent_id: Optional[str] = None,
        env: str = "QA",
        workspace: Optional[str] = None,
        verbose: bool = True
    ):
        self.jwt_token = jwt_token
        self.agent_id = agent_id
        self.env = env
        self.workspace = workspace or tempfile.mkdtemp(prefix="eliza_debug_")
        self.verbose = verbose
        self.steps: List[FlowStep] = []
        self.created_temp_workspace = workspace is None

        # Create workspace directories
        os.makedirs(os.path.join(self.workspace, "nuggets"), exist_ok=True)
        os.makedirs(os.path.join(self.workspace, ".eliza"), exist_ok=True)

    def log(self, step_name: str, level: LogLevel, message: str, data: Dict = None, error: str = None):
        """Log a step in the workflow."""
        step = FlowStep(
            timestamp=datetime.now(),
            step_name=step_name,
            level=level,
            message=message,
            data=data,
            error=error
        )
        self.steps.append(step)

        if self.verbose:
            icon = {
                LogLevel.INFO: "ℹ️",
                LogLevel.SUCCESS: "✅",
                LogLevel.WARNING: "⚠️",
                LogLevel.ERROR: "❌",
                LogLevel.DEBUG: "🔍"
            }.get(level, "•")

            print(f"{icon} [{step_name}] {message}")
            if data and level != LogLevel.DEBUG:
                for k, v in data.items():
                    val_str = str(v)[:100] + "..." if len(str(v)) > 100 else str(v)
                    print(f"   └─ {k}: {val_str}")
            if error:
                print(f"   └─ ERROR: {error}")

    def cleanup(self):
        """Clean up temporary workspace."""
        if self.created_temp_workspace and os.path.exists(self.workspace):
            shutil.rmtree(self.workspace, ignore_errors=True)

    async def run_flow(self, user_query: str) -> Dict[str, Any]:
        """
        Run the complete workflow for a user query.

        Returns a summary of what happened.
        """
        print("\n" + "=" * 70)
        print("WORKFLOW DEBUGGER - REAL FLOW TEST")
        print("=" * 70)
        print(f"Query: {user_query}")
        print(f"Workspace: {self.workspace}")
        print(f"JWT: {'Provided' if self.jwt_token else 'NOT PROVIDED'}")
        print(f"Agent ID: {self.agent_id or 'NOT PROVIDED'}")
        print(f"Environment: {self.env}")
        print("=" * 70 + "\n")

        result = {
            "query": user_query,
            "success": False,
            "steps_completed": [],
            "steps_failed": [],
            "files_created": [],
            "errors": []
        }

        try:
            # =========================================================
            # STEP 1: Import required modules
            # =========================================================
            self.log("IMPORT", LogLevel.INFO, "Loading workflow modules...")

            try:
                from tools.workflow import handle_eliza_workflow
                from tools.workflow_state import get_or_create_state, WorkflowStep, WorkflowStatus
                from search.search import smart_search, detect_intents
                from codegen.nugget_generator import generate_nugget_code
                from validation.static import validate_code
                self.log("IMPORT", LogLevel.SUCCESS, "All modules loaded successfully")
                result["steps_completed"].append("IMPORT")
            except ImportError as e:
                self.log("IMPORT", LogLevel.ERROR, f"Failed to import modules", error=str(e))
                result["steps_failed"].append("IMPORT")
                result["errors"].append(f"Import error: {e}")
                return result

            # =========================================================
            # STEP 2: Start workflow
            # =========================================================
            self.log("WORKFLOW_START", LogLevel.INFO, "Starting eliza_workflow...")

            start_args = {
                "action": "start",
                "requirement": user_query,
                "workspace_path": self.workspace
            }

            workflow_result = await handle_eliza_workflow(start_args)

            self.log("WORKFLOW_START", LogLevel.INFO, "Workflow started", data={
                "status": workflow_result.get("status"),
                "current_step": workflow_result.get("current_step"),
                "message": workflow_result.get("message", workflow_result.get("prompt_for_user", ""))[:100]
            })

            # Check state file was created
            state_file = os.path.join(self.workspace, ".eliza", "workflow_state.json")
            if os.path.exists(state_file):
                result["files_created"].append(".eliza/workflow_state.json")
                self.log("WORKFLOW_START", LogLevel.SUCCESS, "State file created")

            result["steps_completed"].append("WORKFLOW_START")

            # =========================================================
            # STEP 3: Provide credentials (if available)
            # =========================================================
            if workflow_result.get("status") == "NEED_CREDENTIALS":
                self.log("CREDENTIALS", LogLevel.INFO, "Workflow needs credentials...")

                if not self.jwt_token or not self.agent_id:
                    self.log("CREDENTIALS", LogLevel.WARNING,
                             "No credentials provided - workflow will stall here",
                             data={"jwt_provided": bool(self.jwt_token), "agent_id_provided": bool(self.agent_id)})
                    result["steps_failed"].append("CREDENTIALS")
                    result["errors"].append("No JWT token or agent ID provided")

                    # Continue anyway to show what would happen
                    self.log("CREDENTIALS", LogLevel.INFO, "Using placeholder credentials for testing...")
                    self.jwt_token = self.jwt_token or "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.placeholder"
                    self.agent_id = self.agent_id or "12345678-1234-1234-1234-123456789abc"

                cred_args = {
                    "action": "continue",
                    "requirement": user_query,
                    "jwt_token": self.jwt_token,
                    "agent_id": self.agent_id,
                    "env": self.env,
                    "workspace_path": self.workspace
                }

                workflow_result = await handle_eliza_workflow(cred_args)

                self.log("CREDENTIALS", LogLevel.SUCCESS, "Credentials processed", data={
                    "status": workflow_result.get("status"),
                    "current_step": workflow_result.get("current_step")
                })

                result["steps_completed"].append("CREDENTIALS")

            # =========================================================
            # STEP 4: Check intent detection
            # =========================================================
            self.log("INTENT", LogLevel.INFO, "Checking intent detection...")

            state = get_or_create_state(self.workspace)
            intent_data = state.get("intent", {})

            self.log("INTENT", LogLevel.INFO, "Intent detection results", data={
                "user_requirement": intent_data.get("user_requirement", "")[:50],
                "detected_intent": intent_data.get("detected_intent"),
                "discovered_functions": intent_data.get("discovered_functions", [])
            })

            if intent_data.get("discovered_functions"):
                self.log("INTENT", LogLevel.SUCCESS,
                         f"Found {len(intent_data['discovered_functions'])} functions")
                result["steps_completed"].append("INTENT")
            else:
                self.log("INTENT", LogLevel.WARNING, "No functions discovered")
                result["steps_failed"].append("INTENT")

            # =========================================================
            # STEP 5: Generate code
            # =========================================================
            self.log("CODEGEN", LogLevel.INFO, "Generating nugget code...")

            discovered_funcs = intent_data.get("discovered_functions", [])
            if discovered_funcs:
                try:
                    code, label, description, test_data = generate_nugget_code(
                        discovered_funcs,
                        user_query,
                        {}
                    )

                    self.log("CODEGEN", LogLevel.SUCCESS, "Code generated", data={
                        "label": label,
                        "description": description[:50],
                        "code_length": len(code),
                        "test_data": test_data
                    })

                    # Show the actual code
                    print("\n" + "-" * 50)
                    print("GENERATED CODE:")
                    print("-" * 50)
                    print(code)
                    print("-" * 50 + "\n")

                    result["steps_completed"].append("CODEGEN")

                    # =========================================================
                    # STEP 6: Validate code
                    # =========================================================
                    self.log("VALIDATION", LogLevel.INFO, "Running static validation...")

                    validation_result = validate_code(code, "nugget")

                    if validation_result.valid:
                        self.log("VALIDATION", LogLevel.SUCCESS, "Static validation PASSED")
                        result["steps_completed"].append("VALIDATION")
                    else:
                        issues = [f"{i.severity.value}: {i.message}" for i in validation_result.issues]
                        self.log("VALIDATION", LogLevel.ERROR, "Static validation FAILED", data={
                            "issues": issues
                        })
                        result["steps_failed"].append("VALIDATION")
                        result["errors"].extend(issues)

                    # =========================================================
                    # STEP 7: Submit code to workflow
                    # =========================================================
                    self.log("SUBMIT_CODE", LogLevel.INFO, "Submitting code to workflow...")

                    nugget_file = os.path.join(self.workspace, "nuggets", "generated.nugget.js")

                    submit_args = {
                        "action": "continue",
                        "generated_code": code,
                        "file_path": nugget_file,
                        "workspace_path": self.workspace
                    }

                    workflow_result = await handle_eliza_workflow(submit_args)

                    self.log("SUBMIT_CODE", LogLevel.INFO, "Code submitted", data={
                        "status": workflow_result.get("status"),
                        "current_step": workflow_result.get("current_step")
                    })

                    result["steps_completed"].append("SUBMIT_CODE")

                    # =========================================================
                    # STEP 8: Write file to disk
                    # =========================================================
                    if workflow_result.get("status") == "READY_TO_WRITE":
                        self.log("FILE_WRITE", LogLevel.INFO, f"Writing file: {nugget_file}")

                        os.makedirs(os.path.dirname(nugget_file), exist_ok=True)
                        with open(nugget_file, 'w') as f:
                            f.write(code)

                        if os.path.exists(nugget_file):
                            result["files_created"].append("nuggets/generated.nugget.js")
                            self.log("FILE_WRITE", LogLevel.SUCCESS, "File written successfully")
                            result["steps_completed"].append("FILE_WRITE")

                        # Write .env file
                        env_file = os.path.join(self.workspace, ".env")
                        with open(env_file, 'w') as f:
                            f.write(f"ELIZA_JWT_TOKEN={self.jwt_token}\n")
                            f.write(f"ELIZA_AGENT_ID={self.agent_id}\n")
                            f.write(f"ELIZA_ENV={self.env}\n")

                        result["files_created"].append(".env")
                        self.log("FILE_WRITE", LogLevel.SUCCESS, ".env file written")

                        # =========================================================
                        # STEP 9: Run post-write hook (runtime validation)
                        # =========================================================
                        self.log("HOOK", LogLevel.INFO, "Running post-write hook...")

                        try:
                            from tests.helpers.hook_runner import run_hook, create_hook_payload

                            hook_payload = create_hook_payload(nugget_file)
                            hook_result = run_hook(hook_payload, timeout=30)

                            self.log("HOOK", LogLevel.INFO, "Hook executed", data={
                                "exit_code": hook_result.exit_code,
                                "passed": hook_result.passed,
                                "blocked": hook_result.blocked
                            })

                            if hook_result.stdout:
                                print("\n" + "-" * 50)
                                print("HOOK OUTPUT:")
                                print("-" * 50)
                                print(hook_result.stdout)
                                print("-" * 50 + "\n")

                            if hook_result.stderr:
                                self.log("HOOK", LogLevel.WARNING, "Hook stderr", data={
                                    "stderr": hook_result.stderr[:200]
                                })

                            if hook_result.passed:
                                self.log("HOOK", LogLevel.SUCCESS, "Hook PASSED")
                                result["steps_completed"].append("HOOK")
                            elif hook_result.blocked:
                                self.log("HOOK", LogLevel.ERROR, "Hook BLOCKED the write")
                                result["steps_failed"].append("HOOK")
                                result["errors"].append("Post-write hook blocked")
                            else:
                                self.log("HOOK", LogLevel.ERROR, f"Hook failed with exit code {hook_result.exit_code}")
                                result["steps_failed"].append("HOOK")

                        except Exception as e:
                            self.log("HOOK", LogLevel.WARNING, f"Could not run hook: {e}")

                        # =========================================================
                        # STEP 10: Complete workflow
                        # =========================================================
                        self.log("COMPLETE", LogLevel.INFO, "Completing workflow...")

                        complete_args = {
                            "action": "continue",
                            "workspace_path": self.workspace
                        }

                        workflow_result = await handle_eliza_workflow(complete_args)

                        if workflow_result.get("status") == "COMPLETE":
                            self.log("COMPLETE", LogLevel.SUCCESS, "Workflow COMPLETED!")
                            result["steps_completed"].append("COMPLETE")
                            result["success"] = True
                        else:
                            self.log("COMPLETE", LogLevel.INFO, "Workflow status", data=workflow_result)

                except Exception as e:
                    self.log("CODEGEN", LogLevel.ERROR, f"Code generation failed: {e}")
                    result["steps_failed"].append("CODEGEN")
                    result["errors"].append(str(e))
                    traceback.print_exc()

        except Exception as e:
            self.log("FLOW", LogLevel.ERROR, f"Unexpected error: {e}")
            result["errors"].append(str(e))
            traceback.print_exc()

        # =========================================================
        # FINAL SUMMARY
        # =========================================================
        print("\n" + "=" * 70)
        print("FLOW SUMMARY")
        print("=" * 70)
        print(f"Success: {'✅ YES' if result['success'] else '❌ NO'}")
        print(f"\nSteps Completed ({len(result['steps_completed'])}):")
        for step in result['steps_completed']:
            print(f"  ✅ {step}")

        if result['steps_failed']:
            print(f"\nSteps Failed ({len(result['steps_failed'])}):")
            for step in result['steps_failed']:
                print(f"  ❌ {step}")

        if result['errors']:
            print(f"\nErrors ({len(result['errors'])}):")
            for err in result['errors']:
                print(f"  • {err}")

        print(f"\nFiles Created ({len(result['files_created'])}):")
        for f in result['files_created']:
            full_path = os.path.join(self.workspace, f)
            size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
            print(f"  📄 {f} ({size} bytes)")

        print(f"\nWorkspace: {self.workspace}")
        print("=" * 70 + "\n")

        return result


async def main():
    parser = argparse.ArgumentParser(description="Workflow Debugger - Real Flow Testing")
    parser.add_argument("query", help="User query to test")
    parser.add_argument("--jwt", help="JWT token (or set ELIZA_JWT_TOKEN env var)")
    parser.add_argument("--agent-id", help="Agent ID (or set ELIZA_AGENT_ID env var)")
    parser.add_argument("--env", default="QA", choices=["DEV", "TEST", "QA", "PROD"])
    parser.add_argument("--workspace", help="Workspace directory (default: temp)")
    parser.add_argument("--keep-workspace", action="store_true", help="Don't delete workspace after")

    args = parser.parse_args()

    # Get credentials from args or environment
    jwt_token = args.jwt or os.environ.get("ELIZA_JWT_TOKEN")
    agent_id = args.agent_id or os.environ.get("ELIZA_AGENT_ID")

    debugger = WorkflowDebugger(
        jwt_token=jwt_token,
        agent_id=agent_id,
        env=args.env,
        workspace=args.workspace
    )

    try:
        result = await debugger.run_flow(args.query)

        # Exit with appropriate code
        if result["success"]:
            sys.exit(0)
        else:
            sys.exit(1)
    finally:
        if not args.keep_workspace:
            debugger.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
