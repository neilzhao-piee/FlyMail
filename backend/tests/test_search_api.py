"""搜索 API 层测试：响应模型、用户隔离、参数透传。"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("FLYMAIL_DATA_DIR", tempfile.mkdtemp(prefix="flymail-test-api-"))

import pytest  # noqa: E402
from starlette.requests import Request  # noqa: E402

import db as dbmod  # noqa: E402
from models import CachedMessage  # noqa: E402
from routes.search import search_messages_api  # noqa: E402
from schemas import SearchResponse  # noqa: E402


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


def _request(user_uid: str) -> Request:
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/api/search",
        "headers": [(b"x-trim-userid", user_uid.encode())],
    })


def _msg(uid: int, subject: str, body: str, user_uid: str = "u1") -> CachedMessage:
    account_id = f"acc-{user_uid}"
    return CachedMessage(
        id=f"{account_id}:INBOX:{uid}",
        account_id=account_id,
        user_uid=user_uid,
        uid=uid,
        folder="INBOX",
        subject=subject,
        from_addr="alice@example.com",
        to_addr="me@example.com",
        date="2026-10-01T10:00:00Z",
        body_text=body,
        cached_at=1.0,
    )


async def _seed(db) -> None:
    conn = await db.get_db()
    for account_id, user_uid, email in (("acc-u1", "u1", "u1@example.com"), ("acc-u2", "u2", "u2@example.com")):
        await conn.execute(
            "INSERT INTO accounts (id, user_uid, email, provider) VALUES (?, ?, ?, ?)",
            (account_id, user_uid, email, "custom"),
        )
    await conn.commit()
    await db.upsert_cached_messages([
        _msg(1, "项目周报", "本周完成了邮件备份功能"),
        _msg(2, "别人的邮件", "u2 的私有内容", user_uid="u2"),
    ])


async def test_api_returns_valid_model_and_respects_user(fresh_db):
    await _seed(fresh_db)
    result = await search_messages_api(
        request=_request("u1"), q="邮件备份", account_id="", folder="",
        page=1, page_size=40, date_from="", date_to="", sort="date",
    )
    parsed = SearchResponse.model_validate(result)
    assert parsed.total == 1
    assert parsed.mode == "fts"
    assert parsed.messages[0].subject == "项目周报"
    # 用户隔离：u2 的邮件不应出现在 u1 的结果里
    assert all(m.account_email == "u1@example.com" for m in parsed.messages)


async def test_api_status_endpoint(fresh_db):
    from routes.search import search_status_api

    status = await search_status_api()
    assert status["fts_enabled"] is True
