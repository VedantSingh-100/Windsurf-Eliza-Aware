"""
Static Code Validation

Validates Python and JavaScript (nugget) code for Eliza without executing it.
Catches common errors before runtime.

This is the SINGLE SOURCE OF TRUTH for validation.
Uses search/index.py for ez* function signatures.
"""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

# Import the authoritative ez* function index
try:
    from search.index import EZ_FUNCTION_INDEX
except ImportError:
    EZ_FUNCTION_INDEX = {}


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


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
    code_type: Optional[str] = None


# ============================================================================
# VALIDATION RULES
# ============================================================================

FUNCTION_FIELD_MAPPINGS = {
    "name": ("funcNameKey", "Use 'funcNameKey' not 'name' for function identifier"),
    "description": ("label", "Use 'label' not 'description' for function display name"),
    "parameters": ("params", "Use 'params' not 'parameters' for function parameters"),
}

AGENT_FIELD_MAPPINGS = {
    "agentName": ("agent_name", "SDK uses 'agent_name' not 'agentName'"),
    "agentDescription": ("agent_description", "SDK uses 'agent_description' not 'agentDescription'"),
}

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
}

FUNCTION_TYPE_CONSTRAINTS = {
    "PYTHON_STATIC": {
        "pattern_violations": [
            (r"ezMCP", "PYTHON_STATIC cannot call ezMCP - use NUGGET function type"),
            (r"requests\.", "PYTHON_STATIC cannot make HTTP requests - use REST function type"),
            (r"urllib", "PYTHON_STATIC cannot make HTTP requests - use REST function type"),
        ]
    }
}

VALID_RETRIEVER_STRATEGIES = ["STANDARD", "REASON", "RAG", "NUGGET", "AVATAR", "HYDE", "BM25"]

VALID_CONTROL_FLAGS = [
    "ADD_KNOWLEDGE", "SESSION_DOCUMENTS", "BUILD_GRAPH", "ENCRYPTION",
    "USE_HISTORY", "RE_RANK_CHUNKS", "DESCRIBE_IMAGES", "ENTERPRISE_AGENT",
    "PROMPT_EXPRESSION", "USE_MEMORY"
]

# Functions NOT available in nugget sandbox
UNAVAILABLE_EZ_FUNCTIONS = {
    "ezQuery": "Use ezChat or AGENT function type instead",
    "ezSendEmail": "Use ezMail with secrets configured instead",
}

# Functions that require JSON.stringify for object input
REQUIRES_STRINGIFY = [
    "ezChatCompletions", "ezNugget", "ezMail", "ezChat", "ezEmbeddings",
    "ezImageToText", "ezTextToImage", "ezCopilotChat", "ezCopilotQuery",
    "ezSharePoint", "ezJiraSupport", "ezDataSearch", "ezDataCreate",
    "ezDataQuery", "ezExperiments", "ezPrompt", "ezPromptGroup",
    "ezSecret2", "ezTextToVideo", "ezVaApiStream", "ezSharedItems"
]


class PythonValidator:
    """Validates Python code for Eliza SDK usage."""

    def __init__(self, code: str):
        self.code = code
        self.issues: List[ValidationIssue] = []
        self.tree = None

    def parse(self) -> bool:
        try:
            self.tree = ast.parse(self.code)
            return True
        except SyntaxError as e:
            self.issues.append(ValidationIssue(
                Severity.ERROR,
                f"Python syntax error: {e.msg}",
                e.lineno,
                "Fix the syntax error"
            ))
            return False

    def validate(self) -> ValidationResult:
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

        has_errors = any(i.severity == Severity.ERROR for i in self.issues)
        fixed_code = self._apply_auto_fixes() if self.issues else None

        return ValidationResult(
            valid=not has_errors,
            issues=self.issues,
            fixed_code=fixed_code,
            code_type=self._detect_code_type()
        )

    def _detect_code_type(self) -> str:
        if "Agent(" in self.code:
            if "add_function" in self.code:
                return "agent_with_function"
            if "upload_" in self.code:
                return "agent_with_document"
            return "agent"
        if "funcNameKey" in self.code:
            return "function"
        if "upload_data_to_agent" in self.code:
            return "document"
        if "ChatCompletion" in self.code:
            return "llm_call"
        return "unknown"

    def _check_imports(self):
        if "import eliza" in self.code and "bnym_eliza" not in self.code:
            self.issues.append(ValidationIssue(
                Severity.ERROR,
                "Wrong import: 'import eliza'",
                fix="import bnym_eliza as eliza",
                auto_fixable=True
            ))
        if "from eliza " in self.code and "bnym_eliza" not in self.code:
            self.issues.append(ValidationIssue(
                Severity.ERROR,
                "Wrong import: 'from eliza'",
                fix="from bnym_eliza",
                auto_fixable=True
            ))

    def _check_session_setup(self):
        if "Agent(" in self.code or "ChatCompletion" in self.code:
            if "Session.connect" not in self.code and "eliza.session" not in self.code:
                self.issues.append(ValidationIssue(
                    Severity.ERROR,
                    "Missing session setup - eliza.session = eliza.Session.connect() is required"
                ))
            if "Session.connect" in self.code and "initiative_id" not in self.code:
                self.issues.append(ValidationIssue(
                    Severity.WARNING,
                    "Missing initiative_id in Session.connect()",
                    fix="Add initiative_id='ELZI-{your_userid}'"
                ))

    def _check_model_names(self):
        patterns = [
            r"llm_model\s*=\s*['\"]([^'\"]+)['\"]",
            r"['\"]model['\"]\s*:\s*['\"]([^'\"]+)['\"]"
        ]
        for pattern in patterns:
            for model in re.findall(pattern, self.code):
                if not any(model.startswith(p) for p in VALID_MODEL_PREFIXES):
                    if model in COMMON_WRONG_MODELS:
                        self.issues.append(ValidationIssue(
                            Severity.ERROR,
                            f"Invalid model name '{model}'",
                            fix=f"Use '{COMMON_WRONG_MODELS[model]}'",
                            auto_fixable=True
                        ))

    def _check_field_names(self):
        for wrong, (correct, msg) in FUNCTION_FIELD_MAPPINGS.items():
            if re.search(rf'["\']({wrong})["\']s*:', self.code):
                self.issues.append(ValidationIssue(
                    Severity.ERROR,
                    msg,
                    fix=f"Replace '{wrong}' with '{correct}'",
                    auto_fixable=True
                ))
        for wrong, (correct, msg) in AGENT_FIELD_MAPPINGS.items():
            if wrong in self.code:
                self.issues.append(ValidationIssue(
                    Severity.ERROR,
                    msg,
                    fix=f"Replace '{wrong}' with '{correct}'",
                    auto_fixable=True
                ))

    def _check_retriever_strategy(self):
        for strategy in re.findall(r"retriever_strategy\s*=\s*['\"]([^'\"]+)['\"]", self.code):
            if strategy not in VALID_RETRIEVER_STRATEGIES:
                self.issues.append(ValidationIssue(
                    Severity.ERROR,
                    f"Invalid retriever_strategy '{strategy}'"
                ))

    def _check_control_flags(self):
        for flags_str in re.findall(r"control_flags\s*=\s*\[([^\]]+)\]", self.code):
            for flag in re.findall(r"['\"]([^'\"]+)['\"]", flags_str):
                if flag not in VALID_CONTROL_FLAGS:
                    self.issues.append(ValidationIssue(
                        Severity.ERROR,
                        f"Invalid control flag '{flag}'"
                    ))

    def _check_function_type_constraints(self):
        if "'PYTHON_STATIC'" in self.code or '"PYTHON_STATIC"' in self.code:
            for pattern, msg in FUNCTION_TYPE_CONSTRAINTS["PYTHON_STATIC"]["pattern_violations"]:
                if re.search(pattern, self.code):
                    self.issues.append(ValidationIssue(Severity.ERROR, msg))

    def _check_api_patterns(self):
        if "pageNumber" in self.code or "pageSize" in self.code:
            self.issues.append(ValidationIssue(
                Severity.ERROR,
                "Use 'offset'/'limit' not 'pageNumber'/'pageSize'",
                auto_fixable=True
            ))

    def _apply_auto_fixes(self) -> Optional[str]:
        fixed = self.code
        fixed = fixed.replace("import eliza\n", "import bnym_eliza as eliza\n")
        fixed = re.sub(r"from eliza ([^i])", r"from bnym_eliza \1", fixed)
        for wrong, correct in COMMON_WRONG_MODELS.items():
            fixed = re.sub(rf"(['\"]){wrong}(['\"])", rf"\1{correct}\2", fixed)
        for wrong, (correct, _) in FUNCTION_FIELD_MAPPINGS.items():
            fixed = re.sub(rf"(['\"]){wrong}(['\"])", rf"\1{correct}\2", fixed)
        fixed = fixed.replace("pageNumber", "offset").replace("pageSize", "limit")
        return fixed if fixed != self.code else None


def parse_expected_arg_count(signature: str) -> int:
    """
    Parse expected argument count from a function signature.

    Examples:
        "ezLog(message)" → 1
        "ezSaveSessionData(key, value)" → 2
        "ezMail(jsonString)" → 1
    """
    match = re.search(r'\(([^)]*)\)', signature)
    if not match:
        return 0
    args_str = match.group(1).strip()
    if not args_str:
        return 0
    # Count commas + 1 (simple approach for signatures)
    return len([a.strip() for a in args_str.split(',') if a.strip()])


def count_actual_arguments(code: str, func_name: str) -> List[int]:
    """
    Count actual arguments passed to a function in code.

    Handles:
    - Nested parentheses: ezMail(JSON.stringify({...}))
    - Strings with commas: ezLog("Hello, World")
    - Multiple calls of same function

    Returns list of argument counts for each call found.
    """
    counts = []

    # Find all occurrences of the function call
    pattern = rf'{func_name}\s*\('
    for match in re.finditer(pattern, code):
        start = match.end()
        # Find matching closing paren
        depth = 1
        pos = start
        in_string = False
        string_char = None

        while pos < len(code) and depth > 0:
            char = code[pos]

            # Handle string literals
            if char in '"\'`' and (pos == 0 or code[pos - 1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None

            if not in_string:
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1

            pos += 1

        if depth == 0:
            # Extract the arguments string
            args_str = code[start:pos - 1].strip()
            if not args_str:
                counts.append(0)
            else:
                # Count arguments by tracking commas at depth 0
                arg_count = 1
                depth = 0
                in_str = False
                str_char = None

                for i, c in enumerate(args_str):
                    if c in '"\'`' and (i == 0 or args_str[i - 1] != '\\'):
                        if not in_str:
                            in_str = True
                            str_char = c
                        elif c == str_char:
                            in_str = False

                    if not in_str:
                        if c in '([{':
                            depth += 1
                        elif c in ')]}':
                            depth -= 1
                        elif c == ',' and depth == 0:
                            arg_count += 1

                counts.append(arg_count)

    return counts


class NuggetValidator:
    """
    Validates JavaScript nugget code for Eliza.

    Comprehensive validation including:
    - IIFE structure check
    - ez* function availability and signatures
    - JSON.stringify requirements
    - Model name validation
    - Syntax pattern checks
    - Argument count validation (catches hallucinated signatures)
    """

    def __init__(self, code: str):
        self.code = code
        self.issues: List[ValidationIssue] = []

    def validate(self) -> ValidationResult:
        """Run all validations."""
        self._check_structure()
        self._check_ez_functions()
        self._check_json_stringify()
        self._check_common_mistakes()
        self._check_syntax_patterns()

        has_errors = any(i.severity == Severity.ERROR for i in self.issues)
        fixed_code = self._apply_auto_fixes() if self.issues else None

        return ValidationResult(
            valid=not has_errors,
            issues=self.issues,
            fixed_code=fixed_code,
            code_type="nugget"
        )

    def _check_structure(self):
        """Check basic nugget structure."""
        # Check for IIFE pattern
        if not re.search(r"\(function\s*\(", self.code):
            self.issues.append(ValidationIssue(
                Severity.ERROR,
                "Nugget must be an IIFE: (function(data) { ... })",
                fix="Wrap code in (function(data) { return ...; })"
            ))

        # Check for data parameter
        if "(function())" in self.code or "(function ()" in self.code:
            self.issues.append(ValidationIssue(
                Severity.WARNING,
                "Nugget function should accept 'data' parameter",
                fix="Use (function(data) { ... }) to receive input"
            ))

        # Check for return statement
        if "return" not in self.code:
            self.issues.append(ValidationIssue(
                Severity.WARNING,
                "Nugget should return a value",
                fix="Add a return statement"
            ))

    def _check_ez_functions(self):
        """Check ez* function usage against authoritative index."""
        # Find all ez* function calls
        ez_calls = re.findall(r"(ez\w+)\s*\(", self.code)
        checked_funcs = set()  # Track which functions we've checked for arg count

        for func_name in ez_calls:
            # Check if unavailable
            if func_name in UNAVAILABLE_EZ_FUNCTIONS:
                self.issues.append(ValidationIssue(
                    Severity.ERROR,
                    f"'{func_name}' is NOT available in nugget sandbox",
                    fix=UNAVAILABLE_EZ_FUNCTIONS[func_name]
                ))
            # Check against authoritative index
            elif EZ_FUNCTION_INDEX and func_name in EZ_FUNCTION_INDEX:
                func_info = EZ_FUNCTION_INDEX[func_name]
                # Check if function is marked as not available
                if func_info.get("status") == "NOT_AVAILABLE":
                    self.issues.append(ValidationIssue(
                        Severity.ERROR,
                        f"'{func_name}' is NOT available",
                        fix=func_info.get("note", "Use alternative function")
                    ))
                # Warn if function needs configuration
                elif func_info.get("status") == "NEEDS_CONFIG":
                    self.issues.append(ValidationIssue(
                        Severity.WARNING,
                        f"'{func_name}' requires configuration: {func_info.get('note', 'See docs')}",
                        fix=f"Signature: {func_info.get('signature', 'unknown')}"
                    ))
                # Warn if function is limited in QA
                elif func_info.get("status") == "QA_LIMITED":
                    self.issues.append(ValidationIssue(
                        Severity.WARNING,
                        f"'{func_name}' has limited availability in QA: {func_info.get('note', '')}",
                        fix="Function may not work in all environments"
                    ))

                # NEW: Check argument count (only once per function)
                if func_name not in checked_funcs:
                    checked_funcs.add(func_name)
                    signature = func_info.get("signature", "")
                    if signature:
                        expected_args = parse_expected_arg_count(signature)
                        actual_counts = count_actual_arguments(self.code, func_name)

                        for actual_args in actual_counts:
                            if actual_args != expected_args:
                                self.issues.append(ValidationIssue(
                                    Severity.ERROR,
                                    f"'{func_name}' expects {expected_args} argument(s), got {actual_args}",
                                    fix=f"Correct signature: {signature}"
                                ))

            # Unknown function
            elif func_name not in ["ezLog", "ezUserLog"]:  # Common utility functions
                if not EZ_FUNCTION_INDEX or func_name not in EZ_FUNCTION_INDEX:
                    self.issues.append(ValidationIssue(
                        Severity.WARNING,
                        f"Unknown ez* function '{func_name}' - verify it exists",
                        fix="Check EZ_FUNCTION_INDEX for valid functions"
                    ))

    def _check_json_stringify(self):
        """Check that functions requiring JSON.stringify are using it."""
        for func_name in REQUIRES_STRINGIFY:
            if func_name in self.code:
                # Check if JSON.stringify is used with this function
                pattern_stringify = rf"{func_name}\s*\(\s*JSON\.stringify"
                pattern_variable = rf"{func_name}\s*\(\s*\w+\s*\)"  # Variable reference
                pattern_string = rf"{func_name}\s*\(\s*['\"]"  # String literal

                if not (re.search(pattern_stringify, self.code) or
                        re.search(pattern_variable, self.code) or
                        re.search(pattern_string, self.code)):
                    # Check if passing an object literal directly
                    pattern_object = rf"{func_name}\s*\(\s*\{{"
                    if re.search(pattern_object, self.code):
                        self.issues.append(ValidationIssue(
                            Severity.ERROR,
                            f"'{func_name}' requires JSON.stringify() for object input",
                            fix=f"Use {func_name}(JSON.stringify({{...}}))",
                            auto_fixable=False
                        ))

    def _check_common_mistakes(self):
        """Check for common nugget mistakes."""
        # ezMail 'to' field must be array
        if "ezMail" in self.code:
            pattern = r'"to"\s*:\s*"[^"]*@'  # "to": "email@..."
            if re.search(pattern, self.code):
                self.issues.append(ValidationIssue(
                    Severity.ERROR,
                    "ezMail 'to' field must be an array, not a string",
                    fix='Use "to": ["email@example.com"] not "to": "email@example.com"'
                ))

        # Model names in ezChatCompletions
        if "ezChatCompletions" in self.code:
            for wrong, correct in COMMON_WRONG_MODELS.items():
                if f'"{wrong}"' in self.code or f"'{wrong}'" in self.code:
                    self.issues.append(ValidationIssue(
                        Severity.ERROR,
                        f"Invalid model name '{wrong}' in ezChatCompletions",
                        fix=f"Use '{correct}' instead",
                        auto_fixable=True
                    ))

    def _check_syntax_patterns(self):
        """Check for JavaScript syntax issues."""
        # Check for mismatched brackets
        open_parens = self.code.count("(")
        close_parens = self.code.count(")")
        if open_parens != close_parens:
            self.issues.append(ValidationIssue(
                Severity.ERROR,
                f"Mismatched parentheses: {open_parens} '(' vs {close_parens} ')'",
                fix="Check for unclosed parentheses"
            ))

        open_braces = self.code.count("{")
        close_braces = self.code.count("}")
        if open_braces != close_braces:
            self.issues.append(ValidationIssue(
                Severity.ERROR,
                f"Mismatched braces: {open_braces} '{{' vs {close_braces} '}}'",
                fix="Check for unclosed braces"
            ))

        open_brackets = self.code.count("[")
        close_brackets = self.code.count("]")
        if open_brackets != close_brackets:
            self.issues.append(ValidationIssue(
                Severity.ERROR,
                f"Mismatched brackets: {open_brackets} '[' vs {close_brackets} ']'",
                fix="Check for unclosed brackets"
            ))

        # Check for common typos
        typos = [
            ("fucntion", "function"),
            ("retrun", "return"),
            ("varible", "variable"),
            ("funtion", "function"),
            ("funciton", "function"),
        ]
        for typo, correct in typos:
            if typo in self.code.lower():
                self.issues.append(ValidationIssue(
                    Severity.ERROR,
                    f"Typo: '{typo}' should be '{correct}'",
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
        typos = [("fucntion", "function"), ("retrun", "return"), ("funtion", "function"), ("funciton", "function")]
        for typo, correct in typos:
            fixed = re.sub(typo, correct, fixed, flags=re.IGNORECASE)

        return fixed if fixed != self.code else None


def validate_code(code: str, code_type: Optional[str] = None) -> ValidationResult:
    """
    Validate code and return results.

    Args:
        code: Code to validate
        code_type: 'python', 'nugget', or None for auto-detect

    Returns:
        ValidationResult with issues and optional fixed code
    """
    if code_type is None:
        # Auto-detect
        if any(x in code for x in ["(function(data)", "ezLog(", "ezChatCompletions("]):
            code_type = "nugget"
        else:
            code_type = "python"

    if code_type in ["nugget", "javascript"]:
        validator = NuggetValidator(code)
    else:
        validator = PythonValidator(code)

    return validator.validate()


def validate_and_report(code: str, code_type: Optional[str] = None) -> str:
    """
    Validate code and return formatted report.

    Args:
        code: Code to validate
        code_type: 'python', 'nugget', or None for auto-detect

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
        errors = [i for i in result.issues if i.severity == Severity.ERROR]
        warnings = [i for i in result.issues if i.severity == Severity.WARNING]

        if errors:
            report.append("\n### ❌ Errors")
            for i in errors:
                report.append(f"- {i.message}")
                if i.fix:
                    report.append(f"  - **Fix**: {i.fix}")

        if warnings:
            report.append("\n### ⚠ Warnings")
            for i in warnings:
                report.append(f"- {i.message}")
                if i.fix:
                    report.append(f"  - **Fix**: {i.fix}")

    if result.fixed_code:
        report.append("\n### 🔧 Auto-Fixed Code Available")

    return "\n".join(report)