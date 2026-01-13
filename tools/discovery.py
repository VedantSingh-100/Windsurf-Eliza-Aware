"""
Artifact Discovery Module

Scans workspace for existing Eliza artifacts and registers them in workflow state.
Supports incremental discovery (won't duplicate already-tracked files).

This module enables developers to:
- Start using the workflow system midway with existing files
- Auto-discover nuggets, agents, and functions in the workspace
- Register discovered files for workflow tracking
"""

import os
import re
import glob
import fnmatch
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime


# Default patterns for discovering Eliza artifacts
# Aligned with .windsurf/hooks.json file patterns
DEFAULT_DISCOVERY_PATTERNS = {
    "nugget": [
        "**/*.nugget.js",
        "**/*.nugget.ts",
        "**/nuggets/**/*.js",
        "**/nuggets/**/*.ts",
        "**/*nugget*.js",
        "**/*nugget*.ts",
    ],
    "agent": [
        "**/*agent*.py",
        "**/*eliza*.py",
    ],
    "function": [
        "**/*function*.py",
    ]
}

# Patterns to exclude from discovery
EXCLUDE_PATTERNS = [
    "**/node_modules/**",
    "**/.git/**",
    "**/__pycache__/**",
    "**/.eliza/**",
    "**/test*/**",
    "**/tests/**",
    "**/*.test.*",
    "**/*.spec.*",
    "**/conftest.py",
    "**/.venv/**",
    "**/venv/**",
    "**/dist/**",
    "**/build/**",
]


def should_exclude(file_path: str, workspace_path: str) -> bool:
    """
    Check if file should be excluded from discovery.

    Args:
        file_path: Absolute path to the file
        workspace_path: Root workspace path

    Returns:
        True if file should be excluded
    """
    rel_path = os.path.relpath(file_path, workspace_path)

    for pattern in EXCLUDE_PATTERNS:
        # Convert glob pattern to work with fnmatch
        # Remove leading **/ for matching
        simple_pattern = pattern.replace("**/", "")
        if fnmatch.fnmatch(rel_path, simple_pattern):
            return True
        if fnmatch.fnmatch(rel_path, pattern.lstrip("*/")):
            return True
        # Check if any path component matches
        parts = rel_path.split(os.sep)
        for part in parts:
            if fnmatch.fnmatch(part, simple_pattern.rstrip("/**")):
                return True

    return False


def discover_artifacts(
    workspace_path: str,
    patterns: Optional[Dict[str, List[str]]] = None,
    include_tests: bool = False
) -> List[Dict[str, Any]]:
    """
    Discover Eliza artifacts in workspace.

    Scans the workspace using glob patterns to find nugget, agent, and function
    files. Returns metadata about each discovered file.

    Args:
        workspace_path: Root directory to scan
        patterns: Custom patterns by type (optional, uses defaults if not provided)
        include_tests: Whether to include test files (default False)

    Returns:
        List of discovered artifacts with metadata:
        - file_path: Absolute path to file
        - relative_path: Path relative to workspace
        - type: "nugget", "agent", or "function"
        - label: Human-readable label extracted from filename
        - description: Description extracted from file (if available)
        - agent_id: Agent ID extracted from file header (if available)
        - discovered_at: Timestamp of discovery
    """
    patterns = patterns or DEFAULT_DISCOVERY_PATTERNS
    discovered = []
    seen_paths = set()

    for artifact_type, type_patterns in patterns.items():
        for pattern in type_patterns:
            full_pattern = os.path.join(workspace_path, pattern)
            matches = glob.glob(full_pattern, recursive=True)

            for file_path in matches:
                # Normalize path
                file_path = os.path.normpath(os.path.abspath(file_path))

                # Skip if already seen
                if file_path in seen_paths:
                    continue

                # Skip if excluded
                if not include_tests and should_exclude(file_path, workspace_path):
                    continue

                # Skip if not a file
                if not os.path.isfile(file_path):
                    continue

                seen_paths.add(file_path)

                # Extract metadata
                metadata = extract_artifact_metadata(file_path, artifact_type, workspace_path)
                discovered.append(metadata)

    return discovered


def extract_artifact_metadata(
    file_path: str,
    artifact_type: str,
    workspace_path: str
) -> Dict[str, Any]:
    """
    Extract metadata from discovered artifact file.

    Parses file headers and content to extract useful metadata like
    labels, descriptions, and IDs.

    Args:
        file_path: Absolute path to the artifact file
        artifact_type: Type of artifact ("nugget", "agent", "function")
        workspace_path: Root workspace path

    Returns:
        Dict with artifact metadata
    """
    rel_path = os.path.relpath(file_path, workspace_path)
    basename = os.path.basename(file_path)

    # Extract label from filename
    label = extract_label_from_filename(basename, artifact_type)

    # Try to extract more metadata from file content
    content_metadata = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(4000)  # First 4KB
            content_metadata = parse_file_header(content, artifact_type)
    except (IOError, UnicodeDecodeError):
        pass

    # Get file modification time
    try:
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
    except OSError:
        file_mtime = None

    return {
        "file_path": file_path,
        "relative_path": rel_path,
        "type": artifact_type,
        "label": content_metadata.get("label", label),
        "description": content_metadata.get("description"),
        "agent_id": content_metadata.get("agent_id"),
        "nugget_id": content_metadata.get("nugget_id"),
        "discovered_at": datetime.utcnow().isoformat(),
        "file_modified": file_mtime
    }


def extract_label_from_filename(basename: str, artifact_type: str) -> str:
    """
    Extract a human-readable label from filename.

    Args:
        basename: Filename without path
        artifact_type: Type of artifact

    Returns:
        Human-readable label
    """
    label = basename

    if artifact_type == "nugget":
        # Remove .nugget.js, .nugget.ts extensions
        label = re.sub(r'\.(nugget\.)?(js|ts)$', '', basename)
    elif artifact_type in ("agent", "function"):
        # Remove .py extension
        label = re.sub(r'\.py$', '', basename)

    # Convert underscores/dashes to spaces and title case
    label = re.sub(r'[_-]+', ' ', label)
    return label.title().strip()


def parse_file_header(content: str, artifact_type: str) -> Dict[str, Any]:
    """
    Parse file header comments for metadata.

    Looks for special comments/docstrings that contain metadata like:
    - Eliza Nugget: <label>
    - Agent ID: <uuid>
    - Description: <text>

    Args:
        content: File content (first few KB)
        artifact_type: Type of artifact

    Returns:
        Dict with extracted metadata
    """
    metadata = {}

    if artifact_type == "nugget":
        # Look for header comments in JavaScript/TypeScript
        # Format: * Eliza Nugget: <label>
        label_match = re.search(r'\*\s*Eliza Nugget:\s*(.+)', content, re.IGNORECASE)
        if label_match:
            metadata["label"] = label_match.group(1).strip()

        # Format: * Agent ID: <uuid>
        agent_match = re.search(r'\*\s*Agent ID:\s*([a-f0-9-]+)', content, re.IGNORECASE)
        if agent_match:
            metadata["agent_id"] = agent_match.group(1)

        # Format: * Nugget ID: <uuid>
        nugget_match = re.search(r'\*\s*Nugget ID:\s*([a-f0-9-]+)', content, re.IGNORECASE)
        if nugget_match:
            metadata["nugget_id"] = nugget_match.group(1)

        # Format: * Description: <text>
        desc_match = re.search(r'\*\s*Description:\s*(.+)', content, re.IGNORECASE)
        if desc_match:
            metadata["description"] = desc_match.group(1).strip()[:200]

    elif artifact_type in ("agent", "function"):
        # Look for Python docstrings
        docstring_match = re.search(r'"""(.+?)"""', content, re.DOTALL)
        if docstring_match:
            doc = docstring_match.group(1).strip()
            # First line is usually the summary
            first_line = doc.split('\n')[0].strip()
            metadata["description"] = first_line[:200]

        # Look for agent_id in Python code
        agent_id_match = re.search(r'agent_id\s*=\s*["\']([a-f0-9-]+)["\']', content, re.IGNORECASE)
        if agent_id_match:
            metadata["agent_id"] = agent_id_match.group(1)

        # Look for class name for agents
        if artifact_type == "agent":
            class_match = re.search(r'class\s+(\w+Agent)\s*[:\(]', content)
            if class_match:
                class_name = class_match.group(1)
                # Convert CamelCase to spaces
                label = re.sub(r'([a-z])([A-Z])', r'\1 \2', class_name)
                metadata["label"] = label

    return metadata


def sync_discovered_to_state(
    workspace_path: str,
    discovered: List[Dict[str, Any]],
    state: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    """
    Sync discovered artifacts to workflow state.

    Adds newly discovered artifacts to the state's artifacts array.
    Skips files that are already tracked.

    Args:
        workspace_path: Root workspace path
        discovered: List of discovered artifact metadata
        state: Current workflow state (v2.0)

    Returns:
        Tuple of (added_artifact_ids, skipped_file_paths)
    """
    # Import here to avoid circular imports
    from tools.workflow_state import add_artifact, get_artifact_by_path

    added_ids = []
    skipped_paths = []

    for artifact in discovered:
        file_path = artifact["file_path"]

        # Check if already tracked
        existing = get_artifact_by_path(state, file_path)
        if existing:
            skipped_paths.append(file_path)
            continue

        # Add new artifact
        state, artifact_id = add_artifact(
            workspace_path,
            artifact_type=artifact["type"],
            label=artifact["label"],
            file_path=file_path,
            discovered=True
        )
        added_ids.append(artifact_id)

    return added_ids, skipped_paths


def classify_artifact_type(file_path: str) -> str:
    """
    Classify artifact type from file path.

    Uses filename patterns to determine if a file is a nugget, agent, or function.

    Args:
        file_path: Path to the artifact file

    Returns:
        Artifact type: "nugget", "agent", "function", or "unknown"
    """
    path_lower = file_path.lower()
    basename = os.path.basename(path_lower)

    # Check for nugget patterns
    if '.nugget.' in path_lower:
        return "nugget"
    if '/nuggets/' in path_lower or '\\nuggets\\' in path_lower:
        return "nugget"
    if 'nugget' in basename and (basename.endswith('.js') or basename.endswith('.ts')):
        return "nugget"

    # Check for agent patterns
    if 'agent' in basename and basename.endswith('.py'):
        return "agent"
    if 'eliza' in basename and basename.endswith('.py'):
        return "agent"

    # Check for function patterns
    if 'function' in basename and basename.endswith('.py'):
        return "function"

    return "unknown"


def get_discovery_summary(
    workspace_path: str,
    discovered: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate a summary of discovered artifacts.

    Args:
        workspace_path: Root workspace path
        discovered: List of discovered artifact metadata

    Returns:
        Summary dict with counts by type, list of files, etc.
    """
    by_type = {}
    for artifact in discovered:
        artifact_type = artifact["type"]
        if artifact_type not in by_type:
            by_type[artifact_type] = []
        by_type[artifact_type].append({
            "label": artifact["label"],
            "relative_path": artifact["relative_path"],
            "file_modified": artifact.get("file_modified")
        })

    return {
        "workspace_path": workspace_path,
        "total_discovered": len(discovered),
        "by_type": {k: len(v) for k, v in by_type.items()},
        "artifacts": by_type,
        "discovered_at": datetime.utcnow().isoformat()
    }
