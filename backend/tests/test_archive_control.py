"""归档进度：切文件夹时百分比不能超过 100%，累计计数单独统计。"""
import os, sys, tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("FLYMAIL_DATA_DIR", tempfile.mkdtemp(prefix="flymail-test-ac-"))

from services.backup import ArchiveControl  # noqa: E402


def test_per_folder_progress_resets():
    c = ArchiveControl()
    c.begin_folder("a@x.com", "INBOX", 10)
    for _ in range(10):
        c.tick(True)
    snap = c.snapshot()
    assert snap["percent"] == 100.0
    assert snap["overall_archived"] == 10

    # 切到下一个文件夹：当前文件夹计数归零，不会出现 12/4 = 300%
    c.begin_folder("a@x.com", "Sent", 4)
    c.tick(True)
    c.tick(False)
    snap = c.snapshot()
    assert snap["done"] == 2
    assert snap["total"] == 4
    assert snap["percent"] == 50.0
    # 累计计数保留整个任务的结果
    assert snap["overall_done"] == 12
    assert snap["overall_archived"] == 11
    assert snap["overall_failed"] == 1


def test_never_exceeds_100_percent():
    c = ArchiveControl()
    for folder, total in (("INBOX", 3), ("Sent", 2), ("Trash", 5)):
        c.begin_folder("a@x.com", folder, total)
        for _ in range(total):
            c.tick(True)
        assert c.snapshot()["percent"] <= 100.0
