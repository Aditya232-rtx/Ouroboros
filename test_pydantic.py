from typing import Optional, Any
from pydantic.v1 import BaseSettings

class S(BaseSettings):
    a: int = None
    b: float = None
    c: int = 0
