import ast
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DuplicateDefinitionTests(unittest.TestCase):
    """A module-level name defined twice silently disables the first definition.

    fetch_rss.py carried three such pairs until #42: edits to the earlier copy
    had no effect at run time because Python binds the later one.
    """

    def test_no_module_defines_a_function_or_class_twice(self):
        duplicates = {}
        for path in sorted((ROOT / "scripts").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            names = Counter(
                node.name
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            )
            repeated = sorted(name for name, count in names.items() if count > 1)
            if repeated:
                duplicates[str(path.relative_to(ROOT))] = repeated
        self.assertEqual(duplicates, {})


if __name__ == "__main__":
    unittest.main()
