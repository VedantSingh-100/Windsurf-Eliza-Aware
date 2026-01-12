"""
Eliza Static Validator
Performs AST-based validation of Eliza code without executing it.

Validates:
- Python code for agents, functions, documents
- JavaScript code for nuggets
- Field names, model prefixes, patterns
- Architectural constraints (PYTHON_STATIC can't call MCP, etc.)
"""

import ast
import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    ERROR = "error"      # Will definitely fail
    WARNING = "warning"  # Might fail or is bad practice
    INFO = "info"        # Suggestion for improvement


@dataclass
class ValidationIssue:
    severity: Severity
    message: str
    line: Optional[int] = None
    fix: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class ValidationResult:
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    fixed_code: Optional[str] = None
    code_type: Optional[str] = None  # agent, nugget, function, document

    def to_dict(self) -> Dict:
        return {
            "valid": self.valid,
            "issues": [
                {
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "line": issue.line,
                    "fix": issue.fix,
                    "auto_fixable": issue.auto_fixable
                }
                for issue in self.issues
            ],
            "fixed_code": self.fixed_code,
            "code_type": self.code_type
        }


# ============================================================================
# VALIDATION RULES (from validated knowledge)
# ============================================================================

# Correct field names for functions
FUNCTION_FIELD_MAPPINGS = {
    "name": ("funcNameKey", "Use 'funcNameKey' not 'name' for function identifier"),
    "description": ("label", "Use 'label' not 'description' for function display name"),
    "parameters": ("params", "Use 'params' not 'parameters' for function parameters"),
}

# Correct field names for agents
AGENT_FIELD_MAPPINGS = {
    "agentName": ("agent_name", "SDK uses 'agent_name' not 'agentName'"),
    "agentDescription": ("agent_description", "SDK uses 'agent_description' not 'agentDescription'"),
}

# Wrong SDK patterns that don't exist
WRONG_SDK_PATTERNS = [
    (r"eliza\.Agent\.load\s*\(",
     "eliza.Agent.load() does not exist",
     "Use: from bnym_eliza.genai.agent import Agent; agent = Agent(env='QA', agent_id='...')"),
    (r"eliza\.Agent\s*\(",
     "eliza.Agent() is wrong - Agent must be imported from bnym_eliza.genai.agent",
     "Add: from bnym_eliza.genai.agent import Agent"),
    (r"agent\.load\s*\(",
     "agent.load() does not exist",
     "Use: agent = Agent(env='QA', agent_id='...') - loading happens automatically"),
    (r"Agent\.create\s*\(",
     "Agent.create() is not a class method",
     "Use: agent = Agent(...); agent.create()"),
    (r"eliza\.ChatCompletion\.create\s*\(",
     "Wrong pattern - use eliza.chat.ChatCompletion.create()",
     "Use: from bnym_eliza.chat import ChatCompletion; ChatCompletion.create(...)"),
    (r"agent\.query\s*\(",
     "agent.query() does not exist - use agent.chat()",
     "Use: response = agent.chat(query='your question')"),
    (r"agent\.search\s*\(",
     "agent.search() does not exist - use agent.search_documents()",
     "Use: results = agent.search_documents(content=['query'])"),
]

# Model name patterns
VALID_MODEL_PREFIXES = ["openai-", "bnym-", "google-"]
COMMON_WRONG_MODELS = {
    "gpt-4": "openai-gpt-4",
    "gpt-4o": "openai-gpt-4o",
    "gpt-4-turbo": "openai-gpt-4-turbo",
    "gpt-3.5-turbo": "openai-gpt-3.5-turbo",
    "gpt-4.1-mini": "openai-gpt-4.1-mini",
    "llama": "bnym-llama-3.3-70b-instruct",
    "mistral": "bnym-mistral-7b-instruct",
    "gemini": "google-gemini-1.5-pro",
    "gemini-pro": "google-gemini-1.5-pro",
}

# Function types and their constraints
FUNCTION_TYPE_CONSTRAINTS = {
    "PYTHON_STATIC": {
        "cannot_do": ["call MCP servers", "make HTTP requests", "call external APIs", "call LLMs"],
        "pattern_violations": [
            (r"ezMCP", "PYTHON_STATIC cannot call ezMCP - use NUGGET function type"),
            (r"requests\.", "PYTHON_STATIC cannot make HTTP requests - use REST function type"),
            (r"urllib", "PYTHON_STATIC cannot make HTTP requests - use REST function type"),
            (r"httpx", "PYTHON_STATIC cannot make HTTP requests - use REST function type"),
            (r"aiohttp", "PYTHON_STATIC cannot make HTTP requests - use REST function type"),
        ]
    }
}

# Valid retriever strategies
VALID_RETRIEVER_STRATEGIES = ["STANDARD", "REASON", "RAG", "NUGGET", "AVATAR", "HYDE", "BM25"]

# Valid control flags
VALID_CONTROL_FLAGS = [
    "ADD_KNOWLEDGE", "SESSION_DOCUMENTS", "BUILD_GRAPH", "ENCRYPTION",
    "USE_HISTORY", "RE_RANK_CHUNKS", "DESCRIBE_IMAGES", "ENTERPRISE_AGENT",
    "PROMPT_EXPRESSION", "USE_MEMORY"
]

# Valid chunking strategies
VALID_CHUNKING_STRATEGIES = ["TOKEN_SPLIT", "PAGE_SPLIT", "RECURSIVE_CHARACTER_SPLIT", "NUGGET"]

# ez* function signatures (validated)
EZ_FUNCTION_SIGNATURES = {
    "ezLog": {"args": 1, "sig": "ezLog(message)"},
    "ezChatCompletions": {"args": 1, "sig": "ezChatCompletions(jsonString)", "requires_stringify": True},
    "ezInternetSearch": {"args": 1, "sig": "ezInternetSearch(query)"},
    "ezSaveSessionData": {"args": 2, "sig": "ezSaveSessionData(key, value)"},
    "ezGetSessionData": {"args": 1, "sig": "ezGetSessionData(key)"},
    "ezUpdateSessionData": {"args": 2, "sig": "ezUpdateSessionData(key, value)"},
    "ezNugget": {"args": 1, "sig": "ezNugget(jsonString)", "requires_stringify": True},
    "ezMail": {"args": 1, "sig": "ezMail(jsonString)", "requires_stringify": True, "note": "to field must be array"},
    "ezSqlSelect": {"args": 3, "sig": "ezSqlSelect(dataSourceName, label, sql)"},
    "ezNexenApi": {"args": 7, "sig": "ezNexenApi(secretsPath, env, url, method, body, params, headers)"},
    "ezA2A": {"args": 5, "sig": "ezA2A(serverId, message, secretsPath, contextId, tasks)"},
    "ezMCP": {"args": "variable", "sig": "ezMCP(serverId, toolName, params, ...)"},
    "ezChat": {"args": 1, "sig": "ezChat(jsonString)", "requires_stringify": True},
    "ezEmbeddings": {"args": 1, "sig": "ezEmbeddings(jsonString)", "requires_stringify": True},
    "ezToken": {"args": 1, "sig": "ezToken(secretsPath)"},
    "ezSecret": {"args": 1, "sig": "ezSecret(secretsPath)"},
    "ezCanvas": {"args": 1, "sig": "ezCanvas(json)"},
    "ezConfirm": {"args": 1, "sig": "ezConfirm(message)"},
    "ezNotify": {"args": 1, "sig": "ezNotify(message)"},
    "ezBrowser": {"args": 1, "sig": "ezBrowser(timeout)"},
    "ezImageToText": {"args": 1, "sig": "ezImageToText(jsonString)", "requires_stringify": True},
    "ezTextToImage": {"args": 1, "sig": "ezTextToImage(jsonString)", "requires_stringify": True},
    "ezPython": {"args": 1, "sig": "ezPython(code)", "note": "May not work in QA"},
    "ezJavaScript": {"args": 1, "sig": "ezJavaScript(code)"},
    "ezUser": {"args": 0, "sig": "ezUser()"},
    "sleep": {"args": 1, "sig": "sleep(ms)"},
}

# Functions NOT available in sandbox
UNAVAILABLE_FUNCTIONS = {
    "ezQuery": "Use ezChat or AGENT function type instead",
    "ezSendEmail": "Use ezMail with secrets configured instead",
}


# ============================================================================
# PYTHON CODE VALIDATOR
# ============================================================================

class PythonValidator:
    """Validates Python code for Eliza agents, functions, documents."""

    def __init__(self, code: str):
        self.code = code
        self.issues: List[ValidationIssue] = []
        self.tree: Optional[ast.AST] = None

    def parse(self) -> bool:
        """Parse the Python code into AST."""
        try:
            self.tree = ast.parse(self.code)
            return True
        except SyntaxError as e:
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                message=f"Python syntax error: {e.msg}",
                line=e.lineno,
                fix="Fix the syntax error"
            ))
            return False

    def validate(self) -> ValidationResult:
        """Run all validations."""
        if not self.parse():
            return ValidationResult(valid=False, issues=self.issues)

        self._check_imports()
        self._check_session_setup()
        self._check_model_names()
        self._check_field_names()
        self._check_retriever_strategy()
        self._check_control_flags()
        self._check_function_type_constraints()
        self._check_api_patterns()

        # Determine if valid (no errors)
        has_errors = any(i.severity == Severity.ERROR for i in self.issues)

        # Try to auto-fix
        fixed_code = self._apply_auto_fixes() if self.issues else None

        return ValidationResult(
            valid=not has_errors,
            issues=self.issues,
            fixed_code=fixed_code,
            code_type=self._detect_code_type()
        )

    def _detect_code_type(self) -> str:
        """Detect what type of Eliza code this is."""
        if "Agent(" in self.code:
            if "add_function" in self.code:
                return "agent_with_function"
            if "upload_" in self.code:
                return "agent_with_document"
            return "agent"
        if "funcNameKey" in self.code or "functionType" in self.code:
            return "function"
        if "upload_data_to_agent" in self.code or "upload_file_to_agent" in self.code:
            return "document"
        if "ChatCompletion" in self.code:
            return "llm_call"
        return "unknown"

    def _check_imports(self):
        """Check for correct imports."""
        # Check for wrong package names
        wrong_imports = [
            ("import eliza", "import bnym_eliza as eliza"),
            ("from eliza ", "from bnym_eliza "),
            ("import openai", "Use bnym_eliza, not openai directly"),
        ]

        for wrong, fix in wrong_imports:
            if wrong in self.code:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"Wrong import: '{wrong}'",
                    fix=fix,
                    auto_fixable=True
                ))

        # Check for required imports
        if "Agent(" in self.code and "from bnym_eliza.genai.agent import Agent" not in self.code:
            if "from bnym_eliza" not in self.code or "Agent" not in self.code:
                self.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    message="Missing Agent import",
                    fix="Add: from bnym_eliza.genai.agent import Agent"
                ))

    def _check_session_setup(self):
        """Check for proper session setup."""
        if "Agent(" in self.code or "ChatCompletion" in self.code:
            if "Session.connect" not in self.code and "eliza.session" not in self.code:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message="Missing session setup - eliza.session = eliza.Session.connect() is required",
                    fix="Add session setup before Agent creation"
                ))

            # Check for initiative_id
            if "Session.connect" in self.code and "initiative_id" not in self.code:
                self.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    message="Missing initiative_id in Session.connect() - defaults to ELZ-00000 which often fails",
                    fix="Add initiative_id='ELZI-{your_userid}' to Session.connect()"
                ))

    def _check_model_names(self):
        """Check for correct model name prefixes."""
        # Find all string literals that look like model names
        model_patterns = [
            r"llm_model\s*=\s*['\"]([^'\"]+)['\"]",
            r"model\s*=\s*['\"]([^'\"]+)['\"]",
            r"['\"]model['\"]\s*:\s*['\"]([^'\"]+)['\"]",
        ]

        for pattern in model_patterns:
            matches = re.findall(pattern, self.code)
            for model in matches:
                # Skip if it's a variable reference
                if model.startswith("$") or model.startswith("{"):
                    continue

                # Check if it has a valid prefix
                has_valid_prefix = any(model.startswith(p) for p in VALID_MODEL_PREFIXES)

                if not has_valid_prefix:
                    # Check if it's a known wrong model
                    if model in COMMON_WRONG_MODELS:
                        self.issues.append(ValidationIssue(
                            severity=Severity.ERROR,
                            message=f"Invalid model name '{model}' - missing prefix",
                            fix=f"Use '{COMMON_WRONG_MODELS[model]}' instead",
                            auto_fixable=True
                        ))
                    else:
                        self.issues.append(ValidationIssue(
                            severity=Severity.WARNING,
                            message=f"Model '{model}' may be missing prefix (openai-, bnym-, google-)",
                            fix="Add appropriate prefix"
                        ))

    def _check_field_names(self):
        """Check for wrong field names in function definitions."""
        # Check function field names
        for wrong, (correct, message) in FUNCTION_FIELD_MAPPINGS.items():
            # Look for wrong field in dict context
            pattern = rf'["\']({wrong})["\']s*:'
            if re.search(pattern, self.code):
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=message,
                    fix=f"Replace '{wrong}' with '{correct}'",
                    auto_fixable=True
                ))

        # Check agent field names
        for wrong, (correct, message) in AGENT_FIELD_MAPPINGS.items():
            if wrong in self.code:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=message,
                    fix=f"Replace '{wrong}' with '{correct}'",
                    auto_fixable=True
                ))

    def _check_retriever_strategy(self):
        """Check retriever strategy values."""
        pattern = r"retriever_strategy\s*=\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, self.code)

        for strategy in matches:
            if strategy not in VALID_RETRIEVER_STRATEGIES:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"Invalid retriever_strategy '{strategy}'",
                    fix=f"Use one of: {', '.join(VALID_RETRIEVER_STRATEGIES)}"
                ))

            # Check if REASON strategy with function
            if strategy == "REASON" and "add_function" in self.code:
                # Check if using compatible model
                if "bnym-llama" in self.code or "bnym-mistral" in self.code:
                    self.issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        message="REASON strategy with bnym-llama may not support function calling",
                        fix="Consider using openai-gpt-4.1-mini-ptu for REASON strategy"
                    ))

    def _check_control_flags(self):
        """Check control flag values."""
        pattern = r"control_flags\s*=\s*\[([^\]]+)\]"
        matches = re.findall(pattern, self.code)

        for flags_str in matches:
            # Extract individual flags
            flags = re.findall(r"['\"]([^'\"]+)['\"]", flags_str)
            for flag in flags:
                if flag not in VALID_CONTROL_FLAGS:
                    self.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=f"Invalid control flag '{flag}'",
                        fix=f"Use one of: {', '.join(VALID_CONTROL_FLAGS)}"
                    ))

    def _check_function_type_constraints(self):
        """Check that function types aren't used for things they can't do."""
        if "'PYTHON_STATIC'" in self.code or '"PYTHON_STATIC"' in self.code:
            constraints = FUNCTION_TYPE_CONSTRAINTS["PYTHON_STATIC"]

            for pattern, message in constraints["pattern_violations"]:
                if re.search(pattern, self.code):
                    self.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=message,
                        fix="Use NUGGET function type with appropriate ez* function, or REST for HTTP calls"
                    ))

    def _check_api_patterns(self):
        """Check for common API pattern mistakes."""
        # Check for wrong pagination
        if "pageNumber" in self.code or "pageSize" in self.code:
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                message="Use 'offset'/'limit' not 'pageNumber'/'pageSize' for pagination",
                fix="Replace pageNumber with offset, pageSize with limit",
                auto_fixable=True
            ))

        # Check for wrong search content format
        if "search_documents" in self.code:
            # Check if content is a string instead of list
            pattern = r"content\s*=\s*['\"]"
            if re.search(pattern, self.code):
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message="search_documents content must be a list, not a string",
                    fix="Use content=['query'] not content='query'"
                ))

        # Check for wrong SDK patterns that don't exist
        self._check_wrong_sdk_patterns()

    def _check_wrong_sdk_patterns(self):
        """Check for SDK methods/patterns that don't exist."""
        for pattern, message, fix in WRONG_SDK_PATTERNS:
            if re.search(pattern, self.code):
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=message,
                    fix=fix
                ))

    def _apply_auto_fixes(self) -> Optional[str]:
        """Apply auto-fixes where possible."""
        fixed = self.code

        # Fix imports
        fixed = fixed.replace("import eliza\n", "import bnym_eliza as eliza\n")
        fixed = re.sub(r"from eliza ([^i])", r"from bnym_eliza \1", fixed)

        # Fix model names
        for wrong, correct in COMMON_WRONG_MODELS.items():
            fixed = re.sub(rf"(['\"]){wrong}(['\"])", rf"\1{correct}\2", fixed)

        # Fix field names
        for wrong, (correct, _) in FUNCTION_FIELD_MAPPINGS.items():
            fixed = re.sub(rf"(['\"]){wrong}(['\"])", rf"\1{correct}\2", fixed)

        # Fix pagination
        fixed = fixed.replace("pageNumber", "offset")
        fixed = fixed.replace("pageSize", "limit")

        return fixed if fixed != self.code else None


# ============================================================================
# JAVASCRIPT/NUGGET VALIDATOR
# ============================================================================

class NuggetValidator:
    """Validates JavaScript nugget code for Eliza."""

    def __init__(self, code: str):
        self.code = code
        self.issues: List[ValidationIssue] = []

    def validate(self) -> ValidationResult:
        """Run all validations."""
        self._check_structure()
        self._check_ez_functions()
        self._check_json_stringify()
        self._check_unavailable_functions()
        self._check_common_mistakes()
        self._check_syntax_patterns()

        has_errors = any(i.severity == Severity.ERROR for i in self.issues)

        return ValidationResult(
            valid=not has_errors,
            issues=self.issues,
            fixed_code=self._apply_auto_fixes() if self.issues else None,
            code_type="nugget"
        )

    def _check_structure(self):
        """Check basic nugget structure."""
        # Check for IIFE pattern
        if not re.search(r"\(function\s*\(", self.code):
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                message="Nugget must be an IIFE: (function(data) { ... })",
                fix="Wrap code in (function(data) { return ...; })"
            ))

        # Check for data parameter
        if "(function())" in self.code or "(function ()" in self.code:
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                message="Nugget function should accept 'data' parameter",
                fix="Use (function(data) { ... }) to receive input"
            ))

        # Check for return statement
        if "return" not in self.code:
            self.issues.append(ValidationIssue(
                severity=Severity.WARNING,
                message="Nugget should return a value",
                fix="Add a return statement"
            ))

    def _check_ez_functions(self):
        """Check ez* function usage."""
        # Find all ez* function calls
        ez_calls = re.findall(r"(ez\w+)\s*\(", self.code)

        for func_name in ez_calls:
            if func_name in UNAVAILABLE_FUNCTIONS:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"'{func_name}' is NOT available in nugget sandbox",
                    fix=UNAVAILABLE_FUNCTIONS[func_name]
                ))
            elif func_name in EZ_FUNCTION_SIGNATURES:
                sig_info = EZ_FUNCTION_SIGNATURES[func_name]
                # Check argument count if we can parse it
                self._check_function_args(func_name, sig_info)
            else:
                self.issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    message=f"Unknown ez* function '{func_name}' - verify it exists",
                    fix="Check NUGGET_REFERENCE.md for valid functions"
                ))

    def _check_function_args(self, func_name: str, sig_info: Dict):
        """Check if function is called with correct number of arguments."""
        expected_args = sig_info.get("args")
        if expected_args == "variable":
            return  # Can't validate variable args

        # Try to find the function call and count args
        # This is a simple heuristic, not perfect
        pattern = rf"{func_name}\s*\(([^)]*)\)"
        matches = re.findall(pattern, self.code)

        for args_str in matches:
            if not args_str.strip():
                actual_args = 0
            else:
                # Count commas (rough estimate)
                # This doesn't handle nested calls perfectly
                actual_args = args_str.count(",") + 1

            if expected_args != actual_args and expected_args != 0:
                # Allow some flexibility for complex expressions
                if abs(expected_args - actual_args) > 1:
                    self.issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        message=f"'{func_name}' expects {expected_args} args, got ~{actual_args}",
                        fix=f"Signature: {sig_info['sig']}"
                    ))

    def _check_json_stringify(self):
        """Check that functions requiring JSON.stringify are using it."""
        for func_name, sig_info in EZ_FUNCTION_SIGNATURES.items():
            if sig_info.get("requires_stringify"):
                # Check if function is called
                if func_name in self.code:
                    # Check if JSON.stringify is used
                    pattern = rf"{func_name}\s*\(\s*JSON\.stringify"
                    if not re.search(pattern, self.code):
                        # Check if it's already a string variable
                        pattern2 = rf"{func_name}\s*\(\s*['\"]"
                        pattern3 = rf"{func_name}\s*\(\s*\w+\s*\)"  # variable
                        if not re.search(pattern2, self.code) and not re.search(pattern3, self.code):
                            self.issues.append(ValidationIssue(
                                severity=Severity.WARNING,
                                message=f"'{func_name}' typically requires JSON.stringify() for object input",
                                fix=f"Use {func_name}(JSON.stringify(obj))"
                            ))

    def _check_unavailable_functions(self):
        """Check for functions that don't exist in sandbox."""
        for func_name, alternative in UNAVAILABLE_FUNCTIONS.items():
            if func_name in self.code:
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"'{func_name}' is NOT available in nugget sandbox",
                    fix=alternative
                ))

    def _check_common_mistakes(self):
        """Check for common nugget mistakes."""
        # ezMail to field must be array
        if "ezMail" in self.code:
            # Check if "to" is a string instead of array
            pattern = r'"to"\s*:\s*"[^"]*@'  # "to": "email@..."
            if re.search(pattern, self.code):
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message="ezMail 'to' field must be an array, not a string",
                    fix='Use "to": ["email@example.com"] not "to": "email@example.com"'
                ))

        # Model names in ezChatCompletions
        if "ezChatCompletions" in self.code:
            for wrong, correct in COMMON_WRONG_MODELS.items():
                if f'"{wrong}"' in self.code or f"'{wrong}'" in self.code:
                    self.issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=f"Invalid model name '{wrong}' in ezChatCompletions",
                        fix=f"Use '{correct}' instead",
                        auto_fixable=True
                    ))

    def _check_syntax_patterns(self):
        """Check for JavaScript syntax issues."""
        # Check for unclosed brackets (simple check)
        open_parens = self.code.count("(")
        close_parens = self.code.count(")")
        if open_parens != close_parens:
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                message=f"Mismatched parentheses: {open_parens} '(' vs {close_parens} ')'",
                fix="Check for unclosed parentheses"
            ))

        open_braces = self.code.count("{")
        close_braces = self.code.count("}")
        if open_braces != close_braces:
            self.issues.append(ValidationIssue(
                severity=Severity.ERROR,
                message=f"Mismatched braces: {open_braces} '{{' vs {close_braces} '}}'",
                fix="Check for unclosed braces"
            ))

        # Check for common typos
        typos = [
            ("fucntion", "function"),
            ("retrun", "return"),
            ("varible", "variable"),
            ("funtion", "function"),
        ]
        for typo, correct in typos:
            if typo in self.code.lower():
                self.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"Typo: '{typo}' should be '{correct}'",
                    fix=f"Replace with '{correct}'",
                    auto_fixable=True
                ))

    def _apply_auto_fixes(self) -> Optional[str]:
        """Apply auto-fixes where possible."""
        fixed = self.code

        # Fix model names
        for wrong, correct in COMMON_WRONG_MODELS.items():
            fixed = re.sub(rf"(['\"]){wrong}(['\"])", rf"\1{correct}\2", fixed)

        # Fix common typos
        typos = [("fucntion", "function"), ("retrun", "return"), ("funtion", "function")]
        for typo, correct in typos:
            fixed = re.sub(typo, correct, fixed, flags=re.IGNORECASE)

        return fixed if fixed != self.code else None


# ============================================================================
# MAIN VALIDATION FUNCTION
# ============================================================================

def validate_code(code: str, code_type: Optional[str] = None) -> ValidationResult:
    """
    Validate Eliza code.

    Args:
        code: The code to validate
        code_type: Optional hint about code type ('python', 'nugget', 'agent', etc.)
                   If not provided, will auto-detect

    Returns:
        ValidationResult with issues and optional fixed code
    """
    # Auto-detect code type if not provided
    if code_type is None:
        code_type = _detect_code_type(code)

    if code_type in ["nugget", "javascript", "js"]:
        validator = NuggetValidator(code)
    else:
        validator = PythonValidator(code)

    return validator.validate()


def _detect_code_type(code: str) -> str:
    """Auto-detect whether code is Python or JavaScript nugget."""
    # Nugget indicators
    nugget_indicators = [
        "(function(data)",
        "(function (data)",
        "ezLog(",
        "ezChatCompletions(",
        "ezInternetSearch(",
        "ezNugget(",
    ]

    for indicator in nugget_indicators:
        if indicator in code:
            return "nugget"

    # Python indicators
    python_indicators = [
        "import bnym_eliza",
        "from bnym_eliza",
        "Agent(",
        "def ",
        "Session.connect",
    ]

    for indicator in python_indicators:
        if indicator in code:
            return "python"

    # Default to Python
    return "python"


def validate_and_report(code: str, code_type: Optional[str] = None) -> str:
    """
    Validate code and return a formatted report.

    Args:
        code: The code to validate
        code_type: Optional hint about code type

    Returns:
        Formatted validation report string
    """
    result = validate_code(code, code_type)

    report = []

    if result.valid:
        report.append("✅ **STATIC VALIDATION PASSED**\n")
    else:
        report.append("❌ **STATIC VALIDATION FAILED**\n")

    report.append(f"**Code Type**: {result.code_type}\n")

    if result.issues:
        report.append(f"**Issues Found**: {len(result.issues)}\n")

        # Group by severity
        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        warnings = [i for i in result.issues if i.severity == Severity.WARNING]
        infos = [i for i in result.issues if i.severity == Severity.INFO]

        if errors:
            report.append("\n### ❌ Errors (must fix)")
            for issue in errors:
                line_info = f" (line {issue.line})" if issue.line else ""
                report.append(f"- {issue.message}{line_info}")
                if issue.fix:
                    report.append(f"  - **Fix**: {issue.fix}")

        if warnings:
            report.append("\n### ⚠ Warnings (should fix)")
            for issue in warnings:
                line_info = f" (line {issue.line})" if issue.line else ""
                report.append(f"- {issue.message}{line_info}")
                if issue.fix:
                    report.append(f"  - **Fix**: {issue.fix}")

        if infos:
            report.append("\n### ℹ Info")
            for issue in infos:
                report.append(f"- {issue.message}")
    else:
        report.append("**Issues Found**: 0\n")

    if result.fixed_code:
        report.append("\n### 🔧 Auto-Fixed Code Available")
        report.append("Some issues were automatically fixed. Review the corrected code below.")

    return "\n".join(report)


# ============================================================================
# CLI TESTING
# ============================================================================

if __name__ == "__main__":
    # Test Python validation
    test_python = '''
import eliza
from eliza.genai.agent import Agent

agent = Agent(
    env='QA',
    agentName='Test Agent',
    llm_model='gpt-4',
    retriever_strategy='STANDARD'
)
agent.create()

function_def = {
    "name": "my_function",
    "description": "My function",
    "functionType": "PYTHON_STATIC",
    "code": "import requests; requests.get('http://example.com')"
}
agent.add_function(function_def)
'''

    print("=" * 60)
    print("PYTHON VALIDATION TEST")
    print("=" * 60)
    print(validate_and_report(test_python))

    # Test Nugget validation
    test_nugget = '''
(function(data) {
    var result = ezQuery("agent-id", data.query);
    var chat = ezChatCompletions({
        "model": "gpt-4",
        "messages": [{"role": "user", "content": data.query}]
    });
    ezMail(JSON.stringify({
        "to": "user@example.com",
        "subject": "Test"
    }));
    return result;
})
'''

    print("\n" + "=" * 60)
    print("NUGGET VALIDATION TEST")
    print("=" * 60)
    print(validate_and_report(test_nugget))