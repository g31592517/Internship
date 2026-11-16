import os
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))
# Isolated database/data dir for the whole test session; must be set before api.main is imported.
_tmp = tempfile.mkdtemp(prefix="internship-tests-")
os.environ["INTERNSHIP_DATA_DIR"] = _tmp
os.environ["INTERNSHIP_DB"] = os.path.join(_tmp, "test.db")
for k in ("SMTP_USER", "SMTP_PASSWORD", "APPLY_DRY_RUN"):
    os.environ.pop(k, None)
