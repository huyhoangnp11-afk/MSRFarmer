import pystray
import inspect

class A:
    def start_farming(self, icon=None, item=None, auto_started=False):
        pass

a = A()
try:
    print(inspect.signature(a.start_farming).bind())
    print("Zero args OK")
except Exception as e:
    print("Zero args failed:", e)

try:
    print(inspect.signature(a.start_farming).bind(None, None))
    print("Two args OK")
except Exception as e:
    print("Two args failed:", e)

try:
    pystray.MenuItem('Test', a.start_farming)
    print("MenuItem OK!")
except Exception as e:
    print("MenuItem Exception:", type(e), e)
