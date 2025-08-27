from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import httpx
from fastapi import APIRouter, Depends, Request, Response

from module_admin.aspect.interface_auth import CheckRoleInterfaceAuth, CheckUserInterfaceAuth
from module_admin.service.login_service import LoginService
from module_admin.entity.vo.user_vo import CurrentUserModel


"""
基于 URL Path 的权限校验 + 反向代理转发

在一个统一的代理入口下：
1) 按不同 URL 前缀进行权限检查（可配置权限或角色校验，支持严格模式）；
2) 通过 httpx.AsyncClient 转发原始 HTTP 请求到后端上游服务；
3) 最大化复用项目现有的 CheckUserInterfaceAuth / CheckRoleInterfaceAuth。

使用方式：
- 可以根据需要调整 RULES 中的 path_prefix、upstream 和权限/角色设置。
"""


proxyController = APIRouter(prefix="/proxy")


class ProxyRule(Dict[str, Any]):
    """用于类型提示的规则字典结构"""
    path_prefix: str  # 要匹配的前缀（相对于 /proxy 的子路径，例如 /service-a）
    upstream: str  # 目标上游服务的基础地址，例如 http://127.0.0.1:9000
    strip_prefix: bool  # 是否在转发时去掉匹配前缀
    permission: Optional[Union[str, List[str]]]  # 需要的权限标识（字符串或列表）
    perm_strict: bool  # 权限为列表时是否要求全部满足
    roles: Optional[Union[str, List[str]]]  # 需要的角色标识（字符串或列表）
    role_strict: bool  # 角色为列表时是否要求全部满足


# 根据自身业务场景配置你的路由转发与权限控制规则
RULES: List[ProxyRule] = [
    {
        "path_prefix": "/service-a",
        "upstream": "http://127.0.0.1:9001",  # 示例上游
        "strip_prefix": True,
        "permission": "service:a:proxy",  # 需要具备此权限
        "perm_strict": False,
        "roles": None,
        "role_strict": False,
    },
    {
        "path_prefix": "/service-b/admin",
        "upstream": "http://127.0.0.1:9002/admin",  # 示例上游
        "strip_prefix": True,
        # 需要同时具备列表中的所有权限（perm_strict=True）
        "permission": ["service:b:admin:list", "service:b:admin:edit"],
        "perm_strict": True,
        # 需要具备 admin 角色
        "roles": "admin",
        "role_strict": False,
    },
    {
        "path_prefix": "/langgraph",
        "upstream": "http://127.0.0.1:8000",  #langgraph-api sever, 如果docker化，这里需要是容器名：http://langgraph-api
        "strip_prefix": True,
        "permission": "",  # 需要具备此权限
        "perm_strict": False,
        "roles": None,
        "role_strict": False,
    },    
]


HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}


def _match_rule(sub_path: str) -> Optional[ProxyRule]:
    """
    按最长前缀匹配规则选取转发配置。

    sub_path: 不含 /proxy 前缀的真实子路径，例如 "/service-a/foo/bar"
    """
    best: Optional[ProxyRule] = None
    for rule in RULES:
        prefix = rule["path_prefix"].rstrip("/")
        if not prefix:
            continue
        if sub_path.startswith(prefix + "/") or sub_path == prefix:
            if best is None or len(prefix) > len(best["path_prefix"].rstrip("/")):
                best = rule
    return best


def _build_target_url(rule: ProxyRule, sub_path: str, query_string: str) -> str:
    """
    组合目标上游 URL。
    - 若 strip_prefix=True，则去掉匹配到的 path_prefix 后转发到上游
    - 若 strip_prefix=False，则保留完整 sub_path
    """
    prefix = rule["path_prefix"].rstrip("/")
    if rule.get("strip_prefix", True) and (
        sub_path == prefix or sub_path.startswith(prefix + "/")
    ):
        suffix = sub_path[len(prefix) :] or "/"
    else:
        suffix = sub_path
    base = rule["upstream"].rstrip("/")
    url = f"{base}{suffix}"
    if query_string:
        url = f"{url}?{query_string}"
    return url


async def _require_permission_for_path(
    request: Request,
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
) -> bool:
    """
    动态依赖：基于路径匹配到的规则，复用现有依赖进行权限/角色校验。
    找不到匹配规则时，默认拒绝（抛出 PermissionException）。
    """
    full_path: str = request.path_params.get("full_path", "")
    # sub_path 是相对于 /proxy 的子路径，始终以 "/" 开头
    sub_path = "/" + full_path.lstrip("/")
    rule = _match_rule(sub_path)
    if not rule:
        # 未配置的路径，不允许访问
        # 交给 CheckUserInterfaceAuth 抛出统一的 PermissionException
        CheckUserInterfaceAuth("__proxy:not-allowed__")(current_user)
        return False  # 实际到不了这里

    # 先进行角色校验（若配置了）
    if rule.get("roles") is not None:
        role_checker = CheckRoleInterfaceAuth(rule["roles"], is_strict=rule.get("role_strict", False))
        role_checker(current_user)

    # 再进行权限校验（若配置了）
    if rule.get("permission") is not None:
        perm_checker = CheckUserInterfaceAuth(rule["permission"], is_strict=rule.get("perm_strict", False))
        perm_checker(current_user)

    return True


def _filter_request_headers(headers: Dict[str, str]) -> Dict[str, str]:
    # 复制并移除 hop-by-hop 头与由 httpx 自动处理的头
    new_headers = {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}
    # Host 由 httpx 根据目标 URL 设置，去掉原 Host 避免冲突
    new_headers.pop("host", None)
    return new_headers


def _filter_response_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}


@proxyController.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    dependencies=[Depends(_require_permission_for_path)],
)
async def proxy_all(full_path: str, request: Request) -> Response:
    """
    统一代理入口：匹配 RULES 并转发请求。
    """
    sub_path = "/" + full_path.lstrip("/")
    rule = _match_rule(sub_path)
    # 这里理论上一定能匹配，因为 _require_permission_for_path 已经做过一次匹配与校验
    assert rule is not None

    target_url = _build_target_url(rule, sub_path, request.url.query)

    # 提取请求信息
    method = request.method
    body = await request.body()
    headers = _filter_request_headers(dict(request.headers))

    # 使用 httpx.AsyncClient 转发
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        upstream_resp = await client.request(
            method=method,
            url=target_url,
            content=body if body else None,
            headers=headers,
        )

    # 过滤响应头并返回
    resp_headers = _filter_response_headers(dict(upstream_resp.headers))
    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )