from __future__ import annotations
class M(type):
    def __new__(mcs,n,b,ns):
        print('anns:', ns.get('__annotate__'))
        return type.__new__(mcs,n,b,ns)
class C(metaclass=M):
    a: int = None
