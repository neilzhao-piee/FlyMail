"""归档增强测试：正文全文索引、暂停/恢复、进度快照。"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("FLYMAIL_DATA_DIR", tempfile.mkdtemp(prefix="flymail-test-archive-"))

import pytest  # noqa: E402

import db as dbmod  # noqa: E402
from services.backup import ArchiveControl  # noqa: E402


@pytest.fixture
async def fresh_db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(dbmod, "DB_PATH", str(data_dir / "flymail.db"))
    dbmod._db_instance = None
    await dbmod.init_db()
    yield dbmod
    if dbmod._db_instance is not None:
        await dbmod._db_instance.close()
        dbmod._db_instance = None


def _archive(uid: int, subject: str, body: str, *, folder: str = "INBOX", deleted: int = 0) -> dict:
    return {
        "user_uid": "u1", "account_id": "acc1", "folder": folder, "uid": uid,
        "message_id": f"<{uid}@example.com>", "subject": subject,
        "from_addr": "alice@example.com", "to_addr": "me@example.com", "cc": "",
        "date": "2026-10-01T10:00:00Z", "size": 1234,
        "eml_path": f"/tmp/x/{uid}.eml", "flags": "", "has_attachments": 0,
        "is_deleted_on_server": deleted, "body_text": body,
    }


async def _seed(db) -> None:
    await db.upsert_message_archive(_archive(1, "项目周报", "本周完成了归档正文检索的设计"))
    await db.upsert_message_archive(_archive(2, "Invoice", "please review the invoice"))
    await db.upsert_message_archive(_archive(3, "已删除的邮件", "旧通知", deleted=1))


async def test_archive_fts_ready(fresh_db):
    assert fresh_db.archive_fts_available() is True


async def test_archive_body_search(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.get_archived_messages("u1", q="归档正文检索")
    assert result["total"] == 1
    assert result["search_mode"] == "archive_fts"
    assert "<mark>归档正文检索</mark>" in result["messages"][0]["snippet"]


async def test_archive_short_query_falls_back(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.get_archived_messages("u1", q="周报")
    assert result["search_mode"] == "archive_meta"
    assert result["total"] == 1


async def test_archive_deleted_filter_with_search(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.get_archived_messages("u1", q="旧通知", deleted_filter="deleted")
    assert result["total"] == 1
    result = await fresh_db.get_archived_messages("u1", q="旧通知", deleted_filter="alive")
    assert result["total"] == 0


async def test_archive_body_search_english(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.get_archived_messages("u1", q="invoice")
    assert result["total"] == 1
    assert result["messages"][0]["uid"] == 2


def test_archive_control_pause_resume():
    ctl = ArchiveControl()
    ctl.begin_folder("a@example.com", "INBOX", 10)
    assert ctl.snapshot()["running"] is True
    ctl.pause()
    snap = ctl.snapshot()
    assert snap["paused"] is True
    ctl.resume()
    assert ctl.snapshot()["paused"] is False
    ctl.tick(True)
    ctl.tick(False)
    snap = ctl.snapshot()
    assert snap["done"] == 2 and snap["archived"] == 1 and snap["failed"] == 1
    assert snap["percent"] == 20.0
    ctl.finish()
    assert ctl.snapshot()["running"] is False
