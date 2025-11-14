"""CLI package - re-export from cli.py module."""

# Import everything from the cli.py module (which is in parent directory)
import sys
from pathlib import Path

# Add parent to path to import cli module
_parent = Path(__file__).parent.parent
if str(_parent) not in sys.path:
    sys.path.insert(0, str(_parent))

# Now import from the cli module (which is cli.py in parent)
import importlib.util
_cli_path = _parent / "cli.py"
spec = importlib.util.spec_from_file_location("uwss_cli", _cli_path)
cli_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_module)

# Re-export main functions
build_parser = cli_module.build_parser
main = cli_module.main

