# Copy llm_lab from sibling directory for local development
# In production, this symlink/copy ensures the shared package is available
import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent / "llm_finetuning"
if repo_root.exists() and str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
