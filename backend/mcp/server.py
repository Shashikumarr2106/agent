"""Unified MCP Server hosting Data, Skill, Analysis, and Chart tools."""
from typing import Any, Callable, Dict, List
from .data_tools import get_dataset_schema, get_dataset_metadata, get_sample_data, execute_sql
from .skill_tools import search_skills, get_skill, get_skill_version, save_skill, update_skill
from .analysis_tools import run_analysis, execute_custom_analysis, list_sdk_methods
from .chart_tools import generate_chart

class MCPServer:
    """Unified Model Context Protocol Server providing standardized agent-to-tool communication."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._tool_descriptions: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register_tool(self, name: str, description: str, func: Callable, parameters: Dict[str, Any] = None):
        self._tools[name] = func
        self._tool_descriptions[name] = {
            "name": name,
            "description": description,
            "parameters": parameters or {}
        }

    def _register_default_tools(self):
        # Data Tools
        self.register_tool(
            "get_dataset_schema",
            "Retrieve column definitions, data types, and statistics for a dataset.",
            get_dataset_schema
        )
        self.register_tool(
            "get_dataset_metadata",
            "Retrieve high-level metadata (filename, row count, column count).",
            get_dataset_metadata
        )
        self.register_tool(
            "get_sample_data",
            "Retrieve first N rows from dataset table.",
            get_sample_data
        )
        self.register_tool(
            "execute_sql",
            "Safely execute a SELECT query against the dataset table.",
            execute_sql
        )

        # Skill Tools
        self.register_tool(
            "search_skills",
            "Search existing reusable analysis skills via pgvector similarity.",
            search_skills
        )
        self.register_tool(
            "get_skill",
            "Retrieve a skill and its version history by skill_id.",
            get_skill
        )
        self.register_tool(
            "get_skill_version",
            "Retrieve a specific version of a skill.",
            get_skill_version
        )
        self.register_tool(
            "save_skill",
            "Save newly approved analysis method as reusable skill v1.",
            save_skill
        )
        self.register_tool(
            "update_skill",
            "Create a new version (e.g., v2) of an existing skill based on feedback.",
            update_skill
        )

        # Analysis Tools
        self.register_tool(
            "run_analysis",
            "Execute a calculation method using the deterministic Analysis SDK.",
            run_analysis
        )
        self.register_tool(
            "execute_custom_analysis",
            "Safely execute sandboxed Python code for approved dynamic skills.",
            execute_custom_analysis
        )
        self.register_tool(
            "list_sdk_methods",
            "List all registered analytical calculation methods in the SDK.",
            list_sdk_methods
        )

        # Chart Tools
        self.register_tool(
            "generate_chart",
            "Generate an interactive chart specification JSON from analysis results.",
            generate_chart
        )

    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Standard tool execution interface."""
        if tool_name not in self._tools:
            return {"error": f"Tool '{tool_name}' not found on MCP Server.", "status": "error"}
        try:
            return self._tools[tool_name](**kwargs)
        except Exception as e:
            return {"error": f"Error executing tool '{tool_name}': {str(e)}", "status": "error"}

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self._tool_descriptions.values())

mcp_server = MCPServer()
