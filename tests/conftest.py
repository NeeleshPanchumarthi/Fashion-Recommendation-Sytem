import sys
import os
# Ensure the project root is on the import path so that `import app` works during tests.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
