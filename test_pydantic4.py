import inspect
class M(type):
    def __new__(mcs,n,b,ns):
        dummy = type.__new__(mcs,n,b,ns.copy())
        anns = inspect.get_annotations(dummy, eval_str=True)
        print('anns:', anns)
        return type.__new__(mcs,n,b,ns)
class C(metaclass=M):
    a: int = None
