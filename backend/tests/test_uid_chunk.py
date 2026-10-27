"""UID 列表分段拉取测试：18 万封不再触发 1MB 响应限制。"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("FLYMAIL_DATA_DIR", tempfile.mkdtemp(prefix="flymail-test-uid-"))

from providers.base_imap import BaseIMAPReceiver  # noqa: E402


class FakeConn:
    """模拟 imaplib：UID SEARCH 每次最多返回 chunk 个 UID。"""

    def __init__(self, uidnext):
        self.uidnext = uidnext
        self.searches = []

    def select(self, folder, readonly=True):
        return ("OK", [b"1"])

    def status(self, folder, what):
        return ("OK", [f'"INBOX" (UIDNEXT {self.uidnext})'.encode()])

    def uid(self, cmd, *args):
        assert cmd == "SEARCH"
        spec = args[-1]
        start, end = spec.split("UID ")[1].split(":") if "UID " in spec else (spec.split(":")[0], spec.split(":")[1])
        lo, hi = int(start), int(end)
        uids = [str(u) for u in range(lo, min(hi, self.uidnext - 1) + 1)]
        self.searches.append((lo, hi))
        return ("OK", [(" ".join(uids)).encode()]) if uids else ("OK", [b""])


class DummyReceiver(BaseIMAPReceiver):
    """绕过抽象方法，只测 UID 分段逻辑。"""

    async def connect(self, credentials):  # pragma: no cover
        pass

    async def disconnect(self):  # pragma: no cover
        pass

    async def fetch_folders(self):  # pragma: no cover
        return []

    async def fetch_messages(self, folder, page=1, page_size=50):  # pragma: no cover
        raise NotImplementedError


def _receiver(uidnext):
    r = object.__new__(DummyReceiver)
    r._conn = FakeConn(uidnext)
    return r


def _norm(folder):
    return folder


def test_full_uid_list_is_chunked():
    r = _receiver(uidnext=184588)
    r._normalize_folder = _norm
    r._quote_mailbox = lambda f: f
    uids = r._fetch_new_uids_sync("INBOX", 0)
    assert len(uids) == 184587
    assert uids[0] == 1 and uids[-1] == 184587
    # 每个区间不超过 chunk 大小
    assert all(hi - lo + 1 <= BaseIMAPReceiver.UID_SEARCH_CHUNK for lo, hi in r._conn.searches)
    assert len(r._conn.searches) >= 10


def test_incremental_since_uid():
    r = _receiver(uidnext=1001)
    r._normalize_folder = _norm
    r._quote_mailbox = lambda f: f
    uids = r._fetch_new_uids_sync("INBOX", 990)
    assert uids == list(range(991, 1001))
