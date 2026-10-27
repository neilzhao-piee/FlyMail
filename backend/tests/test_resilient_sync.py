"""同步健壮性测试：单封 FETCH 失败不拖垮整批，分页失败回退 UID 分批。"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("FLYMAIL_DATA_DIR", tempfile.mkdtemp(prefix="flymail-test-sync-"))

import pytest  # noqa: E402

import db as dbmod  # noqa: E402
import services.mail_cache as mc  # noqa: E402
from models import Account  # noqa: E402
from providers.base import Message  # noqa: E402


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


def _account() -> Account:
    return Account(id="acc1", user_uid="u1", email="a@example.com", provider="custom")


def _msg(uid: int, folder: str = "INBOX") -> Message:
    return Message(
        id=str(uid), uid=uid, subject=f"subject-{uid}", from_addr="x@example.com",
        to_addr="me@example.com", date="2026-10-01T10:00:00Z", folder=folder,
    )


class FakeReceiver:
    """批量 FETCH 只要包含坏 UID 就整批抛错，模拟 BODYSTRUCTURE 解析失败。"""

    def __init__(self, bad_uids: set[int]):
        self.bad_uids = set(bad_uids)
        self.batch_calls: list[list[int]] = []
        self.single_calls: list[int] = []

    async def fetch_messages_by_uids(self, folder, uids):
        uids = [int(u) for u in uids]
        self.batch_calls.append(list(uids))
        if any(u in self.bad_uids for u in uids):
            raise ValueError('imapkit: in body-type-1part: imapwire: expected "(", got "N"')
        return [_msg(u, folder) for u in uids]


async def test_resilient_fetch_keeps_good_messages(fresh_db):
    receiver = FakeReceiver({2})
    messages = await mc._fetch_messages_resilient(receiver, _account(), "INBOX", [1, 2, 3])
    assert sorted(m.uid for m in messages) == [1, 3]
    assert await dbmod.count_failed_messages("acc1", "INBOX") == 1
    skip = await dbmod.get_failed_uids("acc1", "INBOX", min_attempts=mc.MAX_FETCH_ATTEMPTS)
    assert skip == set()  # 只失败 1 次，还没到跳过阈值


async def test_failed_uid_skipped_after_max_attempts(fresh_db):
    receiver = FakeReceiver({2})
    account = _account()
    for _ in range(mc.MAX_FETCH_ATTEMPTS):
        await mc._fetch_messages_resilient(receiver, account, "INBOX", [1, 2, 3])
    skip = await dbmod.get_failed_uids("acc1", "INBOX", min_attempts=mc.MAX_FETCH_ATTEMPTS)
    assert skip == {2}
    # 再同步时 UID 2 不应再被尝试
    before = sum(1 for uid in receiver.single_calls if uid == 2)
    await mc._fetch_messages_resilient(receiver, account, "INBOX", [1, 2, 3])
    after = sum(1 for uid in receiver.single_calls if uid == 2)
    assert after == before


async def test_page_failure_falls_back_to_uid_batches(fresh_db):
    class PageFailReceiver(FakeReceiver):
        async def fetch_messages(self, folder, page=1, page_size=50):
            raise ValueError("page 31 parse error")

        async def fetch_new_message_uids(self, folder, since_uid=0):
            return [10, 11]

        async def fetch_folder_counts(self, folders):
            return {f: {"total": 2, "unread": 0} for f in folders}

        async def fetch_unseen_uids(self, folder):
            return []

    receiver = PageFailReceiver(set())
    messages, total, unread = await mc._fetch_all_message_pages(receiver, _account(), "INBOX")
    assert total == 2
    assert sorted(m.uid for m in messages) == [10, 11]
