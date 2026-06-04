import os
import sys

# Must be set before any Qt import so it takes effect on QApplication init.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Allow tests to import app modules without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
