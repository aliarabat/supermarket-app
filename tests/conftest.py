# tests/conftest.py
import sys
import os

# Add the project root (parent of tests/) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))