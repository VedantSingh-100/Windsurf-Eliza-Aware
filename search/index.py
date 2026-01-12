"""
EZ Function Search Index

Searchable index of all ez* functions with signatures, keywords, examples.
Used for tool discovery - Cascade searches this to find relevant functions.

Source: NUGGET_JS_FUNCTIONS from eliza_mcp_server.py (validated Dec 22, 2025)
"""

EZ_FUNCTION_INDEX = {
    # ================================================================
    # FULLY WORKING (Validated in QA)
    # ================================================================
    "ezLog": {
        "signature": "ezLog(message)",
        "description": "Debug logging to server console",
        "keywords": ["log", "debug", "print", "console", "trace", "output", "monitor", "track", "record", "diagnostic"],
        "example": 'ezLog("Debug: " + JSON.stringify(data));',
        "status": "WORKS"
    },
    "ezChatCompletions": {
        "signature": "ezChatCompletions(jsonString)",
        "description": "OpenAI-style chat completions - LLM/AI calls",
        "keywords": ["llm", "ai", "gpt", "chat", "generate", "summarize", "analyze", "completion", "openai", "model", "text",
                     "write", "draft", "compose", "rewrite", "translate", "explain", "answer", "respond", "create content",
                     "newsletter", "report", "summary", "digest", "brief", "article", "blog", "document", "review"],
        "example": 'ezChatCompletions(JSON.stringify({model: "openai-gpt-4.1-mini-ptu", messages: [{role: "user", content: "Hi"}]}))',
        "status": "WORKS"
    },
    "ezInternetSearch": {
        "signature": "ezInternetSearch(query)",
        "description": "Google Custom Search API - internet search",
        "keywords": ["search", "google", "internet", "web", "find", "lookup", "news", "query", "online",
                     "research", "discover", "latest", "current", "recent", "trends", "breaking", "updates",
                     "information", "data", "facts", "articles", "sources", "references"],
        "example": 'ezInternetSearch("BNY Mellon headquarters")',
        "status": "WORKS"
    },
    "ezSaveSessionData": {
        "signature": "ezSaveSessionData(key, value)",
        "description": "Save key-value to session for persistence",
        "keywords": ["session", "save", "store", "persist", "remember", "state", "data", "key", "value",
                     "track", "history", "record", "keep", "cache", "preference", "setting", "memory"],
        "example": 'ezSaveSessionData("user_pref", "dark_mode");',
        "status": "WORKS"
    },
    "ezGetSessionData": {
        "signature": "ezGetSessionData(key)",
        "description": "Retrieve session data by key",
        "keywords": ["session", "get", "retrieve", "read", "state", "data", "remember", "key",
                     "fetch", "recall", "history", "preference", "setting", "previous", "stored"],
        "example": 'var pref = ezGetSessionData("user_pref");',
        "status": "WORKS"
    },
    "ezUpdateSessionData": {
        "signature": "ezUpdateSessionData(key, value)",
        "description": "Update existing session data",
        "keywords": ["session", "update", "modify", "change", "state", "data"],
        "example": 'ezUpdateSessionData("counter", "5");',
        "status": "WORKS"
    },
    "ezCanvas": {
        "signature": "ezCanvas(json)",
        "description": "UI canvas operations, returns boolean",
        "keywords": ["canvas", "ui", "interface", "display", "render"],
        "example": 'ezCanvas(JSON.stringify({action: "draw", data: {}}))',
        "status": "WORKS"
    },
    "ezNugget": {
        "signature": "ezNugget(jsonString)",
        "description": "Call another nugget (can recurse/chain)",
        "keywords": ["nugget", "call", "chain", "compose", "invoke", "workflow", "nested",
                     "orchestrate", "pipeline", "sequence", "multi-step", "combine", "reuse"],
        "example": 'ezNugget(JSON.stringify({agentId: "...", nuggetId: "...", data: {}}))',
        "status": "WORKS"
    },

    # ================================================================
    # REQUIRE CONFIGURATION
    # ================================================================
    "ezSqlSelect": {
        "signature": "ezSqlSelect(dataSourceName, label, sql)",
        "description": "SQL queries - 3 positional args",
        "keywords": ["sql", "database", "query", "select", "db", "data", "table",
                     "fetch", "records", "rows", "columns", "report", "analytics", "metrics"],
        "example": 'ezSqlSelect("my_db", "GetUsers", "SELECT * FROM users")',
        "status": "NEEDS_CONFIG",
        "note": "Requires configured data source"
    },
    "ezMail": {
        "signature": "ezMail(jsonString)",
        "description": "Send email - to field must be string[]",
        "keywords": ["email", "mail", "send", "notify", "notification", "message", "smtp",
                     "newsletter", "report", "digest", "reminder", "weekly", "daily", "bulletin",
                     "update", "alert", "subscribe", "broadcast", "outreach", "correspondence"],
        "example": 'ezMail(JSON.stringify({to: ["a@b.com"], subject: "Hi", body: "..."}))',
        "status": "NEEDS_CONFIG",
        "note": 'to field must be array: ["email@example.com"]'
    },
    "ezNexenApi": {
        "signature": "ezNexenApi(secretsPath, env, url, method, body, params, headers)",
        "description": "External API calls - 7 positional args",
        "keywords": ["api", "http", "rest", "external", "request", "call", "webhook", "nexen"],
        "example": 'ezNexenApi("qa/bny/myapp/secrets/api-key", "QA", "https://api.example.com", "GET", null, {}, {})',
        "status": "NEEDS_CONFIG",
        "note": "Secrets path format: env/org/family/app/path"
    },
    "ezToken": {
        "signature": "ezToken(secretsPath)",
        "description": "Get token from secrets",
        "keywords": ["token", "auth", "authentication", "secret", "credential"],
        "example": 'ezToken("qa/bny/myapp/secrets/api-key")',
        "status": "NEEDS_CONFIG",
        "note": "Requires secrets path format: env/org/family/app/path"
    },
    "ezCopilotChat": {
        "signature": "ezCopilotChat(jsonString)",
        "description": "Copilot chat - requires sessionId",
        "keywords": ["copilot", "chat", "assistant", "ai"],
        "example": 'ezCopilotChat(JSON.stringify({sessionId: "...", message: "Hi"}))',
        "status": "NEEDS_CONFIG",
        "note": "Requires sessionId field in JSON"
    },
    "ezCopilotQuery": {
        "signature": "ezCopilotQuery(jsonString)",
        "description": "Copilot query - requires queryString",
        "keywords": ["copilot", "query", "search", "assistant"],
        "example": 'ezCopilotQuery(JSON.stringify({queryString: "..."}))',
        "status": "NEEDS_CONFIG",
        "note": "Requires queryString field in JSON"
    },
    "ezSharePoint": {
        "signature": "ezSharePoint(jsonString)",
        "description": "SharePoint integration",
        "keywords": ["sharepoint", "document", "file", "microsoft", "office", "365",
                     "upload", "download", "folder", "library", "collaboration", "intranet", "portal"],
        "example": 'ezSharePoint(JSON.stringify({siteUrl: "...", action: "list"}))',
        "status": "NEEDS_CONFIG",
        "note": "Requires agent identity/secrets"
    },
    "ezJiraSupport": {
        "signature": "ezJiraSupport(jsonString)",
        "description": "Jira integration - tickets, issues",
        "keywords": ["jira", "ticket", "issue", "bug", "task", "project", "atlassian",
                     "sprint", "backlog", "story", "epic", "kanban", "scrum", "agile", "track"],
        "example": 'ezJiraSupport(JSON.stringify({action: "search", jql: "project = PROJ"}))',
        "status": "NEEDS_CONFIG",
        "note": "Requires secrets path"
    },
    "ezComms": {
        "signature": "ezComms(jsonString)",
        "description": "Communications/messaging",
        "keywords": ["comms", "communication", "message", "notify", "alert"],
        "example": 'ezComms(JSON.stringify({type: "slack", channel: "...", message: "..."}))',
        "status": "NEEDS_CONFIG",
        "note": "Requires agent identity"
    },
    "ezA2A": {
        "signature": "ezA2A(serverId, message, secretsPath, contextId, tasks)",
        "description": "Agent-to-Agent protocol - 5 args",
        "keywords": ["a2a", "agent", "protocol", "multi-agent", "orchestration"],
        "example": 'ezA2A("server-id", "message", "secrets/path", "context-id", [])',
        "status": "NEEDS_CONFIG",
        "note": "Requires A2A server setup"
    },
    "ezMCP": {
        "signature": "ezMCP(serverId, toolName, params...)",
        "description": "MCP protocol calls - variable args",
        "keywords": ["mcp", "protocol", "tool", "server", "external"],
        "example": 'ezMCP("server-id", "tool-name", {param: "value"})',
        "status": "NEEDS_CONFIG",
        "note": "Multiple args required"
    },

    # ================================================================
    # LIMITED IN QA
    # ================================================================
    "ezPython": {
        "signature": "ezPython(code)",
        "description": "Python code execution",
        "keywords": ["python", "code", "execute", "script", "run"],
        "example": 'ezPython("print(2+2)")',
        "status": "QA_LIMITED",
        "note": "No available instances in QA environment"
    },
    "ezTextToSpeech": {
        "signature": "ezTextToSpeech(jsonString)",
        "description": "Text to speech / audio generation",
        "keywords": ["tts", "speech", "audio", "voice", "speak", "sound"],
        "example": 'ezTextToSpeech(JSON.stringify({text: "Hello", voice: "en-US"}))',
        "status": "QA_LIMITED",
        "note": "Model not found in QA"
    },
    "ezParse": {
        "signature": "ezParse(string)",
        "description": "Parse data",
        "keywords": ["parse", "extract", "convert", "transform"],
        "example": 'ezParse(dataString)',
        "status": "QA_LIMITED",
        "note": "Under review - use JSON.parse() instead"
    },
    "ezDeepResearch": {
        "signature": "ezDeepResearch(jsonString)",
        "description": "AI-powered deep research",
        "keywords": ["research", "deep", "analysis", "investigate", "study",
                     "comprehensive", "thorough", "in-depth", "detailed", "exhaustive",
                     "explore", "examine", "report", "findings", "insights"],
        "example": 'ezDeepResearch(JSON.stringify({topic: "...", depth: 3}))',
        "status": "QA_LIMITED",
        "note": "Invalid number of arguments - signature unknown"
    },
    "ezDataQuery": {
        "signature": "ezDataQuery(jsonString)",
        "description": "Data query operations",
        "keywords": ["data", "query", "fetch", "retrieve", "database"],
        "example": 'ezDataQuery(JSON.stringify({source: "...", query: "..."}))',
        "status": "QA_LIMITED",
        "note": "Invalid number of arguments - signature unknown"
    },

    # ================================================================
    # AVAILABLE (Not fully tested but should work)
    # ================================================================
    "ezChat": {
        "signature": "ezChat(jsonString)",
        "description": "Chat with another agent",
        "keywords": ["chat", "agent", "talk", "converse", "query", "ask", "message"],
        "example": 'ezChat(JSON.stringify({agentId: "...", message: "Hello"}))',
        "status": "AVAILABLE"
    },
    "ezEmbeddings": {
        "signature": "ezEmbeddings(jsonString)",
        "description": "Generate vector embeddings",
        "keywords": ["embeddings", "vector", "similarity", "semantic", "encode", "embedding"],
        "example": 'ezEmbeddings(JSON.stringify({model: "openai-text-embedding-ada-002", input: "text"}))',
        "status": "AVAILABLE"
    },
    "ezPrompt": {
        "signature": "ezPrompt(jsonString)",
        "description": "Prompt management/retrieval",
        "keywords": ["prompt", "template", "instruction", "system"],
        "example": 'ezPrompt(JSON.stringify({promptId: "...", variables: {}}))',
        "status": "AVAILABLE"
    },
    "ezPromptGroup": {
        "signature": "ezPromptGroup(jsonString)",
        "description": "Prompt groups management",
        "keywords": ["prompt", "group", "collection", "template"],
        "example": 'ezPromptGroup(JSON.stringify({groupId: "..."}))',
        "status": "AVAILABLE"
    },
    "ezGenAISearch": {
        "signature": "ezGenAISearch(query)",
        "description": "GenAI-powered search with summarization",
        "keywords": ["search", "genai", "ai", "find", "research", "query", "intelligent",
                     "smart search", "semantic", "understand", "context", "meaning", "natural language"],
        "example": 'ezGenAISearch("search query")',
        "status": "AVAILABLE"
    },
    "ezDataSearch": {
        "signature": "ezDataSearch(jsonString)",
        "description": "Data search operations",
        "keywords": ["data", "search", "find", "query", "lookup"],
        "example": 'ezDataSearch(JSON.stringify({query: "...", limit: 10}))',
        "status": "AVAILABLE"
    },
    "ezFunction": {
        "signature": "ezFunction(jsonString)",
        "description": "Call a registered function",
        "keywords": ["function", "call", "invoke", "execute", "run"],
        "example": 'ezFunction(JSON.stringify({funcNameKey: "myFunc", args: {}}))',
        "status": "AVAILABLE"
    },
    "ezApi": {
        "signature": "ezApi(url, method, headers, body)",
        "description": "Generic API call - 4 args",
        "keywords": ["api", "http", "rest", "call", "request", "fetch"],
        "example": 'ezApi("https://api.example.com", "GET", {}, null)',
        "status": "AVAILABLE"
    },
    "ezJavaScript": {
        "signature": "ezJavaScript(code)",
        "description": "Nested JavaScript execution",
        "keywords": ["javascript", "js", "code", "execute", "script", "run"],
        "example": 'ezJavaScript("return 2 + 2;")',
        "status": "AVAILABLE"
    },
    "ezImageToText": {
        "signature": "ezImageToText(jsonString)",
        "description": "Image analysis/OCR - extract text from images",
        "keywords": ["image", "ocr", "vision", "picture", "analyze", "describe", "extract", "text",
                     "scan", "read", "document", "photo", "screenshot", "recognize", "caption"],
        "example": 'ezImageToText(JSON.stringify({imageUrl: "https://...", prompt: "Describe"}))',
        "status": "AVAILABLE"
    },
    "ezTextToImage": {
        "signature": "ezTextToImage(jsonString)",
        "description": "Image generation from text",
        "keywords": ["image", "generate", "create", "picture", "art", "dalle", "text",
                     "draw", "illustration", "visual", "graphic", "design", "artwork", "render"],
        "example": 'ezTextToImage(JSON.stringify({prompt: "A sunset"}))',
        "status": "AVAILABLE"
    },
    "ezTextToVideo": {
        "signature": "ezTextToVideo(jsonString)",
        "description": "Video generation from text",
        "keywords": ["video", "generate", "create", "movie", "clip", "animation"],
        "example": 'ezTextToVideo(JSON.stringify({prompt: "A walking cat"}))',
        "status": "AVAILABLE"
    },
    "ezJson": {
        "signature": "ezJson(data)",
        "description": "JSON utilities - stringify/parse",
        "keywords": ["json", "parse", "stringify", "convert", "format"],
        "example": 'ezJson({key: "value"})',
        "status": "AVAILABLE"
    },
    "ezUserLog": {
        "signature": "ezUserLog(message)",
        "description": "User-visible logging (not just debug)",
        "keywords": ["log", "user", "message", "output", "display"],
        "example": 'ezUserLog("Processing complete!")',
        "status": "AVAILABLE"
    },
    "ezUser": {
        "signature": "ezUser()",
        "description": "Get current user info",
        "keywords": ["user", "info", "current", "profile", "identity"],
        "example": 'var user = ezUser(); // returns user object',
        "status": "AVAILABLE"
    },
    "ezSecret": {
        "signature": "ezSecret(secretsPath)",
        "description": "Get secrets by path",
        "keywords": ["secret", "credential", "password", "key", "auth"],
        "example": 'ezSecret("qa/bny/myapp/secrets/api-key")',
        "status": "AVAILABLE"
    },
    "ezSecret2": {
        "signature": "ezSecret2(jsonString)",
        "description": "Alternative secrets API",
        "keywords": ["secret", "credential", "password", "key", "auth"],
        "example": 'ezSecret2(JSON.stringify({path: "...", key: "..."}))',
        "status": "AVAILABLE"
    },
    "ezConfirm": {
        "signature": "ezConfirm(message)",
        "description": "User confirmation dialog",
        "keywords": ["confirm", "dialog", "prompt", "user", "ask", "yes", "no"],
        "example": 'var ok = ezConfirm("Proceed?"); if(ok) {...}',
        "status": "AVAILABLE"
    },
    "ezNotify": {
        "signature": "ezNotify(message)",
        "description": "Send notification to user",
        "keywords": ["notify", "notification", "alert", "message", "toast"],
        "example": 'ezNotify("Task completed successfully!")',
        "status": "AVAILABLE"
    },
    "ezBrowser": {
        "signature": "ezBrowser(timeout, browserId)",
        "description": "Browser automation session",
        "keywords": ["browser", "automation", "web", "scrape", "selenium", "puppeteer",
                     "crawl", "navigate", "click", "fill", "form", "webpage", "site", "bot"],
        "example": 'var browser = ezBrowser(30); // 30s timeout',
        "status": "AVAILABLE"
    },
    "ezExperiments": {
        "signature": "ezExperiments(jsonString)",
        "description": "A/B experiments and feature flags",
        "keywords": ["experiment", "ab", "test", "feature", "flag", "variant"],
        "example": 'ezExperiments(JSON.stringify({expId: "...", variant: "A"}))',
        "status": "AVAILABLE"
    },
    "ezComputer": {
        "signature": "ezComputer(action, params)",
        "description": "Computer use/automation",
        "keywords": ["computer", "automation", "click", "type", "mouse", "keyboard"],
        "example": 'ezComputer("click", {x: 100, y: 200})',
        "status": "AVAILABLE"
    },
    "ezVaApiStream": {
        "signature": "ezVaApiStream(jsonString)",
        "description": "VA API streaming",
        "keywords": ["va", "api", "stream", "streaming", "realtime"],
        "example": 'ezVaApiStream(JSON.stringify({endpoint: "...", stream: true}))',
        "status": "AVAILABLE"
    },
    "ezDataCreate": {
        "signature": "ezDataCreate(jsonString)",
        "description": "Create data record",
        "keywords": ["data", "create", "insert", "add", "record", "new"],
        "example": 'ezDataCreate(JSON.stringify({table: "...", data: {}}))',
        "status": "AVAILABLE"
    },
    "ezSharedItems": {
        "signature": "ezSharedItems(jsonString)",
        "description": "Shared items management",
        "keywords": ["shared", "items", "share", "collaborate", "common"],
        "example": 'ezSharedItems(JSON.stringify({action: "list"}))',
        "status": "AVAILABLE"
    },
    "sleep": {
        "signature": "sleep(ms)",
        "description": "Sleep/wait for milliseconds",
        "keywords": ["sleep", "wait", "delay", "pause", "timeout"],
        "example": 'sleep(1000); // wait 1 second',
        "status": "AVAILABLE"
    },

    # ================================================================
    # NOT AVAILABLE (Deprecated or unavailable in sandbox)
    # ================================================================
    "ezQuery": {
        "signature": "ezQuery(agentId, query)",
        "description": "NOT AVAILABLE in sandbox",
        "keywords": ["query", "agent", "deprecated"],
        "example": "N/A",
        "status": "NOT_AVAILABLE",
        "note": "Use ezChat or AGENT function type instead"
    },
    "ezSendEmail": {
        "signature": "ezSendEmail(...)",
        "description": "NOT AVAILABLE in sandbox",
        "keywords": ["email", "send", "deprecated"],
        "example": "N/A",
        "status": "NOT_AVAILABLE",
        "note": "Use ezMail with secrets configured instead"
    },
}

# List of function names by category for quick lookup
EZ_FUNCTIONS_BY_CATEGORY = {
    "communication": ["ezMail", "ezChat", "ezNotify", "ezComms", "ezConfirm"],
    "search": ["ezInternetSearch", "ezGenAISearch", "ezDataSearch"],
    "ai": ["ezChatCompletions", "ezEmbeddings", "ezImageToText", "ezTextToImage", "ezTextToVideo", "ezTextToSpeech", "ezDeepResearch"],
    "data": ["ezSqlSelect", "ezSaveSessionData", "ezGetSessionData", "ezUpdateSessionData", "ezDataQuery", "ezDataCreate"],
    "integration": ["ezNexenApi", "ezJiraSupport", "ezSharePoint", "ezA2A", "ezMCP", "ezApi"],
    "utility": ["ezLog", "ezUserLog", "ezNugget", "ezFunction", "ezJson", "ezCopilotChat", "ezCopilotQuery"],
    "user": ["ezUser", "ezSecret", "ezSecret2", "ezToken", "sleep"],
    "automation": ["ezBrowser", "ezComputer", "ezCanvas", "ezPython", "ezJavaScript"],
    "experimental": ["ezExperiments", "ezVaApiStream", "ezSharedItems", "ezPrompt", "ezPromptGroup"],
}


# =============================================================================
# INTENT PATTERNS - Map natural language intents to ez* functions
# =============================================================================
# These patterns help detect what the user wants to build and which
# functions are required vs optional for that use case.

INTENT_PATTERNS = {
    # Communication intents
    "newsletter": {
        "description": "Automated newsletter or digest emails",
        "triggers": ["newsletter", "digest", "weekly email", "daily email", "bulletin", "subscriber"],
        "requires": ["ezMail"],
        "optional": ["ezChatCompletions", "ezInternetSearch"],
        "example_prompt": "Make me an agent that sends weekly newsletters"
    },
    "email_notification": {
        "description": "Simple email alerts or notifications",
        "triggers": ["email alert", "send email", "notify by email", "email notification", "mail"],
        "requires": ["ezMail"],
        "optional": ["ezLog"],
        "example_prompt": "Send email when something happens"
    },

    # Research intents
    "deep_research": {
        "description": "Comprehensive internet research with AI analysis",
        "triggers": ["deep research", "research", "investigate", "comprehensive analysis", "in-depth"],
        "requires": ["ezInternetSearch", "ezChatCompletions"],
        "optional": ["ezDeepResearch", "ezGenAISearch"],
        "example_prompt": "Research a topic and give me a summary"
    },
    "news_monitor": {
        "description": "Track and monitor news on topics",
        "triggers": ["news", "monitor", "track", "latest", "breaking", "updates", "trends"],
        "requires": ["ezInternetSearch"],
        "optional": ["ezChatCompletions", "ezMail", "ezSaveSessionData"],
        "example_prompt": "Monitor news about a company"
    },

    # Data & Analytics intents
    "data_tracking": {
        "description": "Track and persist data across sessions",
        "triggers": ["track", "remember", "persist", "history", "log data", "record"],
        "requires": ["ezSaveSessionData", "ezGetSessionData"],
        "optional": ["ezLog", "ezUpdateSessionData"],
        "example_prompt": "Track user preferences over time"
    },
    "database_query": {
        "description": "Query databases for reports or analytics",
        "triggers": ["database", "sql", "query data", "report", "analytics", "metrics", "dashboard"],
        "requires": ["ezSqlSelect"],
        "optional": ["ezChatCompletions", "ezMail"],
        "example_prompt": "Generate weekly reports from database"
    },

    # AI Content intents
    "content_generation": {
        "description": "Generate text content using AI",
        "triggers": ["write", "draft", "compose", "create content", "summarize", "article", "blog"],
        "requires": ["ezChatCompletions"],
        "optional": ["ezInternetSearch"],
        "example_prompt": "Write a blog post about a topic"
    },
    "translation": {
        "description": "Translate text between languages",
        "triggers": ["translate", "translation", "language", "multilingual"],
        "requires": ["ezChatCompletions"],
        "optional": [],
        "example_prompt": "Translate documents to Spanish"
    },

    # Integration intents
    "jira_automation": {
        "description": "Automate Jira ticket operations",
        "triggers": ["jira", "ticket", "issue", "sprint", "backlog", "story", "bug tracking"],
        "requires": ["ezJiraSupport"],
        "optional": ["ezChatCompletions", "ezMail"],
        "example_prompt": "Create Jira tickets from user requests"
    },
    "sharepoint_automation": {
        "description": "Automate SharePoint document operations",
        "triggers": ["sharepoint", "document", "file management", "office 365", "intranet"],
        "requires": ["ezSharePoint"],
        "optional": ["ezChatCompletions"],
        "example_prompt": "Upload reports to SharePoint"
    },
    "api_integration": {
        "description": "Call external APIs",
        "triggers": ["api", "webhook", "external service", "integration", "connect to"],
        "requires": ["ezNexenApi"],
        "optional": ["ezToken", "ezSecret"],
        "example_prompt": "Call an external API and process results"
    },

    # Visual intents
    "image_analysis": {
        "description": "Analyze or extract text from images",
        "triggers": ["analyze image", "ocr", "read image", "describe image", "vision", "scan document"],
        "requires": ["ezImageToText"],
        "optional": ["ezChatCompletions"],
        "example_prompt": "Extract text from scanned documents"
    },
    "image_generation": {
        "description": "Generate images from text descriptions",
        "triggers": ["generate image", "create image", "draw", "illustration", "artwork", "visual"],
        "requires": ["ezTextToImage"],
        "optional": [],
        "example_prompt": "Generate marketing images from descriptions"
    },

    # Automation intents
    "web_scraping": {
        "description": "Scrape or automate web pages",
        "triggers": ["scrape", "crawl", "automate browser", "web automation", "fill form"],
        "requires": ["ezBrowser"],
        "optional": ["ezChatCompletions", "ezSaveSessionData"],
        "example_prompt": "Scrape data from websites"
    },
    "multi_agent": {
        "description": "Orchestrate multiple agents or nuggets",
        "triggers": ["multi-agent", "orchestrate", "chain", "pipeline", "workflow", "sequence"],
        "requires": ["ezNugget"],
        "optional": ["ezChat", "ezA2A"],
        "example_prompt": "Chain multiple nuggets together"
    },

    # Chat/Assistant intents
    "chatbot": {
        "description": "Interactive chat or Q&A assistant",
        "triggers": ["chatbot", "assistant", "answer questions", "help desk", "support"],
        "requires": ["ezChatCompletions"],
        "optional": ["ezInternetSearch", "ezSaveSessionData", "ezGetSessionData"],
        "example_prompt": "Build a Q&A chatbot"
    },
}