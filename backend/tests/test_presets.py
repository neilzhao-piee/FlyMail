"""邮箱服务商预设测试：域名匹配与列表。"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("FLYMAIL_DATA_DIR", tempfile.mkdtemp(prefix="flymail-test-preset-"))

from providers.presets import detect_preset, list_presets  # noqa: E402


def test_detect_preset_matches_domain():
    for email in ("a@139.com", "b@189.cn", "c@sohu.com", "d@aliyun.com"):
        preset = detect_preset(email)
        assert preset is not None
        assert preset["imap_host"].startswith("imap.")
        assert preset["smtp_port"] == 465


def test_detect_preset_case_insensitive():
    assert detect_preset("X@139.COM") is not None


def test_detect_preset_unknown_domain():
    assert detect_preset("a@gmail.com") is None
    assert detect_preset("") is None


def test_list_presets_has_labels():
    presets = list_presets()
    domains = {p["domain"] for p in presets}
    assert {"139.com", "189.cn", "sohu.com", "aliyun.com"} <= domains
    assert all(p["label"] for p in presets)
