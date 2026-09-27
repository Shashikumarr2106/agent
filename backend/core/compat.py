"""Compatibility layer providing fallback implementations when external packages are not yet installed."""
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError:
    class FieldInfo:
        def __init__(self, default=None, default_factory=None):
            self.default = default
            self.default_factory = default_factory

    def Field(default=None, default_factory=None, **kwargs):
        return FieldInfo(default=default, default_factory=default_factory)

    class BaseModel:
        def __init__(self, **kwargs):
            # Inspect class annotations and field defaults
            cls = self.__class__
            for attr, val in cls.__dict__.items():
                if isinstance(val, FieldInfo):
                    if val.default_factory:
                        setattr(self, attr, val.default_factory())
                    else:
                        setattr(self, attr, val.default)
                elif not attr.startswith("_") and not callable(val):
                    setattr(self, attr, val)

            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self) -> Dict[str, Any]:
            def _serialize(obj):
                if isinstance(obj, BaseModel):
                    return obj.model_dump()
                elif isinstance(obj, dict):
                    return {k: _serialize(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [_serialize(item) for item in obj]
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                return obj

            return {
                k: _serialize(v)
                for k, v in self.__dict__.items()
                if not k.startswith("_")
            }

        def model_dump_json(self) -> str:
            return json.dumps(self.model_dump(), default=str)

        @classmethod
        def model_validate_json(cls, json_str: str):
            data = json.loads(json_str)
            return cls.model_validate(data)

        @classmethod
        def model_validate(cls, data: dict):
            return cls(**data)

__all__ = ["BaseModel", "Field"]
