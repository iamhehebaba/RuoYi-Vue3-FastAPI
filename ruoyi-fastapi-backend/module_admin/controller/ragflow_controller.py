from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from module_admin.aspect.data_scope import GetDataScope

from config.get_db import get_db
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.service.login_service import LoginService
from module_admin.service.ragflow_kb_service import RagflowKbService
from module_admin.entity.vo.user_vo import CurrentUserModel
from utils.ragflow_util import ragflow_client
from utils.log_util import logger
from config.env import RagflowConfig


"""
基于 URL Path 的权限校验 + Ragflow API 转发

在一个统一的代理入口下：
1) 按不同 URL 前缀进行权限检查（可配置权限校验，支持严格模式）；
2) 通过 RagflowClient 转发请求到 Ragflow 服务，自动处理认证、注册、token刷新；
3) 最大化复用项目现有的 CheckUserInterfaceAuth。

使用方式：
- 可以根据需要调整 RULES 中的 path_prefix、权限设置。
"""


ragflowController = APIRouter(prefix="/ragflow", tags=["Ragflow模型管理"])


class RagflowModelRule(Dict[str, Any]):
    """用于类型提示的规则字典结构"""
    path_prefix: str  # 要匹配的前缀（相对于 /ragflow_model 的子路径，例如 /v1/llm/factories）
    method: str  # HTTP方法
    permission: Optional[Union[str, List[str]]]  # 需要的权限标识（字符串或列表）
    perm_strict: Optional[bool]  # 权限为列表时是否要求全部满足
    upstream_path: Optional[str]  # 如果有值，则使用此路径替换path_prefix的值
    description: Optional[str]
    post_processor: Optional[Callable[[str, Request, AsyncSession, CurrentUserModel, str, Any], Awaitable[Any]]]  # 后处理函数


# 根据 model_controller.py 中的API配置转发规则
RULES: List[RagflowModelRule] = [
    {
        "path_prefix": "/v1/llm/factories",
        "method": "GET",
        "permission": "model:model:add",
        "perm_strict": False,
        "description": "list all LLM providers"
    },
    {
        "path_prefix": "/v1/llm/my_llms",
        "method": "GET",
        "permission": ["model:model:add", "model:model:list", "model:model:remove", "model:model:config"],
        "perm_strict": False,  # 非严格模式，满足任一权限即可
        "description": "list my currently added LLMs"
    },
    {
        "path_prefix": "/v1/llm/delete_llm",
        "method": "POST",
        "permission": "model:model:remove",
        "perm_strict": False,
        "description": "delete one LLM from my currently added LLMs"
    },
    {
        "path_prefix": "/v1/llm/set_api_key",
        "method": "POST",
        "permission": "model:model:add",
        "perm_strict": False,
        "description": "set the API key to add new LLM"
    },
    {
        "path_prefix": "/v1/llm/list",
        "method": "GET",
        "description": "list all LLMs for setting default LLMs"
    },    

    # kb apis
    {
        "path_prefix": "/v1/kb/list",   # anyone can list his own kb
        "method": "POST",
        "descriptioni": "list all kbs for current user based on his role assignments",
        "post_processor": RagflowKbService.filter_ragflow_kb_by_permission
    },    
    {
        "path_prefix": "/v1/kb/create",
        "method": "POST",
        "permission": "kb:kb:add",      # must have the "add kb" permission
        "description": "create a new kb"
    },

    # tenant apis
    {
        "path_prefix": "/v1/tenant/list",   # anyone can list his tenants(one user may belong to multiple tenants)
        "method": "GET",
        "description": "list all tenants for current user"
    },

    # user apis
    {
        "path_prefix": "/v1/user/set_tenant_info",
        "method": "POST",
        "permission": "model:model:config",
        "description": "set the default LLMs for current tenant"
    },    
    {
        "path_prefix": "/v1/user/tenant_info",
        "method": "GET",
        "permission": ["model:model:add", "model:model:list", "model:model:remove", "model:model:config"],
        "description": "list all default LLMs for current tenant"
    },    
]    



def _match_rule(sub_path: str, method: str) -> Optional[RagflowModelRule]:
    """
    按最长前缀匹配规则选取转发配置，method必须严格匹配。

    sub_path: 不含 /ragflow_model 前缀的真实子路径，例如 "/v1/llm/factories"
    method: HTTP方法，例如 "GET", "POST"
    """
    best: Optional[RagflowModelRule] = None
    for rule in RULES:
        # method必须严格匹配
        if rule["method"].upper() != method.upper():
            continue
            
        prefix = rule["path_prefix"].rstrip("/")
        if not prefix:
            continue
            
        # 检查路径是否匹配（精确匹配或前缀匹配）
        if sub_path.startswith(prefix + "/") or sub_path == prefix:
            # 按最长前缀匹配
            if best is None or len(prefix) > len(best["path_prefix"].rstrip("/")):
                best = rule
    return best


async def _require_permission_for_path(
    request: Request,
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
) -> bool:
    """
    动态依赖：基于路径匹配到的规则，复用现有依赖进行权限校验。
    找不到匹配规则时，默认拒绝（抛出 PermissionException）。
    """
    full_path: str = request.path_params.get("full_path", "")
    # sub_path 是相对于 /ragflow_model 的子路径，始终以 "/" 开头
    sub_path = "/" + full_path.lstrip("/")
    method = request.method
    
    rule = _match_rule(sub_path, method)
    if not rule:
        # 未配置的路径，不允许访问
        # 交给 CheckUserInterfaceAuth 抛出统一的 PermissionException
        CheckUserInterfaceAuth("__ragflow_model:not-allowed__")(current_user)
        return False  # 实际到不了这里

    # 进行权限校验（若配置了）
    if rule.get("permission") is not None:
        perm_checker = CheckUserInterfaceAuth(rule["permission"], is_strict=rule.get("perm_strict", False))
        perm_checker(current_user)

    return True


@ragflowController.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    dependencies=[Depends(_require_permission_for_path)],
)
async def ragflow_model_proxy_all(
    full_path: str, 
    request: Request,     
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),    
    data_scope_sql: str = Depends(GetDataScope('RagflowKb')),
) -> Response:
    """
    统一Ragflow模型API代理入口：匹配 RULES 并转发请求。
    """
    sub_path = "/" + full_path.lstrip("/")
    method = request.method
    rule = _match_rule(sub_path, method)
    # 这里理论上一定能匹配，因为 _require_permission_for_path 已经做过一次匹配与校验
    assert rule is not None

    try:
        # 确定实际转发的路径
        actual_path = sub_path
        if rule.get("upstream_path"):
            actual_path = rule["upstream_path"]
        
        # 提取请求信息
        body = await request.body()
        query_params = dict(request.query_params)
        
        # 准备请求参数
        kwargs = {}
        if query_params:
            kwargs['params'] = query_params
        if body:
            try:
                import json
                kwargs['json'] = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                kwargs['data'] = body
        
        # 使用 RagflowClient 转发请求
        if method.upper() == 'GET':
            response_data = await ragflow_client.get(actual_path, **kwargs)
        elif method.upper() == 'POST':
            response_data = await ragflow_client.post(actual_path, **kwargs)
        elif method.upper() == 'PUT':
            response_data = await ragflow_client.put(actual_path, **kwargs)
        elif method.upper() == 'DELETE':
            response_data = await ragflow_client.delete(actual_path, **kwargs)
        else:
            # 其他方法暂不支持
            return JSONResponse(
                status_code=405,
                content={"code": 405, "message": f"Method {method} not allowed"}
            )
        
        logger.info(f"Ragflow API {method} {actual_path} 调用成功")
        
        # 如果配置了后处理函数，则调用进行后处理
        if rule.get("post_processor"):
            response_data = await rule["post_processor"](
                full_path, request, query_db, current_user, data_scope_sql, response_data
            )
        
        # 返回响应
        return JSONResponse(
            status_code=200,
            content=response_data
        )
        
    except Exception as e:
        logger.error(f"Ragflow API {method} {actual_path} 调用失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"Ragflow API调用失败: {str(e)}"}
        )