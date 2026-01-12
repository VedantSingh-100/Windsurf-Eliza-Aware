"""
Document Tools

Tools for uploading documents to Eliza agents for RAG/Q&A.
"""

from mcp.types import Tool
from typing import Dict, Any

DOCUMENT_TOOLS = [
    Tool(
        name="create_document_upload",
        description="""Create code to UPLOAD DOCUMENTS to an Eliza agent for RAG/Q&A.

USE THIS WHEN: User wants to upload PDFs, text files, or data to knowledge base.

CAPABILITY: Generates code using agent.upload_file_to_agent() or agent.upload_data_to_agent().

REQUIRES: Agent must exist. Best with retriever_strategy="STANDARD" (RAG agent).

UPLOAD TYPES:
- file: Upload a PDF or text file from disk
- text: Upload raw text content directly
- url: Fetch and upload content from a URL

CHUNKING STRATEGIES:
- RECURSIVE_CHARACTER_SPLIT: Best for general documents (default)
- TOKEN_SPLIT: Best for code or structured text
- PAGE_SPLIT: Best for PDFs with clear page boundaries

EXAMPLE TRIGGERS: "upload document", "add PDF", "upload file", "add to knowledge base" """,
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {
                    "type": "string",
                    "description": "UUID of the agent to upload documents to"
                },
                "upload_type": {
                    "type": "string",
                    "enum": ["file", "text", "url"],
                    "description": "Type of upload: file (from disk), text (raw content), or url (fetch from web)"
                },
                "chunking_strategy": {
                    "type": "string",
                    "enum": ["RECURSIVE_CHARACTER_SPLIT", "TOKEN_SPLIT", "PAGE_SPLIT"],
                    "description": "How to split the document into chunks (default: RECURSIVE_CHARACTER_SPLIT)"
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to file (for file upload type)"
                },
                "text_content": {
                    "type": "string",
                    "description": "Raw text content (for text upload type)"
                },
                "url": {
                    "type": "string",
                    "description": "URL to fetch content from (for url upload type)"
                }
            },
            "required": ["agent_id"]
        }
    )
]


def create_document_upload(args: Dict[str, Any]) -> str:
    """Generate document upload code."""
    agent_id = args.get("agent_id", "{AGENT_ID}")
    upload_type = args.get("upload_type", "file")
    chunking = args.get("chunking_strategy", "RECURSIVE_CHARACTER_SPLIT")
    file_path = args.get("file_path", "/path/to/your/document.pdf")
    text_content = args.get("text_content", "Your document content here...")
    url = args.get("url", "https://example.com/document")

    base_code = f'''# Document Upload to Eliza Agent
# Agent ID: {agent_id}

import bnym_eliza as eliza
from bnym_eliza.genai.agent import Agent
from bnym_eliza.utils import get_jwt

# Connect to Eliza
jwt_token = get_jwt()
eliza.session = eliza.Session.connect(
    env='QA',
    jwt_token=jwt_token,
    initiative_id='ELZI-{{YOUR_USERID}}'
)

# Get existing agent
agent = Agent(env='QA')
agent.agent_id = '{agent_id}'

'''

    if upload_type == "file":
        return base_code + f'''# Upload file to agent
file_detail = agent.upload_file_to_agent(
    file_path="{file_path}",
    embedding_model='openai-text-embedding-ada-002',
    chunking_strategy='{chunking}',
    token_split_count=512,
    metadata={{'source': 'uploaded_file'}}
)
print(f"Document uploaded: {{file_detail.agent_doc_id}}")
'''
    elif upload_type == "text":
        return base_code + f'''# Upload text data to agent
text_data = """{text_content}"""

file_detail = agent.upload_data_to_agent(
    text_data=text_data,
    embedding_model='openai-text-embedding-ada-002',
    chunking_strategy='{chunking}',
    token_split_count=512,
    metadata={{'source': 'text_upload'}}
)
print(f"Document uploaded: {{file_detail.agent_doc_id}}")
'''
    else:  # url
        return base_code + f'''# Upload from URL
import requests

# Fetch content from URL
response = requests.get("{url}")
content = response.text

file_detail = agent.upload_data_to_agent(
    text_data=content,
    embedding_model='openai-text-embedding-ada-002',
    chunking_strategy='{chunking}',
    token_split_count=512,
    metadata={{'source': 'url_upload', 'url': '{url}'}}
)
print(f"Document uploaded: {{file_detail.agent_doc_id}}")
'''
