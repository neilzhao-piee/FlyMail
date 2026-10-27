"""国内常见邮箱服务商预设（自定义 IMAP/SMTP 的便捷入口）。

这些服务商都使用「授权码」登录标准 IMAP/SMTP，不需要 OAuth。
添加账号时若邮箱域名命中预设，前端可只填邮箱 + 授权码，服务器参数自动补全。
"""
from typing import Optional

# 域名 → IMAP/SMTP 参数（端口/加密方式均为服务商公开推荐值）
PRESETS: dict[str, dict] = {
    "139.com": {
        "label": "中国移动 139 邮箱",
        "imap_host": "imap.139.com", "imap_port": 993, "imap_ssl": "ssl",
        "smtp_host": "smtp.139.com", "smtp_port": 465, "smtp_ssl": "ssl",
    },
    "189.cn": {
        "label": "中国电信 189 邮箱",
        "imap_host": "imap.189.cn", "imap_port": 993, "imap_ssl": "ssl",
        "smtp_host": "smtp.189.cn", "smtp_port": 465, "smtp_ssl": "ssl",
    },
    "sohu.com": {
        "label": "搜狐邮箱",
        "imap_host": "imap.sohu.com", "imap_port": 993, "imap_ssl": "ssl",
        "smtp_host": "smtp.sohu.com", "smtp_port": 465, "smtp_ssl": "ssl",
    },
    "aliyun.com": {
        "label": "阿里云邮箱",
        "imap_host": "imap.aliyun.com", "imap_port": 993, "imap_ssl": "ssl",
        "smtp_host": "smtp.aliyun.com", "smtp_port": 465, "smtp_ssl": "ssl",
    },
}


def detect_preset(email: str) -> Optional[dict]:
    """按域名匹配预设，返回 {label, imap_host, ...} 或 None。"""
    domain = (email or "").rsplit("@", 1)[-1].strip().lower()
    if not domain:
        return None
    preset = PRESETS.get(domain)
    return dict(preset) if preset else None


def list_presets() -> list[dict]:
    """返回可用的预设列表（供前端提示）。"""
    return [{"domain": domain, **cfg} for domain, cfg in sorted(PRESETS.items())]
