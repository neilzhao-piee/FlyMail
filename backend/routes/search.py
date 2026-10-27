"""全文搜索路由

提供跨账号、跨文件夹的邮件检索：
- FTS5 trifram 索引命中时返回正文片段（<mark> 高亮）
- 索引不可用或查询短于 3 个字符时自动回退 LIKE（保证中文短词可搜）
"""
from fastapi import APIRouter, Query, Request

from db import fts_available, search_cached_messages
from deps import get_uid
from schemas import SearchResponse
from utils.logger import get_logger

logger = get_logger("routes.search")

router = APIRouter(tags=["搜索"])


@router.get("/api/search", response_model=SearchResponse, summary="跨账号跨文件夹全文搜索")
async def search_messages_api(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="搜索关键词，多个词为 AND，可用双引号短语"),
    account_id: str = Query(default="", description="限定账号 ID，空=全部账号"),
    folder: str = Query(default="", description="限定文件夹，空=全部文件夹"),
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=40, ge=1, le=100, description="每页数量"),
    date_from: str = Query(default="", max_length=20, description="起始日期 YYYY-MM-DD（含当天）"),
    date_to: str = Query(default="", max_length=20, description="结束日期 YYYY-MM-DD（含当天）"),
    sort: str = Query(default="date", pattern="^(date|relevance)$", description="排序：date=按时间，relevance=按相关度"),
):
    user_uid = await get_uid(request)
    return await search_cached_messages(
        user_uid,
        q,
        account_id=account_id,
        folder=folder,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )


@router.get("/api/search/status", summary="搜索索引状态")
async def search_status_api():
    """返回全文索引是否可用，便于前端提示"当前是精确检索还是模糊回退"。"""
    return {"fts_enabled": fts_available()}
