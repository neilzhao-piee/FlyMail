"""归档文件名清洗：控制字符不能进入文件名（会让 rsync/SMB 失败）。"""
import os, sys, tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("FLYMAIL_DATA_DIR", tempfile.mkdtemp(prefix="flymail-test-san-"))

from services.backup import sanitize_filename, build_eml_filename  # noqa: E402


def test_control_chars_removed():
    assert sanitize_filename("a\tb\r\nc") == "a b c"
    assert "\t" not in sanitize_filename("x\ty")
    assert "\r" not in sanitize_filename("x\ry")
    assert "\n" not in sanitize_filename("x\ny")


def test_eml_filename_has_no_control_chars():
    name = build_eml_filename(188023, "You’re\r\n\r\nalmost a Level 6", "Wed, 20 Nov 2026 10:00:00 +0800")
    assert not any(ord(c) < 32 for c in name)
    assert name.startswith("2026-11-20_")
