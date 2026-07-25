import sys
from pathlib import Path

# Rend les modules backend importables depuis le dossier tests/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
