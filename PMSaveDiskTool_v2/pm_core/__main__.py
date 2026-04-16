"""Entry point for `python -m pm_core` — launches the GUI.

Kept in pm_core because it is on sys.path regardless of invocation style.
"""

import os
import sys

_here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _here not in sys.path:
    sys.path.insert(0, _here)

from pm_gui import main  # noqa: E402

if __name__ == "__main__":
    main()
