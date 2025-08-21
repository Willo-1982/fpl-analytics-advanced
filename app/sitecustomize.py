# Ensure the repository root is on sys.path when running Streamlit from app/
import sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent  # parent of "app"
root_str = str(root)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
