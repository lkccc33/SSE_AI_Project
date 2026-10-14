"""Regenerate the dependency-free SVG graph preview."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('build_kg.py')),run_name='__main__')
