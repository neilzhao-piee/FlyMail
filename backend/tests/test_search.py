"""全文搜索测试：FTS5 索引、中文短词回退、跨账号检索、索引随缓存更新。"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# db 模块在 import 时根据该环境变量拼 DB_PATH，测试用临时目录避免碰到真实库
os.environ.setdefault("FLYMAIL_DATA_DIR", tempfile.mkdtemp(prefix="flymail-test-"))

import pytest  # noqa: E402

import db as dbmod  # noqa: E402
from models import CachedMessage  # noqa: E402


@pytest.fixture
async def fresh_db(tmp_path, monkeypatch):
    """每个用例独立一个全新 SQLite 文件，并重置全局单例连接。"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(dbmod, "DB_PATH", str(data_dir / "flymail.db"))
    dbmod._db_instance = None
    await dbmod.init_db()
    yield dbmod
    if dbmod._db_instance is not None:
        await dbmod._db_instance.close()
        dbmod._db_instance = None


async def _add_account(db, account_id: str, email: str, user_uid: str = "u1") -> None:
    conn = await db.get_db()
    await conn.execute(
        "INSERT INTO accounts (id, user_uid, email, provider) VALUES (?, ?, ?, ?)",
        (account_id, user_uid, email, "custom"),
    )
    await conn.commit()


def _msg(account_id: str, uid: int, subject: str, body: str, *, folder: str = "INBOX",
         date: str = "2026-10-01T10:00:00Z", from_addr: str = "alice@example.com") -> CachedMessage:
    return CachedMessage(
        id=f"{account_id}:{folder}:{uid}",
        account_id=account_id,
        user_uid="u1",
        uid=uid,
        folder=folder,
        subject=subject,
        from_addr=from_addr,
        to_addr="me@example.com",
        cc="",
        date=date,
        body_text=body,
        cached_at=1.0,
    )


async def _seed(db) -> None:
    await _add_account(db, "accA", "a@example.com")
    await _add_account(db, "accB", "b@example.com")
    await db.upsert_cached_messages([
        _msg("accA", 1, "项目周报", "本周完成了邮件备份功能的设计与实现"),
        _msg("accA", 2, "Invoice October", "Please review the invoice attached", date="2026-10-02T09:00:00Z"),
        _msg("accB", 3, "会议纪要", "讨论了下季度的产品规划", date="2026-09-20T09:00:00Z"),
    ])


async def test_fts_ready(fresh_db):
    assert fresh_db.fts_available() is True


async def test_chinese_fulltext_hits_with_snippet(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.search_cached_messages("u1", "邮件备份")
    assert result["mode"] == "fts"
    assert result["total"] == 1
    hit = result["messages"][0]
    assert hit["subject"] == "项目周报"
    assert "<mark>邮件备份</mark>" in hit["snippet"]
    assert hit["account_email"] == "a@example.com"


async def test_short_chinese_query_falls_back_to_like(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.search_cached_messages("u1", "会议")
    assert result["mode"] == "like"
    assert result["total"] == 1
    assert result["messages"][0]["subject"] == "会议纪要"


async def test_english_case_insensitive(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.search_cached_messages("u1", "INVOICE")
    assert result["total"] == 1
    assert result["messages"][0]["subject"] == "Invoice October"


async def test_cross_account_search(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.search_cached_messages("u1", "the")
    emails = {m["account_email"] for m in result["messages"]}
    assert "a@example.com" in emails


async def test_account_and_folder_filters(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.search_cached_messages("u1", "规划", account_id="accB")
    assert result["total"] == 1
    result = await fresh_db.search_cached_messages("u1", "规划", account_id="accA")
    assert result["total"] == 0


async def test_date_range_filter(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.search_cached_messages(
        "u1", "invoice", date_from="2026-10-01", date_to="2026-10-31"
    )
    assert result["total"] == 1
    result = await fresh_db.search_cached_messages(
        "u1", "invoice", date_from="2026-11-01"
    )
    assert result["total"] == 0


async def test_index_tracks_update_and_delete(fresh_db):
    await _seed(fresh_db)
    conn = await fresh_db.get_db()
    # 正文更新 -> 新词可搜，旧词消失
    await conn.execute(
        "UPDATE cached_messages SET body_text = ? WHERE id = ?",
        ("改成了全新的归档说明", "accA:INBOX:1"),
    )
    await conn.commit()
    result = await fresh_db.search_cached_messages("u1", "归档说明")
    assert result["total"] == 1
    result = await fresh_db.search_cached_messages("u1", "邮件备份功能")
    assert result["total"] == 0
    # 删除 -> 索引同步移除
    await conn.execute("DELETE FROM cached_messages WHERE id = ?", ("accA:INBOX:1",))
    await conn.commit()
    result = await fresh_db.search_cached_messages("u1", "归档说明")
    assert result["total"] == 0


async def test_empty_query_returns_empty(fresh_db):
    await _seed(fresh_db)
    result = await fresh_db.search_cached_messages("u1", "   ")
    assert result["total"] == 0
    assert result["messages"] == []
