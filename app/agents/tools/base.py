from dataclasses import dataclass, field
from typing import Callable, Dict, Any


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
