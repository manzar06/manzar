import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("IG_APP_SECRET", "test-secret")
os.environ.setdefault("IG_VERIFY_TOKEN", "test-verify")
os.environ.setdefault("IG_USER_ID", "999")
os.environ["DB_PATH"] = ":memory:"
