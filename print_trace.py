import traceback
from pydantic.v1 import BaseSettings

try:
    class S(BaseSettings):
        a: int = None
except Exception as e:
    traceback.print_exc()
