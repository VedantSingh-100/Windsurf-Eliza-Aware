"""
Nugget Code Generator

Generates JavaScript nugget code using discovered ez* function signatures.
This is the core code generation logic - uses known correct patterns.

SECURITY:
- All user inputs are sanitized before being embedded in generated code
- Email addresses are validated and escaped
- Query strings are length-limited and escaped
"""

import re
from typing import List, Dict, Any, Tuple
from search.index import EZ_FUNCTION_INDEX


# =============================================================================
# SANITIZATION FUNCTIONS
# =============================================================================

def sanitize_string_for_js(s: str, max_length: int = 1000) -> str:
    """
    Sanitize a string for safe embedding in JavaScript code.

    Escapes:
    - Backslashes (\ -> \\)
    - Double quotes (" -> \")
    - Single quotes (' -> \')
    - Newlines (\n -> \\n)
    - Carriage returns (\r -> \\r)
    - Tabs (\t -> \\t)
    - Script tags (</script> -> <\/script>)

    Args:
        s: String to sanitize
        max_length: Maximum allowed length (default 1000)

    Returns:
        Sanitized string safe for JS embedding
    """
    if not s:
        return ""

    if not isinstance(s, str):
        s = str(s)

    # Truncate to max length
    if len(s) > max_length:
        s = s[:max_length]

    # Escape in order (backslash first!)
    s = s.replace("\\", "\\\\")  # Must be first
    s = s.replace('"', '\\"')
    s = s.replace("'", "\\'")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")

    # Prevent script injection
    s = s.replace("</script>", "<\\/script>")
    s = s.replace("</Script>", "<\\/Script>")
    s = s.replace("</SCRIPT>", "<\\/SCRIPT>")

    # Remove null bytes
    s = s.replace("\x00", "")

    return s


def sanitize_email_for_js(email: str) -> str:
    """
    Sanitize and validate email for safe embedding in JavaScript code.

    Args:
        email: Email address to sanitize

    Returns:
        Sanitized email or "user@example.com" if invalid
    """
    if not email:
        return "user@example.com"

    if not isinstance(email, str):
        return "user@example.com"

    # Remove whitespace
    email = email.strip()

    # Basic email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return "user@example.com"

    # Check for dangerous characters
    dangerous = ['"', "'", "\\", "\n", "\r", "<", ">", ";", "(", ")", "{", "}", "`"]
    for char in dangerous:
        if char in email:
            return "user@example.com"

    # Length limit
    if len(email) > 254:  # RFC 5321 limit
        return "user@example.com"

    return email


def sanitize_query_for_js(query: str) -> str:
    """
    Sanitize a search query for safe embedding in JavaScript code.

    Args:
        query: Search query to sanitize

    Returns:
        Sanitized query string, max 500 chars
    """
    if not query:
        return "search query"

    # Use general string sanitizer with 500 char limit
    return sanitize_string_for_js(query, max_length=500)


def generate_nugget_code(
    discovered_functions: List[str],
    requirement: str,
    params: Dict[str, Any] = None
) -> Tuple[str, str, str, Dict]:
    """
    Generate nugget code using discovered function signatures.

    Args:
        discovered_functions: List of ez* function names to use
        requirement: What the nugget should do
        params: Additional parameters (email address, query, etc.)

    Returns:
        Tuple of (code, label, description, test_data)

    SECURITY: All user inputs are sanitized before code generation.
    """
    params = params or {}

    # Extract and SANITIZE user inputs
    email_addr = sanitize_email_for_js(params.get("email") or "user@example.com")
    default_query = sanitize_query_for_js(params.get("query") or "latest news")

    # Determine what combination of functions we have
    # Pick the ACTUAL search function that was discovered
    search_func = None
    for f in ["ezInternetSearch", "ezGenAISearch"]:
        if f in discovered_functions:
            search_func = f
            break

    has_search = search_func is not None
    has_email = "ezMail" in discovered_functions
    has_llm = "ezChatCompletions" in discovered_functions
    has_session = any(f in discovered_functions for f in ["ezSaveSessionData", "ezGetSessionData"])

    # Generate code based on function combination - PASS the actual functions
    if has_search and has_email and has_llm:
        return _generate_search_summarize_email_nugget(email_addr, default_query, search_func)

    if has_search and has_email:
        return _generate_search_email_nugget(email_addr, default_query, search_func)

    if has_search and has_llm:
        return _generate_search_summarize_nugget(default_query, search_func)

    if has_email and not has_search:
        return _generate_email_nugget(email_addr)

    if has_search:
        return _generate_search_nugget(default_query, search_func)

    if has_llm:
        return _generate_llm_nugget()

    if has_session:
        return _generate_session_nugget()

    # Fallback: generate nugget with discovered functions
    return _generate_generic_nugget(discovered_functions, requirement)


def _generate_search_email_nugget(email: str, query: str, search_func: str = "ezInternetSearch") -> Tuple[str, str, str, Dict]:
    """Generate nugget that searches internet and emails results."""
    code = f'''(function(data) {{
    // Step 1: Search the internet
    var query = data.query || "{query}";
    ezLog("Searching for: " + query);
    var searchResults = {search_func}(query);
    ezLog("Search completed");

    // Step 2: Format results for email
    var resultsText = typeof searchResults === "string"
        ? searchResults
        : JSON.stringify(searchResults, null, 2);
    var emailBody = "Search Results for: " + query + "\\n\\n" + resultsText;

    // Step 3: Send email
    var emailPayload = JSON.stringify({{
        to: ["{email}"],
        subject: "Search Results: " + query,
        body: emailBody
    }});
    ezLog("Sending email to {email}");
    var emailResult = ezMail(emailPayload);
    ezLog("Email sent: " + emailResult);

    return "Searched for '" + query + "' and emailed results to {email}. Results preview: " + resultsText.substring(0, 500);
}})'''

    return (
        code,
        "Search and Email",
        f"Searches internet and emails results to {email}",
        {"query": query}
    )


def _generate_search_summarize_nugget(query: str, search_func: str = "ezInternetSearch") -> Tuple[str, str, str, Dict]:
    """Generate nugget that searches and summarizes with LLM."""
    code = f'''(function(data) {{
    // Step 1: Search the internet
    var query = data.query || "{query}";
    ezLog("Searching for: " + query);
    var searchResults = {search_func}(query);

    // Step 2: Summarize with LLM
    var llmRequest = JSON.stringify({{
        "model": "openai-gpt-4.1-mini-ptu",
        "messages": [
            {{"role": "system", "content": "Summarize the following search results concisely."}},
            {{"role": "user", "content": "Search results for '" + query + "':\\n" + searchResults}}
        ],
        "max_tokens": 500
    }});
    var llmResult = ezChatCompletions(llmRequest);
    var summary = JSON.parse(llmResult).textResponse;

    return "Summary of '" + query + "':\\n" + summary;
}})'''

    return (
        code,
        "Search and Summarize",
        "Searches internet and summarizes with AI",
        {"query": query}
    )


def _generate_search_summarize_email_nugget(email: str, query: str, search_func: str = "ezInternetSearch") -> Tuple[str, str, str, Dict]:
    """Generate nugget that searches, summarizes with LLM, and emails."""
    code = f'''(function(data) {{
    // Step 1: Search
    var query = data.query || "{query}";
    ezLog("Searching: " + query);
    var searchResults = {search_func}(query);

    // Step 2: Summarize with LLM
    var llmRequest = JSON.stringify({{
        "model": "openai-gpt-4.1-mini-ptu",
        "messages": [
            {{"role": "system", "content": "Summarize the following search results into a clear, concise email format."}},
            {{"role": "user", "content": "Search results for '" + query + "':\\n" + searchResults}}
        ],
        "max_tokens": 500
    }});
    var llmResult = ezChatCompletions(llmRequest);
    var summary = JSON.parse(llmResult).textResponse;

    // Step 3: Email the summary
    var emailPayload = JSON.stringify({{
        to: ["{email}"],
        subject: "Summary: " + query,
        body: summary
    }});
    ezMail(emailPayload);

    return "Searched, summarized, and emailed to {email}:\\n" + summary;
}})'''

    return (
        code,
        "Search Summarize Email",
        f"Searches, summarizes with AI, emails to {email}",
        {"query": query}
    )


def _generate_email_nugget(email: str) -> Tuple[str, str, str, Dict]:
    """Generate nugget that sends email."""
    code = f'''(function(data) {{
    var to = data.to || ["{email}"];
    var subject = data.subject || "Notification";
    var body = data.body || data.message || "No message provided";

    var emailPayload = JSON.stringify({{
        to: Array.isArray(to) ? to : [to],
        subject: subject,
        body: body
    }});

    ezLog("Sending email to: " + JSON.stringify(to));
    var result = ezMail(emailPayload);
    return "Email sent to " + (Array.isArray(to) ? to.join(", ") : to) + ": " + result;
}})'''

    return (
        code,
        "Send Email",
        "Sends email notification",
        {"to": [email], "subject": "Test", "body": "Test message"}
    )


def _generate_search_nugget(query: str, search_func: str = "ezInternetSearch") -> Tuple[str, str, str, Dict]:
    """Generate nugget that searches internet."""
    code = f'''(function(data) {{
    var query = data.query || "{query}";
    ezLog("Searching for: " + query);
    var results = {search_func}(query);
    return "Search results for '" + query + "': " + results;
}})'''

    return (
        code,
        "Internet Search",
        "Searches the internet",
        {"query": query}
    )


def _generate_llm_nugget() -> Tuple[str, str, str, Dict]:
    """Generate nugget that calls LLM."""
    code = '''(function(data) {
    var request = {
        "model": "openai-gpt-4.1-mini-ptu",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": data.query || data.prompt || "Hello"}
        ],
        "max_tokens": 500
    };
    var result = ezChatCompletions(JSON.stringify(request));
    return JSON.parse(result).textResponse;
})'''

    return (
        code,
        "LLM Chat",
        "Calls LLM to process query",
        {"query": "What is 2+2?"}
    )


def _generate_session_nugget() -> Tuple[str, str, str, Dict]:
    """Generate nugget that uses session data."""
    code = '''(function(data) {
    var key = data.key || "default_key";
    var value = data.value;

    if (value) {
        ezSaveSessionData(key, value);
        return "Saved '" + key + "' = '" + value + "'";
    } else {
        var stored = ezGetSessionData(key);
        return "Value of '" + key + "': " + (stored || "not found");
    }
})'''

    return (
        code,
        "Session Data",
        "Saves/retrieves session data",
        {"key": "test_key", "value": "test_value"}
    )


def _generate_generic_nugget(functions: List[str], requirement: str) -> Tuple[str, str, str, Dict]:
    """
    Generate nugget that chains discovered functions together.

    Uses EZ_FUNCTION_INDEX to get correct signatures and build working code.

    SECURITY: Requirement string is sanitized before embedding.
    """
    # SANITIZE the requirement for use in label/description
    safe_requirement = sanitize_string_for_js(requirement, max_length=200) if requirement else ""

    # Build code blocks for each discovered function
    code_blocks = []
    step = 1
    test_data = {"input": "test"}

    for func_name in functions:
        if func_name not in EZ_FUNCTION_INDEX:
            continue

        func_info = EZ_FUNCTION_INDEX[func_name]
        sig = func_info.get("signature", "")
        example = func_info.get("example", "")

        # Generate appropriate call based on function type
        if func_name == "ezLog":
            code_blocks.append(f'    // Step {step}: Log\n    ezLog("Processing: " + JSON.stringify(data));')
        elif func_name == "ezInternetSearch":
            code_blocks.append(f'    // Step {step}: Search internet\n    var query = data.query || "news";\n    var searchResult = ezInternetSearch(query);')
            test_data["query"] = "test search"
        elif func_name == "ezGenAISearch":
            code_blocks.append(f'    // Step {step}: GenAI Search\n    var query = data.query || "research topic";\n    var searchResult = ezGenAISearch(query);')
            test_data["query"] = "test search"
        elif func_name == "ezChatCompletions":
            code_blocks.append(f'''    // Step {step}: Call LLM
var llmRequest = JSON.stringify({{
"model": "openai-gpt-4.1-mini-ptu",
"messages": [
    {{"role": "system", "content": "You are a helpful assistant."}},
    {{"role": "user", "content": data.prompt || data.query || "Hello"}}
],
"max_tokens": 500
}});
var llmResult = ezChatCompletions(llmRequest);
var llmResponse = JSON.parse(llmResult).textResponse;'''.format(step))
            test_data["prompt"] = "test prompt"
        elif func_name == "ezMail":
            code_blocks.append(f'''    // Step {step}: Send email
var emailPayload = JSON.stringify({{
    to: data.to || ["user@example.com"],
    subject: data.subject || "Notification",
    body: data.body || "Message from nugget"
}});
var emailResult = ezMail(emailPayload);'''.format(step))
            test_data["to"] = ["test@example.com"]
            test_data["subject"] = "Test"
            test_data["body"] = "Test message"
        elif func_name == "ezChat":
            code_blocks.append(f'''    // Step {step}: Chat with agent
var chatRequest = JSON.stringify({{
    agentId: data.agentId,
    message: data.message || data.query
}});
var chatResult = ezChat(chatRequest);'''.format(step))
            test_data["message"] = "test message"
        elif func_name == "ezNugget":
            code_blocks.append(f'''    // Step {step}: Call another nugget
var nuggetRequest = JSON.stringify({{
    agentId: data.agentId,
    nuggetId: data.nuggetId,
    data: data.nuggetData || {{}}
}});
var nuggetResult = ezNugget(nuggetRequest);'''.format(step))
        elif func_name == "ezSaveSessionData":
            code_blocks.append(f'    // Step {step}: Save to session\n    ezSaveSessionData(data.key || "default_key", data.value || "default_value");')
            test_data["key"] = "test_key"
            test_data["value"] = "test_value"
        elif func_name == "ezGetSessionData":
            code_blocks.append(f'    // Step {step}: Get from session\n    var sessionValue = ezGetSessionData(data.key || "default_key");')
            test_data["key"] = "test_key"
        elif func_name == "ezUser":
            code_blocks.append(f'    // Step {step}: Get current user\n    var currentUser = ezUser();')
        elif func_name == "ezNotify":
            code_blocks.append(f'    // Step {step}: Send notification\n    ezNotify(data.message || "Notification from nugget");')
            test_data["message"] = "Test notification"
        elif func_name == "ezConfirm":
            code_blocks.append(f'    // Step {step}: Ask for confirmation\n    var confirmed = ezConfirm(data.message || "Proceed?");')
        elif func_name == "sleep":
            code_blocks.append(f'    // Step {step}: Wait\n    sleep(data.ms || 1000);')
        else:
            # Generic handling for other functions - use example from index
            code_blocks.append(f'    // Step {step}: {func_name}\n    // Signature: {sig}\n    // Example: {example}')

        step += 1

    # Build the complete nugget
    blocks_code = "\n\n".join(code_blocks) if code_blocks else '    ezLog("No functions to execute");'

    # Determine return value based on what functions were used
    return_expr = '"Completed"'
    if "ezChatCompletions" in functions:
        return_expr = 'llmResponse'
    elif "ezInternetSearch" in functions or "ezGenAISearch" in functions:
        return_expr = 'searchResult'
    elif "ezChat" in functions:
        return_expr = 'chatResult'
    elif "ezNugget" in functions:
        return_expr = 'nuggetResult'
    elif "ezGetSessionData" in functions:
        return_expr = 'sessionValue'
    elif "ezUser" in functions:
        return_expr = 'JSON.stringify(currentUser)'

    code = f'''(function(data) {{
ezLog("Starting nugget execution");

{blocks_code}

ezLog("Nugget completed");
return {return_expr};
}})'''

    # Generate label from requirement or function names (use sanitized version)
    label = safe_requirement[:30] if safe_requirement else " + ".join(functions[:2])
    if len(label) > 30:
        label = label[:27] + "..."

    return (
        code,
        label or "Custom Nugget",
        safe_requirement or f"Executes: {', '.join(functions)}",
        test_data
    )