"""账号级「全部已读」测试：遍历所有文件夹、跳过 Gmail「所有邮件」、同步缓存与未读计数。"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("FLYMAIL_DATA_DIR", tempfile.mkdtemp(prefix="flymail-test-mark-"))

import pytest  # noqa: E402

import db as dbmod  # noqa: E402
import routes.messages as rm  # noqa: E402
from models import Account, CachedMessage  # noqa: E402
from providers.base import Folder  # noqa: E402


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


class FakeReceiver:
    def __init__(self):
        self.seen_calls = []

    async def fetch_folders(self):
        return [
            Folder(name="收件箱", path="INBOX"),
            Folder(name="所有邮件", path="[Gmail]/All Mail"),
            Folder(name="垃圾邮件", path="[Gmail]/Spam"),
        ]

    async def fetch_unseen_uids(self, folder):
        return {"INBOX": [1, 2], "[Gmail]/Spam": [3]}.get(folder, [])

    async def mark_as_read_batch(self, uids, folder):
        self.seen_calls.append((folder, list(uids)))
        return len(uids)

    async def disconnect(self):
        pass


async def _seed(db):
    conn = await db.get_db()
    await conn.execute(
        "INSERT INTO accounts (id, user_uid, email, provider) VALUES ('acc1','default','a@example.com','custom')"
    )
    await conn.commit()
    msgs = []
    for uid, folder in ((1, "INBOX"), (2, "INBOX"), (3, "[Gmail]/Spam")):
        msgs.append(CachedMessage(
            id=f"acc1:{folder}:{uid}", account_id="acc1", user_uid="default",
            uid=uid, folder=folder, subject=f"s{uid}", from_addr="x@example.com",
            to_addr="a@example.com", date="2026-10-01T10:00:00Z",
        ))
    await db.upsert_cached_messages(msgs)
    await db.upsert_folder_stats("acc1", "INBOX", 2, 2)
    await db.upsert_folder_stats("acc1", "[Gmail]/Spam", 1, 1)


async def test_mark_account_all_read(fresh_db, monkeypatch):
    await _seed(fresh_db)
    fake = FakeReceiver()
    monkeypatch.setattr(rm, "_ensure_gmail_token", lambda acc: _async_value(object()))
    monkeypatch.setattr(rm, "_get_cached_receiver", lambda acc, cred: _async_value(fake))
    monkeypatch.setattr(rm, "_safe_disconnect", lambda recv: _async_value(None))

    account = Account(id="acc1", user_uid="default", email="a@example.com", provider="custom")
    result = await rm._mark_account_all_read(account, "default")

    assert result["total_marked"] == 3
    # Gmail「所有邮件」是虚拟文件夹，必须跳过
    assert all(f["folder"] != "[Gmail]/All Mail" for f in result["folders"])
    assert fake.seen_calls == [("INBOX", ["1", "2"]), ("[Gmail]/Spam", ["3"])]

    # 缓存全部置为已读，未读计数清零
    conn = await fresh_db.get_db()
    rows = await (await conn.execute("SELECT COUNT(*) FROM cached_messages WHERE is_read=0")).fetchone()
    assert rows[0] == 0
    assert (await fresh_db.get_folder_stats("acc1", "INBOX"))["unread_count"] == 0


async def _async_value(v):
    return v
