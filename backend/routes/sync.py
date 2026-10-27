"""同步诊断路由

查看同步过程中单封拉取失败的邮件（BODYSTRUCTURE 畸形等），便于运维排查。
"""
from fastapi import APIRouter, Query, Request

from db import list_failed_messages
from deps import get_uid

router = APIRouter(tags=["同步"])


@router.get("/api/sync/failed", summary="列出拉取失败的邮件")
async def failed_messages_api(
    request: Request,
    account_id: str = Query(default="", description="限定账号 ID，空=全部账号"),
    folder: str = Query(default="", description="限定文件夹，空=全部文件夹"),
    limit: int = Query(default=50, ge=1, le=500, description="最多返回条数"),
):
    """返回失败邮件的 UID、错误原因和已重试次数。

    累计失败达到 FLYMAIL_MAX_FETCH_ATTEMPTS（默认 3）次后，同步会跳过这些 UID，
    需要人工处理时可据此定位具体邮件。
    """
    user_uid = await get_uid(request)
    messages = await list_failed_messages(
        user_uid, account_id=account_id, folder=folder, limit=limit
    )
    return {"messages": messages, "count": len(messages)}
