class Meta(type):
    def __new__(mcs, name, bases, namespace):
        print(namespace.keys())
        if '__annotate__' in namespace:
            print(namespace['__annotate__'](1))
        return super().__new__(mcs, name, bases, namespace)

class C(metaclass=Meta):
    a: int = 1
