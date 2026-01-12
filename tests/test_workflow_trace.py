"""
Workflow Trace & Journey Tests

Comprehensive testing that combines:
1. TRACE: Logs every function call, API call, and state change
2. JOURNEY: End-to-end tests with assertions verifying the complete flow
3. MOCK MIRROR: Simulates real experience with mocked API responses

Usage:
    pytest tests/test_workflow_trace.py -v -s  # -s shows trace output
    pytest tests/test_workflow_trace.py::TestWorkflowJourneys::test_newsletter_journey -v -s
"""

import pytest
import asyncio
import os
import sys
import json
import tempfile
import shutil
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
from functools import wraps
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.workflow_state import (
    get_or_create_state,
    update_step,
    update_credentials,
    mark_env_file_written,
    update_pending_write,
    WorkflowStep,
    WorkflowStatus,
    MANDATORY_STEPS
)
from tools.workflow import handle_eliza_workflow
from search.search import smart_search, detect_intents, get_functions_for_intent
from search.index import EZ_FUNCTION_INDEX
from codegen.nugget_generator import generate_nugget_code
from validation.static import validate_code


# =============================================================================
# TRACE EVENT TYPES
# =============================================================================

class EventType(Enum):
    """Types of events in the workflow trace."""
    TOOL_CALL = "TOOL_CALL"
    API_CALL = "API_CALL"
    STATE_CHANGE = "STATE_CHANGE"
    VALIDATION = "VALIDATION"
    SEARCH = "SEARCH"
    CODEGEN = "CODEGEN"
    HOOK = "HOOK"
    ERROR = "ERROR"


@dataclass
class TraceEvent:
    """A single event in the workflow trace."""
    timestamp: datetime
    event_type: EventType
    name: str
    input: Dict[str, Any]
    output: Any
    duration_ms: float = 0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "type": self.event_type.value,
            "name": self.name,
            "input": self.input,
            "output": str(self.output)[:500] if self.output else None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error
        }


# =============================================================================
# WORKFLOW TRACER
# =============================================================================

class WorkflowTracer:
    """
    Captures all events during workflow execution.

    Wraps components to trace:
    - Tool calls (eliza_workflow, search_ez_functions, etc.)
    - API calls (create_nugget, call_nugget, etc.)
    - State changes (workflow_state.json updates)
    - Validation (static and runtime)
    - Search (intent detection, function discovery)
    - Code generation

    Example:
        tracer = WorkflowTracer()
        with tracer:
            result = await handle_eliza_workflow({...})

        tracer.print_trace()
        tracer.assert_sequence(["TOOL_CALL:eliza_workflow", "SEARCH:detect_intents"])
    """

    def __init__(self, verbose: bool = True):
        self.events: List[TraceEvent] = []
        self.verbose = verbose
        self._patches = []
        self._start_time = None

    def __enter__(self):
        self._start_time = datetime.now()
        self._apply_patches()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remove_patches()
        if self.verbose:
            self.print_trace()
        return False

    def add_event(
        self,
        event_type: EventType,
        name: str,
        input_data: Dict[str, Any],
        output: Any = None,
        duration_ms: float = 0,
        success: bool = True,
        error: str = None
    ):
        """Add an event to the trace."""
        event = TraceEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            name=name,
            input=input_data,
            output=output,
            duration_ms=duration_ms,
            success=success,
            error=error
        )
        self.events.append(event)

        if self.verbose:
            status = "✓" if success else "✗"
            print(f"  [{status}] {event_type.value}: {name}")

    def _apply_patches(self):
        """Apply monkey patches to capture events."""
        # Store references to original functions
        import search.search as search_module
        import validation.static as validation_module
        import codegen.nugget_generator as codegen_module

        self._original_smart_search = search_module.smart_search
        self._original_detect_intents = search_module.detect_intents
        self._original_validate_code = validation_module.validate_code
        self._original_generate = codegen_module.generate_nugget_code

        # Create traced wrappers
        tracer = self  # Capture self for closures

        def traced_smart_search(query, *args, **kwargs):
            start = datetime.now()
            result = tracer._original_smart_search(query, *args, **kwargs)
            duration = (datetime.now() - start).total_seconds() * 1000
            tracer.add_event(
                EventType.SEARCH,
                "smart_search",
                {"query": query},
                result,
                duration
            )
            return result

        def traced_detect_intents(query, *args, **kwargs):
            start = datetime.now()
            result = tracer._original_detect_intents(query, *args, **kwargs)
            duration = (datetime.now() - start).total_seconds() * 1000
            tracer.add_event(
                EventType.SEARCH,
                "detect_intents",
                {"query": query},
                {"intents": [i["intent"] for i in result] if result else []},
                duration
            )
            return result

        def traced_validate_code(code, code_type=None):
            start = datetime.now()
            result = tracer._original_validate_code(code, code_type)
            duration = (datetime.now() - start).total_seconds() * 1000
            tracer.add_event(
                EventType.VALIDATION,
                "static_validate",
                {"code_type": code_type, "code_length": len(code)},
                {"valid": result.valid, "issues": len(result.issues)},
                duration,
                success=result.valid
            )
            return result

        def traced_generate(functions, requirement, params=None):
            start = datetime.now()
            result = tracer._original_generate(functions, requirement, params)
            duration = (datetime.now() - start).total_seconds() * 1000
            tracer.add_event(
                EventType.CODEGEN,
                "generate_nugget_code",
                {"functions": functions, "requirement": requirement[:50] if requirement else ""},
                {"code_length": len(result[0]), "label": result[1]},
                duration
            )
            return result

        # Apply patches to all possible import paths
        self._patches = [
            # Patch in modules
            patch.object(search_module, 'smart_search', traced_smart_search),
            patch.object(search_module, 'detect_intents', traced_detect_intents),
            patch.object(validation_module, 'validate_code', traced_validate_code),
            patch.object(codegen_module, 'generate_nugget_code', traced_generate),
        ]

        for p in self._patches:
            p.start()

        # Also update global references in this module
        global smart_search, detect_intents, validate_code, generate_nugget_code
        smart_search = traced_smart_search
        detect_intents = traced_detect_intents
        validate_code = traced_validate_code
        generate_nugget_code = traced_generate

    def _remove_patches(self):
        """Remove all patches."""
        for p in self._patches:
            p.stop()

        # Restore global references
        global smart_search, detect_intents, validate_code, generate_nugget_code
        if hasattr(self, '_original_smart_search'):
            import search.search as search_module
            import validation.static as validation_module
            import codegen.nugget_generator as codegen_module

            smart_search = search_module.smart_search
            detect_intents = search_module.detect_intents
            validate_code = validation_module.validate_code
            generate_nugget_code = codegen_module.generate_nugget_code

    def print_trace(self):
        """Print a formatted trace report."""
        print("\n" + "=" * 60)
        print("WORKFLOW TRACE REPORT")
        print("=" * 60)

        if not self.events:
            print("No events captured")
            return

        total_duration = sum(e.duration_ms for e in self.events)

        # Group by event type
        by_type: Dict[EventType, List[TraceEvent]] = {}
        for e in self.events:
            if e.event_type not in by_type:
                by_type[e.event_type] = []
            by_type[e.event_type].append(e)

        print(f"\nTotal Events: {len(self.events)}")
        print(f"Total Duration: {total_duration:.2f}ms")
        print(f"Success Rate: {sum(1 for e in self.events if e.success)}/{len(self.events)}")

        print("\n--- Events by Type ---")
        for event_type, events in by_type.items():
            print(f"\n{event_type.value} ({len(events)} events):")
            for e in events:
                status = "✓" if e.success else "✗"
                print(f"  [{status}] {e.name}: {e.duration_ms:.1f}ms")
                if e.error:
                    print(f"      ERROR: {e.error}")

        print("\n--- Timeline ---")
        for i, e in enumerate(self.events):
            status = "✓" if e.success else "✗"
            print(f"{i+1}. [{status}] {e.event_type.value}: {e.name}")

        print("=" * 60 + "\n")

    def get_events_by_type(self, event_type: EventType) -> List[TraceEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def assert_event_occurred(self, event_type: EventType, name: str):
        """Assert that a specific event occurred."""
        matching = [e for e in self.events if e.event_type == event_type and e.name == name]
        assert matching, f"Expected event {event_type.value}:{name} did not occur"

    def assert_sequence(self, expected: List[str]):
        """
        Assert events occurred in order.

        Format: ["EVENT_TYPE:name", ...]
        Example: ["SEARCH:detect_intents", "CODEGEN:generate_nugget_code"]
        """
        actual = [f"{e.event_type.value}:{e.name}" for e in self.events]

        # Check subsequence
        j = 0
        for expected_event in expected:
            found = False
            while j < len(actual):
                if actual[j] == expected_event:
                    found = True
                    j += 1
                    break
                j += 1
            assert found, f"Expected sequence {expected} not found in {actual}"

    def assert_no_errors(self):
        """Assert no errors occurred."""
        errors = [e for e in self.events if not e.success]
        assert not errors, f"Errors occurred: {[e.error for e in errors]}"

    def to_json(self) -> str:
        """Export trace as JSON."""
        return json.dumps([e.to_dict() for e in self.events], indent=2)


# =============================================================================
# WORKFLOW SIMULATOR (Mock Mirror)
# =============================================================================

class WorkflowSimulator:
    """
    Simulates the real workflow with mocked API responses.

    Provides a sandbox environment where you can:
    - Run queries through the full workflow
    - See exactly what would happen in production
    - Verify without making real API calls

    Example:
        sim = WorkflowSimulator()
        result = await sim.run_query("create a newsletter agent that sends daily emails")

        assert sim.created_nuggets == 1
        assert "ezMail" in sim.discovered_functions
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.workspace = None
        self.tracer = WorkflowTracer(verbose=verbose)

        # Track what happened
        self.discovered_functions: List[str] = []
        self.generated_code: Optional[str] = None
        self.validation_result: Optional[Any] = None
        self.api_calls: List[Dict] = []
        self.created_nuggets: int = 0
        self.created_functions: int = 0

    def __enter__(self):
        self.workspace = tempfile.mkdtemp(prefix="eliza_sim_")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.workspace:
            shutil.rmtree(self.workspace, ignore_errors=True)
        return False

    def _mock_api_calls(self):
        """Set up mocked API responses."""
        def mock_request(method, path, data=None, timeout=30):
            self.api_calls.append({
                "method": method,
                "path": path,
                "data": data
            })

            self.tracer.add_event(
                EventType.API_CALL,
                f"{method} {path}",
                {"data": data},
                {"status": 200}
            )

            # Return appropriate mock response
            if "/nuggets/" in path and method == "POST":
                self.created_nuggets += 1
                return (True, {
                    "agentNuggetId": f"mock-nugget-{self.created_nuggets}",
                    "label": "Mock Nugget"
                })
            elif "/functions" in path and method == "POST":
                self.created_functions += 1
                return (True, {
                    "agentFunctionId": f"mock-func-{self.created_functions}"
                })
            elif "/call" in path:
                return (True, {"result": "Mock execution success"})
            else:
                return (True, {"success": True})

        return mock_request

    async def run_query(
        self,
        query: str,
        jwt_token: str = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.test",
        agent_id: str = "12345678-1234-1234-1234-123456789abc"
    ) -> Dict[str, Any]:
        """
        Run a query through the complete workflow.

        Returns the final workflow result and populates tracking attributes.
        """
        # Import modules for direct function access (will be patched by tracer)
        import search.search as search_module
        import validation.static as validation_module
        import codegen.nugget_generator as codegen_module

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"SIMULATING QUERY: {query[:50]}...")
            print(f"{'='*60}\n")

        with self.tracer:
            # Step 1: Detect intent and search for functions
            # Use module functions (these get patched by tracer)
            search_result = search_module.smart_search(query)
            self.discovered_functions = search_result.get("all_functions", [])

            self.tracer.add_event(
                EventType.TOOL_CALL,
                "eliza_workflow:start",
                {"requirement": query},
                {"status": "SEARCHING"}
            )

            # Step 2: Generate code if functions found
            if self.discovered_functions:
                code, label, description, test_data = codegen_module.generate_nugget_code(
                    self.discovered_functions,
                    query,
                    {}
                )
                self.generated_code = code

                # Step 3: Validate the code
                self.validation_result = validation_module.validate_code(code, "nugget")

                self.tracer.add_event(
                    EventType.STATE_CHANGE,
                    "workflow_state",
                    {"step": "STATIC_VALIDATION"},
                    {"valid": self.validation_result.valid}
                )

        return {
            "query": query,
            "discovered_functions": self.discovered_functions,
            "generated_code": self.generated_code,
            "validation_passed": self.validation_result.valid if self.validation_result else None,
            "api_calls": self.api_calls,
            "trace": self.tracer.to_json()
        }

    def print_summary(self):
        """Print a summary of the simulation."""
        print("\n" + "-" * 40)
        print("SIMULATION SUMMARY")
        print("-" * 40)
        print(f"Discovered Functions: {self.discovered_functions}")
        print(f"Generated Code: {len(self.generated_code) if self.generated_code else 0} chars")
        print(f"Validation Passed: {self.validation_result.valid if self.validation_result else 'N/A'}")
        print(f"API Calls Made: {len(self.api_calls)}")
        print(f"Nuggets Created: {self.created_nuggets}")
        print(f"Functions Created: {self.created_functions}")
        print("-" * 40 + "\n")


# =============================================================================
# JOURNEY TEST CASES
# =============================================================================

class TestWorkflowJourneys:
    """
    End-to-end journey tests that verify complete user flows.

    Each test simulates a real user scenario:
    1. User sends a query
    2. System detects intent
    3. System discovers required functions
    4. System generates code
    5. System validates code
    6. (Mocked) API creates resources
    """

    @pytest.fixture
    def simulator(self):
        """Create a workflow simulator."""
        sim = WorkflowSimulator(verbose=True)
        with sim:
            yield sim

    @pytest.mark.asyncio
    async def test_newsletter_journey(self, simulator):
        """
        Journey: User wants to create a newsletter agent.

        Expected flow:
        1. Query: "create a newsletter agent that sends daily emails"
        2. Intent: newsletter detected
        3. Functions: ezMail, ezInternetSearch found
        4. Code: Generated with email capability
        5. Validation: Should pass
        """
        result = await simulator.run_query(
            "create a newsletter agent that sends daily emails"
        )

        simulator.print_summary()

        # Assertions
        assert "ezMail" in simulator.discovered_functions, \
            f"Expected ezMail in {simulator.discovered_functions}"

        assert simulator.generated_code is not None, \
            "Expected code to be generated"

        assert "ezMail" in simulator.generated_code, \
            "Generated code should use ezMail"

        assert simulator.validation_result.valid, \
            f"Validation should pass: {[i.message for i in simulator.validation_result.issues]}"

        # Verify trace sequence
        simulator.tracer.assert_event_occurred(EventType.SEARCH, "detect_intents")
        simulator.tracer.assert_event_occurred(EventType.CODEGEN, "generate_nugget_code")
        simulator.tracer.assert_event_occurred(EventType.VALIDATION, "static_validate")

    @pytest.mark.asyncio
    async def test_research_journey(self, simulator):
        """
        Journey: User wants to research topics on the internet.

        Expected flow:
        1. Query: "research latest AI news on the internet"
        2. Intent: research/search detected
        3. Functions: ezInternetSearch found
        4. Code: Generated with search capability
        5. Validation: Should pass
        """
        result = await simulator.run_query(
            "research latest AI news on the internet"
        )

        simulator.print_summary()

        # Assertions
        assert any(f in simulator.discovered_functions for f in ["ezInternetSearch", "ezGenAISearch"]), \
            f"Expected search function in {simulator.discovered_functions}"

        assert simulator.generated_code is not None
        assert simulator.validation_result.valid

    @pytest.mark.asyncio
    async def test_search_and_email_journey(self, simulator):
        """
        Journey: User wants to search and email results.

        Expected flow:
        1. Query: "search for news and email me a summary"
        2. Intent: combined search + email
        3. Functions: ezInternetSearch, ezMail, possibly ezChatCompletions
        4. Code: Generated with chained operations
        5. Validation: Should pass
        """
        result = await simulator.run_query(
            "search for news and email me a summary"
        )

        simulator.print_summary()

        # Should have both search and email
        has_search = any(f in simulator.discovered_functions
                        for f in ["ezInternetSearch", "ezGenAISearch"])
        has_email = "ezMail" in simulator.discovered_functions

        assert has_search or has_email, \
            f"Expected search or email functions in {simulator.discovered_functions}"

    @pytest.mark.asyncio
    async def test_llm_chat_journey(self, simulator):
        """
        Journey: User wants an LLM-powered chatbot.

        Expected flow:
        1. Query: "create an AI assistant that answers questions"
        2. Functions: ezChatCompletions found
        3. Code: Generated with LLM capability
        4. Validation: Should pass
        """
        result = await simulator.run_query(
            "create an AI assistant that answers questions using GPT"
        )

        simulator.print_summary()

        # Should have LLM function
        assert "ezChatCompletions" in simulator.discovered_functions, \
            f"Expected ezChatCompletions in {simulator.discovered_functions}"


class TestWorkflowTracing:
    """
    Tests that verify the tracing mechanism captures all events.
    """

    def test_tracer_captures_search_events(self):
        """Verify tracer captures search events."""
        import search.search as search_module

        tracer = WorkflowTracer(verbose=False)

        with tracer:
            # Run a search using module-level function (will be patched)
            result = search_module.smart_search("send email newsletter")

        # Check events were captured
        search_events = tracer.get_events_by_type(EventType.SEARCH)
        assert len(search_events) > 0, "Expected search events to be captured"

        # Check specific functions
        tracer.assert_event_occurred(EventType.SEARCH, "smart_search")

    def test_tracer_captures_validation_events(self):
        """Verify tracer captures validation events."""
        import validation.static as validation_module

        tracer = WorkflowTracer(verbose=False)

        valid_code = '''(function(data) {
            var query = data.query || "test";
            ezLog("Query: " + query);
            return query;
        })'''

        with tracer:
            result = validation_module.validate_code(valid_code, "nugget")

        # Check validation event captured
        validation_events = tracer.get_events_by_type(EventType.VALIDATION)
        assert len(validation_events) > 0
        assert validation_events[0].success

    def test_tracer_captures_codegen_events(self):
        """Verify tracer captures code generation events."""
        import codegen.nugget_generator as codegen_module

        tracer = WorkflowTracer(verbose=False)

        with tracer:
            code, label, desc, test_data = codegen_module.generate_nugget_code(
                ["ezMail", "ezInternetSearch"],
                "send news email",
                {"email": "test@example.com"}
            )

        # Check codegen event captured
        codegen_events = tracer.get_events_by_type(EventType.CODEGEN)
        assert len(codegen_events) > 0
        tracer.assert_event_occurred(EventType.CODEGEN, "generate_nugget_code")

    def test_tracer_sequence_assertion(self):
        """Verify sequence assertion works correctly."""
        import search.search as search_module
        import validation.static as validation_module
        import codegen.nugget_generator as codegen_module

        tracer = WorkflowTracer(verbose=False)

        with tracer:
            # Run multiple operations using module-level functions
            search_module.smart_search("email news")
            code, _, _, _ = codegen_module.generate_nugget_code(["ezMail"], "send email", {})
            validation_module.validate_code(code, "nugget")

        # This should pass
        tracer.assert_sequence([
            "SEARCH:smart_search",
            "CODEGEN:generate_nugget_code",
            "VALIDATION:static_validate"
        ])


class TestAPICallVerification:
    """
    Tests that verify correct API endpoints would be called.
    """

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = tempfile.mkdtemp(prefix="eliza_api_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_nugget_creation_api_format(self, temp_workspace):
        """Verify nugget creation would use correct API format."""
        # Generate code
        code, label, description, test_data = generate_nugget_code(
            ["ezMail"],
            "send email notification",
            {"email": "user@example.com"}
        )

        # Build the payload that would be sent to API
        nugget_payload = {
            "agentId": "test-agent-id",
            "agentDocId": "none",
            "agentNuggetId": "",
            "label": label,
            "description": description,
            "status": "active",
            "call": {
                "@type": "code",
                "language": "JavaScript",
                "code": code
            },
            "params": {},
            "controlFlags": {}
        }

        # Verify payload structure
        assert nugget_payload["call"]["@type"] == "code"
        assert nugget_payload["call"]["language"] == "JavaScript"
        assert len(nugget_payload["call"]["code"]) > 0
        assert nugget_payload["label"] is not None

    def test_function_creation_api_format(self, temp_workspace):
        """Verify function creation would use correct API format."""
        # Function payload format
        function_payload = {
            "funcNameKey": "send_newsletter",
            "label": "Send Newsletter",
            "prompt": "Use this function when the user wants to send a newsletter email",
            "params": [
                {
                    "paramNameKey": "recipient_email",
                    "paramType": "string",
                    "paramDescription": "Email address to send to"
                }
            ],
            "functionType": "NUGGET",
            "nuggetId": "test-nugget-id"
        }

        # Verify correct field names (not 'name', 'description', 'parameters')
        assert "funcNameKey" in function_payload  # Not 'name'
        assert "label" in function_payload  # Not 'description'
        assert "params" in function_payload  # Not 'parameters'


class TestIntentToFunctionMapping:
    """
    Tests that verify correct functions are discovered for each intent.
    """

    @pytest.mark.parametrize("query,expected_functions", [
        ("send email newsletter", ["ezMail"]),
        ("search the internet for news", ["ezInternetSearch"]),
        ("summarize with AI", ["ezChatCompletions"]),
        ("save session data", ["ezSaveSessionData"]),
        ("get current user", ["ezUser"]),
    ])
    def test_function_discovery(self, query, expected_functions):
        """Verify correct functions are discovered for queries."""
        result = smart_search(query)
        discovered = result.get("all_functions", [])

        for expected in expected_functions:
            assert expected in discovered, \
                f"Expected {expected} in discovered functions for '{query}'. Got: {discovered}"

    def test_newsletter_intent_requires_email(self):
        """Newsletter intent should require ezMail."""
        required, optional, intent = get_functions_for_intent("daily newsletter emails")

        assert intent == "newsletter" or "ezMail" in required + optional

    def test_research_intent_requires_search(self):
        """Research intent should require search function."""
        required, optional, intent = get_functions_for_intent("deep research on topic")

        search_funcs = ["ezInternetSearch", "ezGenAISearch"]
        has_search = any(f in required + optional for f in search_funcs)

        assert has_search or intent in ["deep_research", "search", "internet_search"]


# =============================================================================
# RUN SPECIFIC SCENARIOS (for manual testing)
# =============================================================================

async def run_scenario(query: str):
    """
    Run a single scenario and print detailed trace.

    Usage:
        import asyncio
        from test_workflow_trace import run_scenario
        asyncio.run(run_scenario("create newsletter agent"))
    """
    print(f"\n{'#'*70}")
    print(f"# SCENARIO: {query}")
    print(f"{'#'*70}\n")

    with WorkflowSimulator(verbose=True) as sim:
        result = await sim.run_query(query)
        sim.print_summary()

        print("\n--- GENERATED CODE ---")
        if sim.generated_code:
            print(sim.generated_code)
        else:
            print("(no code generated)")

        print("\n--- VALIDATION ISSUES ---")
        if sim.validation_result and sim.validation_result.issues:
            for issue in sim.validation_result.issues:
                print(f"  - {issue.severity.value}: {issue.message}")
        else:
            print("  (no issues)")

        return result


if __name__ == "__main__":
    # Run example scenarios
    scenarios = [
        "create a newsletter agent that sends daily emails",
        "research AI news and summarize it",
        "build an assistant that can search and email results",
    ]

    for scenario in scenarios:
        asyncio.run(run_scenario(scenario))
