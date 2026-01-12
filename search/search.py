"""
EZ Function Search

BM25-style search over ez* functions.
Returns matching function signatures and examples for code generation.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from search.index import EZ_FUNCTION_INDEX, INTENT_PATTERNS


def search_ez_functions(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for ez* functions matching a query.

    Uses keyword matching with scoring to find relevant functions.
    Returns full function info including signature and example.

    Args:
        query: Natural language query (e.g., "send email", "search internet")
        max_results: Maximum number of results to return

    Returns:
        List of matching function definitions with signatures and examples
    """
    query_terms = query.lower().split()
    scores = {}

    for func_name, func_data in EZ_FUNCTION_INDEX.items():
        score = 0

        # Search in keywords (highest weight)
        for term in query_terms:
            for keyword in func_data.get("keywords", []):
                if term in keyword or keyword in term:
                    score += 3

        # Search in description (medium weight)
        desc_lower = func_data.get("description", "").lower()
        for term in query_terms:
            if term in desc_lower:
                score += 2

        # Search in function name (medium weight)
        if any(term in func_name.lower() for term in query_terms):
            score += 2

        if score > 0:
            scores[func_name] = score

    # Sort by score descending
    sorted_matches = sorted(scores.items(), key=lambda x: -x[1])

    # Return top matches with full info
    results = []
    for func_name, score in sorted_matches[:max_results]:
        func_info = EZ_FUNCTION_INDEX[func_name].copy()
        func_info["name"] = func_name
        func_info["match_score"] = score
        results.append(func_info)

    return results


def get_function_signatures(function_names: List[str]) -> str:
    """
    Get formatted signatures and examples for specific functions.

    Args:
        function_names: List of function names to get info for

    Returns:
        Formatted string with signatures and examples
    """
    output = []
    for name in function_names:
        if name in EZ_FUNCTION_INDEX:
            func = EZ_FUNCTION_INDEX[name]
            output.append(f"### {name}")
            output.append(f"Signature: `{func['signature']}`")
            output.append(f"Description: {func['description']}")
            output.append(f"Example:\n```javascript\n{func['example']}\n```")
            if func.get("note"):
                output.append(f"Note: {func['note']}")
            output.append("")

    return "\n".join(output)


def format_search_results(results: List[Dict[str, Any]]) -> str:
    """
    Format search results for display to LLM.

    Args:
        results: List of function info dicts from search_ez_functions

    Returns:
        Formatted string ready for LLM context
    """
    if not results:
        return "No matching ez* functions found."

    output = ["## Discovered ez* Functions\n"]

    for func in results:
        output.append(f"### {func['name']}")
        output.append(f"**Signature:** `{func['signature']}`")
        output.append(f"**Description:** {func['description']}")
        output.append(f"**Status:** {func.get('status', 'UNKNOWN')}")
        output.append(f"\n**Example:**\n```javascript\n{func['example']}\n```")
        if func.get("note"):
            output.append(f"⚠ **Note:** {func['note']}")
        output.append("")

    return "\n".join(output)


# =============================================================================
# INTENT-AWARE SEARCH
# =============================================================================

def detect_intents(query: str) -> List[Dict[str, Any]]:
    """
    Detect user intents from a natural language query.

    Matches query against INTENT_PATTERNS triggers to identify
    what the user is trying to build.

    Args:
        query: Natural language query (e.g., "make me a newsletter agent")

    Returns:
        List of matched intents with their required/optional functions
    """
    query_lower = query.lower()
    matched_intents = []

    for intent_name, intent_data in INTENT_PATTERNS.items():
        score = 0
        matched_triggers = []

        for trigger in intent_data.get("triggers", []):
            if trigger in query_lower:
                # Longer triggers get higher scores (more specific)
                score += len(trigger.split())
                matched_triggers.append(trigger)

        if score > 0:
            matched_intents.append({
                "intent": intent_name,
                "description": intent_data.get("description", ""),
                "score": score,
                "matched_triggers": matched_triggers,
                "requires": intent_data.get("requires", []),
                "optional": intent_data.get("optional", []),
                "example_prompt": intent_data.get("example_prompt", "")
            })

    # Sort by score descending
    matched_intents.sort(key=lambda x: -x["score"])
    return matched_intents


def get_functions_for_intent(query: str) -> Tuple[List[str], List[str], Optional[str]]:
    """
    Get required and optional functions for a user's intent.

    This is the main entry point for intent-aware function discovery.

    Args:
        query: Natural language query

    Returns:
        Tuple of (required_functions, optional_functions, detected_intent_name)
        Returns empty lists if no intent detected
    """
    intents = detect_intents(query)

    if not intents:
        return [], [], None

    # Use the highest-scoring intent
    top_intent = intents[0]
    return (
        top_intent["requires"],
        top_intent["optional"],
        top_intent["intent"]
    )


def smart_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Enhanced search combining intent detection with keyword search.

    This provides a comprehensive search that:
    1. Detects user intent and gets required functions
    2. Falls back to keyword search for additional matches
    3. Combines and deduplicates results

    Args:
        query: Natural language query
        max_results: Maximum results from keyword search

    Returns:
        Dict with:
        - detected_intent: The matched intent name (if any)
        - intent_description: Description of what the intent does
        - required_functions: List of function names that MUST be used
        - optional_functions: List of function names that could help
        - keyword_matches: Additional matches from keyword search
        - all_functions: Deduplicated list of all discovered functions
    """
    # Step 1: Detect intent
    required, optional, intent_name = get_functions_for_intent(query)

    # Step 2: Run keyword search for additional matches
    keyword_results = search_ez_functions(query, max_results)
    keyword_function_names = [r["name"] for r in keyword_results]

    # Step 3: Combine all functions (deduplicated)
    all_functions: Set[str] = set()
    all_functions.update(required)
    all_functions.update(optional)
    all_functions.update(keyword_function_names)

    # Step 4: Build result
    result = {
        "detected_intent": intent_name,
        "intent_description": "",
        "required_functions": required,
        "optional_functions": optional,
        "keyword_matches": keyword_function_names,
        "all_functions": list(all_functions),
        "has_intent": intent_name is not None
    }

    # Add intent description if found
    if intent_name and intent_name in INTENT_PATTERNS:
        result["intent_description"] = INTENT_PATTERNS[intent_name].get("description", "")

    return result


def format_smart_search_results(results: Dict[str, Any]) -> str:
    """
    Format smart search results for display to LLM.

    Args:
        results: Dict from smart_search()

    Returns:
        Formatted string with intent and function information
    """
    output = []

    # Intent detection results
    if results.get("has_intent"):
        output.append("## Detected Intent")
        output.append(f"**Type:** {results['detected_intent']}")
        output.append(f"**Description:** {results.get('intent_description', '')}")
        output.append("")

        if results.get("required_functions"):
            output.append("### Required Functions")
            output.append("These functions are MANDATORY for this use case:")
            for func_name in results["required_functions"]:
                if func_name in EZ_FUNCTION_INDEX:
                    func = EZ_FUNCTION_INDEX[func_name]
                    output.append(f"- **{func_name}**: `{func['signature']}` - {func['description']}")
            output.append("")

        if results.get("optional_functions"):
            output.append("### Optional Functions")
            output.append("These functions may enhance the solution:")
            for func_name in results["optional_functions"]:
                if func_name in EZ_FUNCTION_INDEX:
                    func = EZ_FUNCTION_INDEX[func_name]
                    output.append(f"- **{func_name}**: `{func['signature']}` - {func['description']}")
            output.append("")
    else:
        output.append("## No Specific Intent Detected")
        output.append("Using keyword search to find relevant functions.")
        output.append("")

    # Keyword search results (if any additional)
    additional_matches = set(results.get("keyword_matches", [])) - set(results.get("required_functions", [])) - set(results.get("optional_functions", []))
    if additional_matches:
        output.append("### Additional Keyword Matches")
        for func_name in additional_matches:
            if func_name in EZ_FUNCTION_INDEX:
                func = EZ_FUNCTION_INDEX[func_name]
                output.append(f"- **{func_name}**: `{func['signature']}` - {func['description']}")
        output.append("")

    # Summary
    output.append("### Discovered Functions List")
    output.append(f"`discovered_functions`: {results.get('all_functions', [])}")

    return "\n".join(output)