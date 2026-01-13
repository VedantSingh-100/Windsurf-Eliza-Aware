"""
Tests for Artifact Discovery Module

Tests auto-discovery of existing Eliza artifacts:
- Pattern matching for nuggets, agents, functions
- Metadata extraction from file headers
- Sync discovered artifacts to state
- Exclusion patterns (node_modules, tests, etc.)
"""

import pytest
import os
import sys
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.discovery import (
    DEFAULT_DISCOVERY_PATTERNS,
    EXCLUDE_PATTERNS,
    discover_artifacts,
    extract_artifact_metadata,
    extract_label_from_filename,
    parse_file_header,
    sync_discovered_to_state,
    classify_artifact_type,
    get_discovery_summary,
    should_exclude,
)
from tools.workflow_state import (
    create_empty_state_v2,
    save_state,
    load_state,
    get_artifact_by_path,
    list_artifacts,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    workspace = tempfile.mkdtemp(prefix="eliza_discovery_")
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def workspace_with_nuggets(temp_workspace):
    """Create workspace with sample nugget files."""
    # Create nuggets directory
    nuggets_dir = os.path.join(temp_workspace, "nuggets")
    os.makedirs(nuggets_dir)

    # Create sample nugget files
    nugget_files = [
        ("email.nugget.js", '''/**
 * Eliza Nugget: Send Email
 * Agent ID: 12345678-1234-1234-1234-123456789abc
 * Description: Sends email using ezMail function
 */
(function(data) {
    var result = ezMail(data.to, data.subject, data.body);
    return JSON.stringify(result);
})()'''),
        ("search.nugget.js", '''/**
 * Eliza Nugget: Internet Search
 * Description: Performs internet search
 */
(function(data) {
    return ezInternetSearch(data.query);
})()'''),
        ("simple.nugget.js", "(function(data) { return ezLog(data); })()"),
    ]

    for filename, content in nugget_files:
        with open(os.path.join(nuggets_dir, filename), 'w') as f:
            f.write(content)

    return temp_workspace


@pytest.fixture
def workspace_with_agents(temp_workspace):
    """Create workspace with sample Python agent files."""
    agents_dir = os.path.join(temp_workspace, "agents")
    os.makedirs(agents_dir)

    agent_files = [
        ("newsletter_agent.py", '''"""
Newsletter Agent

Sends daily newsletter emails to subscribers.
"""

from bnym_eliza.genai.agent import Agent

class NewsletterAgent:
    def __init__(self):
        self.agent_id = "98765432-1234-1234-1234-123456789abc"
'''),
        ("research_eliza.py", '''"""
Research Assistant using Eliza SDK
"""

agent_id = "abcd1234-1234-1234-1234-123456789abc"
'''),
    ]

    for filename, content in agent_files:
        with open(os.path.join(agents_dir, filename), 'w') as f:
            f.write(content)

    return temp_workspace


@pytest.fixture
def workspace_mixed(temp_workspace):
    """Create workspace with mix of nuggets, agents, and excluded files."""
    # Nuggets
    nuggets_dir = os.path.join(temp_workspace, "nuggets")
    os.makedirs(nuggets_dir)
    with open(os.path.join(nuggets_dir, "valid.nugget.js"), 'w') as f:
        f.write("(function(data) { return ezLog(data); })()")

    # Agents
    with open(os.path.join(temp_workspace, "my_agent.py"), 'w') as f:
        f.write("# Agent file")

    # Test files (should be excluded)
    tests_dir = os.path.join(temp_workspace, "tests")
    os.makedirs(tests_dir)
    with open(os.path.join(tests_dir, "test_nugget.js"), 'w') as f:
        f.write("// Test file")

    # Node modules (should be excluded)
    node_dir = os.path.join(temp_workspace, "node_modules", "some_package")
    os.makedirs(node_dir)
    with open(os.path.join(node_dir, "nugget.js"), 'w') as f:
        f.write("// Excluded")

    return temp_workspace


# =============================================================================
# PATTERN MATCHING TESTS
# =============================================================================

class TestPatternMatching:
    """Test artifact discovery patterns."""

    def test_default_patterns_exist(self):
        """Test that default patterns are defined."""
        assert "nugget" in DEFAULT_DISCOVERY_PATTERNS
        assert "agent" in DEFAULT_DISCOVERY_PATTERNS
        assert "function" in DEFAULT_DISCOVERY_PATTERNS

    def test_nugget_patterns(self):
        """Test nugget discovery patterns."""
        patterns = DEFAULT_DISCOVERY_PATTERNS["nugget"]
        assert any("*.nugget.js" in p for p in patterns)
        assert any("nuggets" in p for p in patterns)

    def test_agent_patterns(self):
        """Test agent discovery patterns."""
        patterns = DEFAULT_DISCOVERY_PATTERNS["agent"]
        assert any("agent" in p.lower() for p in patterns)
        assert any("eliza" in p.lower() for p in patterns)

    def test_exclude_patterns(self):
        """Test exclusion patterns."""
        assert any("node_modules" in p for p in EXCLUDE_PATTERNS)
        assert any(".git" in p for p in EXCLUDE_PATTERNS)
        assert any("test" in p.lower() for p in EXCLUDE_PATTERNS)


# =============================================================================
# DISCOVERY TESTS
# =============================================================================

class TestDiscovery:
    """Test artifact discovery functionality."""

    def test_discover_nuggets(self, workspace_with_nuggets):
        """Test discovering nugget files."""
        discovered = discover_artifacts(workspace_with_nuggets)

        assert len(discovered) >= 3
        nuggets = [d for d in discovered if d["type"] == "nugget"]
        assert len(nuggets) == 3

    def test_discover_agents(self, workspace_with_agents):
        """Test discovering agent files."""
        discovered = discover_artifacts(workspace_with_agents)

        agents = [d for d in discovered if d["type"] == "agent"]
        assert len(agents) == 2

    def test_discover_excludes_tests(self, workspace_mixed):
        """Test that test files are excluded."""
        discovered = discover_artifacts(workspace_mixed)

        paths = [d["relative_path"] for d in discovered]
        assert not any("tests" in p for p in paths)

    def test_discover_excludes_node_modules(self, workspace_mixed):
        """Test that node_modules are excluded."""
        discovered = discover_artifacts(workspace_mixed)

        paths = [d["file_path"] for d in discovered]
        assert not any("node_modules" in p for p in paths)

    def test_discover_with_include_tests(self, workspace_mixed):
        """Test discovering with include_tests=True."""
        discovered = discover_artifacts(workspace_mixed, include_tests=True)

        # Should find more files when tests included
        # Note: This depends on patterns matching test files
        paths = [d["relative_path"] for d in discovered]
        # At minimum should find the non-test files
        assert len(discovered) >= 2

    def test_discover_custom_patterns(self, temp_workspace):
        """Test discovery with custom patterns."""
        # Create file with custom pattern
        custom_dir = os.path.join(temp_workspace, "custom")
        os.makedirs(custom_dir)
        with open(os.path.join(custom_dir, "my_custom_file.xyz"), 'w') as f:
            f.write("custom content")

        custom_patterns = {
            "custom": ["**/*.xyz"]
        }

        discovered = discover_artifacts(temp_workspace, patterns=custom_patterns)

        assert len(discovered) == 1
        assert discovered[0]["type"] == "custom"


# =============================================================================
# METADATA EXTRACTION TESTS
# =============================================================================

class TestMetadataExtraction:
    """Test metadata extraction from files."""

    def test_extract_label_from_filename_nugget(self):
        """Test extracting label from nugget filename."""
        label = extract_label_from_filename("send_email.nugget.js", "nugget")
        assert label == "Send Email"

        label = extract_label_from_filename("my-cool-nugget.js", "nugget")
        assert label == "My Cool Nugget"

    def test_extract_label_from_filename_agent(self):
        """Test extracting label from agent filename."""
        label = extract_label_from_filename("newsletter_agent.py", "agent")
        assert label == "Newsletter Agent"

    def test_parse_nugget_header(self):
        """Test parsing nugget file header."""
        content = '''/**
 * Eliza Nugget: My Email Sender
 * Agent ID: 12345678-1234-1234-1234-123456789abc
 * Nugget ID: abcdef12-3456-7890-abcd-ef1234567890
 * Description: Sends emails using the ezMail function
 */
(function(data) { })()'''

        metadata = parse_file_header(content, "nugget")

        assert metadata.get("label") == "My Email Sender"
        assert metadata.get("agent_id") == "12345678-1234-1234-1234-123456789abc"
        assert metadata.get("nugget_id") == "abcdef12-3456-7890-abcd-ef1234567890"
        assert "email" in metadata.get("description", "").lower()

    def test_parse_agent_header(self):
        """Test parsing Python agent file header."""
        content = '''"""
Newsletter Email Agent

This agent sends daily newsletter emails to subscribers.
"""

class NewsletterAgent:
    agent_id = "12345678-1234-1234-1234-123456789abc"
'''

        metadata = parse_file_header(content, "agent")

        assert "Newsletter" in metadata.get("description", "")
        assert metadata.get("agent_id") == "12345678-1234-1234-1234-123456789abc"

    def test_parse_agent_class_name(self):
        """Test extracting label from class name."""
        content = '''class MyAwesomeAgent:
    pass
'''
        metadata = parse_file_header(content, "agent")
        assert metadata.get("label") == "My Awesome Agent"

    def test_extract_artifact_metadata(self, workspace_with_nuggets):
        """Test full metadata extraction."""
        nugget_path = os.path.join(
            workspace_with_nuggets, "nuggets", "email.nugget.js"
        )

        metadata = extract_artifact_metadata(
            nugget_path, "nugget", workspace_with_nuggets
        )

        assert metadata["type"] == "nugget"
        assert metadata["label"] == "Send Email"  # From header
        assert metadata["agent_id"] == "12345678-1234-1234-1234-123456789abc"
        assert "email" in metadata["description"].lower()
        assert metadata["relative_path"] == "nuggets/email.nugget.js"


# =============================================================================
# STATE SYNC TESTS
# =============================================================================

class TestStateSync:
    """Test syncing discovered artifacts to workflow state."""

    def test_sync_discovered_to_state(self, workspace_with_nuggets):
        """Test syncing discovered artifacts to state."""
        # Create v2 state
        state = create_empty_state_v2(workspace_with_nuggets)
        save_state(workspace_with_nuggets, state)

        # Discover artifacts
        discovered = discover_artifacts(workspace_with_nuggets)

        # Sync to state
        state = load_state(workspace_with_nuggets)
        added_ids, skipped_paths = sync_discovered_to_state(
            workspace_with_nuggets, discovered, state
        )

        assert len(added_ids) == len(discovered)
        assert len(skipped_paths) == 0

        # Verify in state
        state = load_state(workspace_with_nuggets)
        assert len(state["artifacts"]) == len(discovered)

    def test_sync_skips_already_tracked(self, workspace_with_nuggets):
        """Test that sync skips already-tracked files."""
        state = create_empty_state_v2(workspace_with_nuggets)
        save_state(workspace_with_nuggets, state)

        discovered = discover_artifacts(workspace_with_nuggets)

        # First sync
        state = load_state(workspace_with_nuggets)
        added_ids, _ = sync_discovered_to_state(
            workspace_with_nuggets, discovered, state
        )
        first_count = len(added_ids)

        # Second sync (should skip all)
        state = load_state(workspace_with_nuggets)
        added_ids, skipped_paths = sync_discovered_to_state(
            workspace_with_nuggets, discovered, state
        )

        assert len(added_ids) == 0
        assert len(skipped_paths) == first_count

    def test_sync_incremental(self, workspace_with_nuggets):
        """Test incremental sync when new files added."""
        state = create_empty_state_v2(workspace_with_nuggets)
        save_state(workspace_with_nuggets, state)

        # First discovery and sync
        discovered = discover_artifacts(workspace_with_nuggets)
        state = load_state(workspace_with_nuggets)
        sync_discovered_to_state(workspace_with_nuggets, discovered, state)

        initial_count = len(load_state(workspace_with_nuggets)["artifacts"])

        # Add new file
        new_nugget_path = os.path.join(
            workspace_with_nuggets, "nuggets", "new.nugget.js"
        )
        with open(new_nugget_path, 'w') as f:
            f.write("(function(data) { return ezLog(data); })()")

        # Second discovery and sync
        discovered = discover_artifacts(workspace_with_nuggets)
        state = load_state(workspace_with_nuggets)
        added_ids, skipped_paths = sync_discovered_to_state(
            workspace_with_nuggets, discovered, state
        )

        assert len(added_ids) == 1  # Only the new file
        assert len(skipped_paths) == initial_count

        final_count = len(load_state(workspace_with_nuggets)["artifacts"])
        assert final_count == initial_count + 1


# =============================================================================
# CLASSIFICATION TESTS
# =============================================================================

class TestClassification:
    """Test artifact type classification."""

    def test_classify_nugget_by_extension(self):
        """Test classifying nugget by .nugget.js extension."""
        assert classify_artifact_type("/path/to/my.nugget.js") == "nugget"
        assert classify_artifact_type("/path/to/my.nugget.ts") == "nugget"

    def test_classify_nugget_by_directory(self):
        """Test classifying nugget by nuggets directory."""
        assert classify_artifact_type("/workspace/nuggets/file.js") == "nugget"
        assert classify_artifact_type("/workspace/nuggets/12345/code.js") == "nugget"

    def test_classify_nugget_by_name(self):
        """Test classifying nugget by name containing 'nugget'."""
        assert classify_artifact_type("/path/my_nugget_code.js") == "nugget"

    def test_classify_agent(self):
        """Test classifying agent files."""
        assert classify_artifact_type("/path/newsletter_agent.py") == "agent"
        assert classify_artifact_type("/path/my_eliza_code.py") == "agent"

    def test_classify_function(self):
        """Test classifying function files."""
        assert classify_artifact_type("/path/create_function.py") == "function"
        assert classify_artifact_type("/path/my_function_helper.py") == "function"

    def test_classify_unknown(self):
        """Test classifying unknown files."""
        assert classify_artifact_type("/path/readme.md") == "unknown"
        assert classify_artifact_type("/path/config.json") == "unknown"


# =============================================================================
# EXCLUSION TESTS
# =============================================================================

class TestExclusion:
    """Test file exclusion logic."""

    def test_should_exclude_node_modules(self, temp_workspace):
        """Test that node_modules are excluded."""
        path = os.path.join(temp_workspace, "node_modules", "pkg", "file.js")
        assert should_exclude(path, temp_workspace) is True

    def test_should_exclude_git(self, temp_workspace):
        """Test that .git directory is excluded."""
        path = os.path.join(temp_workspace, ".git", "objects", "file")
        assert should_exclude(path, temp_workspace) is True

    def test_should_exclude_tests(self, temp_workspace):
        """Test that test directories are excluded."""
        path = os.path.join(temp_workspace, "tests", "test_file.py")
        assert should_exclude(path, temp_workspace) is True

    def test_should_exclude_test_files(self, temp_workspace):
        """Test that test files are excluded."""
        path = os.path.join(temp_workspace, "src", "module.test.js")
        assert should_exclude(path, temp_workspace) is True

        path = os.path.join(temp_workspace, "src", "module.spec.ts")
        assert should_exclude(path, temp_workspace) is True

    def test_should_not_exclude_valid(self, temp_workspace):
        """Test that valid files are not excluded."""
        path = os.path.join(temp_workspace, "nuggets", "email.nugget.js")
        assert should_exclude(path, temp_workspace) is False

        path = os.path.join(temp_workspace, "src", "agent.py")
        assert should_exclude(path, temp_workspace) is False


# =============================================================================
# DISCOVERY SUMMARY TESTS
# =============================================================================

class TestDiscoverySummary:
    """Test discovery summary generation."""

    def test_get_discovery_summary(self, workspace_with_nuggets):
        """Test generating discovery summary."""
        discovered = discover_artifacts(workspace_with_nuggets)
        summary = get_discovery_summary(workspace_with_nuggets, discovered)

        assert summary["workspace_path"] == workspace_with_nuggets
        assert summary["total_discovered"] == 3
        assert "nugget" in summary["by_type"]
        assert summary["by_type"]["nugget"] == 3
        assert "discovered_at" in summary

    def test_summary_mixed_types(self, workspace_mixed):
        """Test summary with mixed artifact types."""
        discovered = discover_artifacts(workspace_mixed)
        summary = get_discovery_summary(workspace_mixed, discovered)

        # Should have both nuggets and agents
        assert summary["total_discovered"] >= 2
        assert "artifacts" in summary


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestDiscoveryIntegration:
    """Integration tests for discovery workflow."""

    def test_full_discovery_workflow(self, workspace_with_nuggets):
        """Test complete discovery workflow."""
        # 1. Create v2 state
        state = create_empty_state_v2(workspace_with_nuggets)
        state["credentials"]["jwt_provided"] = True
        state["credentials"]["env_file_written"] = True
        save_state(workspace_with_nuggets, state)

        # 2. Discover artifacts
        discovered = discover_artifacts(workspace_with_nuggets)
        assert len(discovered) > 0

        # 3. Sync to state
        state = load_state(workspace_with_nuggets)
        added_ids, _ = sync_discovered_to_state(
            workspace_with_nuggets, discovered, state
        )
        assert len(added_ids) == len(discovered)

        # 4. Verify artifacts are in state
        state = load_state(workspace_with_nuggets)
        artifacts = list_artifacts(state)
        assert len(artifacts) == len(discovered)

        # 5. Verify lookup by path works
        email_path = os.path.join(
            workspace_with_nuggets, "nuggets", "email.nugget.js"
        )
        artifact = get_artifact_by_path(state, email_path)
        assert artifact is not None
        assert artifact["discovered"] is True

    def test_discovery_midway_start(self, workspace_with_nuggets):
        """Test discovery for midway start scenario."""
        # Scenario: Developer has existing files, starts using workflow midway

        # 1. NO state exists yet (simulating midway start)
        state_file = os.path.join(workspace_with_nuggets, ".eliza", "workflow_state.json")
        assert not os.path.exists(state_file)

        # 2. Developer would call eliza_workflow(action='discover')
        # This creates state and discovers files

        # Create v2 state
        state = create_empty_state_v2(workspace_with_nuggets)
        save_state(workspace_with_nuggets, state)

        # Discover
        discovered = discover_artifacts(workspace_with_nuggets)

        # Sync
        state = load_state(workspace_with_nuggets)
        sync_discovered_to_state(workspace_with_nuggets, discovered, state)

        # 3. All existing files should now be tracked
        state = load_state(workspace_with_nuggets)
        assert len(state["artifacts"]) == 3

        # 4. Each artifact should be marked as discovered
        for artifact in state["artifacts"]:
            assert artifact["discovered"] is True
            assert artifact["workflow_step"] == "INIT"  # Ready for workflow
