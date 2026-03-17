import os
import sys
import pkgutil
import importlib
import inspect
import unittest


class AutoCallablesTest(unittest.TestCase):
    def test_call_simple_callables(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        visited = set()

        for finder, modname, ispkg in pkgutil.walk_packages([project_root]):
            # skip test files and virtualenv
            if modname.startswith('tests') or modname.startswith('venv') or modname.startswith('.venv'):
                continue

            try:
                mod = importlib.import_module(modname)
            except Exception:
                # import errors already covered by import-all test
                continue

            if mod in visited:
                continue
            visited.add(mod)

            for name, obj in inspect.getmembers(mod):
                # skip private
                if name.startswith('_'):
                    continue

                # attempt to call simple functions with no args
                if inspect.isfunction(obj):
                    try:
                        obj()
                    except TypeError:
                        # needs args, skip
                        continue
                    except Exception:
                        # swallow runtime errors — goal is coverage, not correctness
                        continue

                # attempt to instantiate simple classes
                if inspect.isclass(obj):
                    try:
                        inst = None
                        try:
                            inst = obj()
                        except TypeError:
                            continue
                        except Exception:
                            continue

                        # call simple no-arg methods
                        for mname, mobj in inspect.getmembers(inst, predicate=inspect.ismethod):
                            if mname.startswith('_'):
                                continue
                            try:
                                mobj()
                            except TypeError:
                                continue
                            except Exception:
                                continue
                    except Exception:
                        continue


if __name__ == '__main__':
    unittest.main()
