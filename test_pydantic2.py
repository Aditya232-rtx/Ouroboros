from pydantic.v1 import BaseSettings

class S(BaseSettings):
    __annotations__ = {'a': int, 'b': float}
    a = None
    b = 0.0

print(S().dict())
