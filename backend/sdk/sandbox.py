"""Safe execution sandbox for user-approved dynamically generated analysis logic."""
import ast
import math
from typing import Any, Dict
from .base import AnalysisResult

class SecurityViolationError(Exception):
    pass

class SafeCodeValidator(ast.NodeVisitor):
    """AST validator that blocks malicious or unsafe Python syntax."""

    ALLOWED_NODES = {
        ast.Module, ast.Expr, ast.Assign, ast.AugAssign, ast.Name, ast.Constant,
        ast.Num, ast.Str, ast.List, ast.Dict, ast.Tuple, ast.Set,
        ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.Not,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
        ast.And, ast.Or,
        ast.Call, ast.keyword, ast.Subscript, ast.Slice,
        ast.IfExp, ast.For, ast.comprehension, ast.ListComp, ast.DictComp, ast.GeneratorExp,
        ast.FunctionDef, ast.Return, ast.arguments, ast.arg,
        ast.Load, ast.Store, ast.Del
    }

    FORBIDDEN_NAMES = {
        "__import__", "eval", "exec", "open", "compile", "globals", "locals",
        "vars", "dir", "getattr", "setattr", "delattr", "hasattr",
        "os", "sys", "subprocess", "socket", "shutil", "builtins"
    }

    def generic_visit(self, node):
        if type(node) not in self.ALLOWED_NODES:
            raise SecurityViolationError(f"Disallowed Python construct: {type(node).__name__}")
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if node.id in self.FORBIDDEN_NAMES or node.id.startswith("__"):
            raise SecurityViolationError(f"Access to forbidden identifier: '{node.id}'")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr.startswith("__"):
            raise SecurityViolationError(f"Access to private attribute '{node.attr}' is forbidden")
        self.generic_visit(node)

def execute_sandboxed_code(
    code_str: str,
    data: Any,
    context: Dict[str, Any] = None
) -> AnalysisResult:
    """Safely validate and execute approved Python analysis code with restricted scope."""
    try:
        # 1. Parse AST
        parsed = ast.parse(code_str)

        # 2. Security validation
        validator = SafeCodeValidator()
        validator.visit(parsed)

        # 3. Safe environment with built-in mathematical primitives
        safe_builtins = {
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "len": len,
            "float": float,
            "int": int,
            "str": str,
            "bool": bool,
            "sorted": sorted,
            "math": math,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
        }

        local_vars = {
            "data": data,
            "result": None,
            **(context or {})
        }

        # 4. Compile and execute
        compiled = compile(parsed, filename="<sandboxed_skill>", mode="exec")
        exec(compiled, {"__builtins__": safe_builtins}, local_vars)

        output = local_vars.get("result")
        if output is None and "calculate" in local_vars and callable(local_vars["calculate"]):
            output = local_vars["calculate"](data)

        return AnalysisResult(
            method="sandboxed_custom_skill",
            status="success",
            value=output,
            sample_size=len(data) if isinstance(data, list) else 1,
            summary="Sandboxed custom analysis completed successfully.",
            details={"output": output}
        )

    except SecurityViolationError as sve:
        return AnalysisResult(
            method="sandboxed_custom_skill",
            status="error",
            value=None,
            sample_size=0,
            error=f"Security policy violation: {str(sve)}"
        )
    except Exception as e:
        return AnalysisResult(
            method="sandboxed_custom_skill",
            status="error",
            value=None,
            sample_size=0,
            error=f"Execution error in sandboxed code: {str(e)}"
        )
