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
from module_admin.controller.proxy_controller import ProxyRule, ProxyRuleHandler

"""
基于 URL Path 的权限校验 + Ragflow API 转发

在一个统一的代理入口下：
1) 按不同 URL 前缀进行权限检查（可配置权限校验，支持严格模式）；
2) 通过 RagflowClient 转发请求到 Ragflow 服务，自动处理认证、注册、token刷新；
3) 最大化复用项目现有的 CheckUserInterfaceAuth。

使用方式：
- 可以根据需要调整 RULES 中的 path_prefix、权限设置。
"""




# 根据 model_controller.py 中的API配置转发规则
RAGFLOW_RULES: List[ProxyRule] = [
    # model apis
    {
        "path_prefix": "\/v1\/llm\/factories",
        "method": "GET",
        "permission": "model:model:add",
        "perm_strict": False,
        "description": "list all LLM providers"
    },
    {
        "path_prefix": "\/v1\/llm\/my_llms",
        "method": "GET",
        "permission": ["model:model:add", "model:model:list", "model:model:remove", "model:model:config"],
        "perm_strict": False,  # 非严格模式，满足任一权限即可
        "description": "list my currently added LLMs"
    },
    {
        "path_prefix": "\/v1\/llm\/delete_llm",
        "method": "POST",
        "permission": "model:model:remove",
        "perm_strict": False,
        "description": "delete one LLM from my currently added LLMs"
    },
    {
        "path_prefix": "\/v1\/llm\/delete_factory",
        "method": "POST",
        "permission": "model:model:remove",
        "perm_strict": False,
        "description": "delete one LLM factory(all LLMs under this factory will be deleted)"
    },    
    {
        "path_prefix": "\/v1\/llm\/set_api_key",
        "method": "POST",
        "permission": "model:model:add",
        "perm_strict": False,
        "description": "set the API key to add new LLM"
    },
    {
        "path_prefix": "\/v1\/llm\/list",
        "method": "GET",
        "description": "list all LLMs for setting default LLMs"
    },    
    {
        "path_prefix": "\/v1\/llm\/add_llm",
        "method": "POST",
        "permission": "model:model:add",
        "perm_strict": False,
        "description": "add a new LLM(for example, by Ollama reference engine)"
    },

    # kb apis
    {
        "path_prefix": "\/v1\/kb\/list",   # anyone can list his own kb
        "method": "POST",
        "descriptioni": "list all kbs for current user based on his role assignments",
        "post_processor": [RagflowKbService.filter_ragflow_kb_by_permission],
    },    
    {
        "path_prefix": "\/v1\/kb\/create",
        "method": "POST",
        "permission": "kb:kb:add",      # must have the "add kb" permission
        "description": "create a new kb",
        "post_processor": [RagflowKbService.post_process_create_kb],
    },
    {
        "path_prefix": "\/v1\/kb\/update",
        "method": "POST",
        "permission": ["kb:kb:edit", "kb:kb:add"],      # must have the "edit kb" or "add kb" permission
        "perm_strict": False,
        "description": "update a kb configuration",
        "pre_processor": [RagflowKbService.check_ragflow_kb_permission],
    },
    {
        "path_prefix": "\/v1\/kb\/rm",
        "method": "POST",
        "permission": "kb:kb:rm",      # must have the "rm kb" permission
        "perm_strict": False,
        "description": "remove a kb",
        "pre_processor": [RagflowKbService.check_ragflow_kb_permission],
    },    

    # document apis
    {
        "path_prefix": "\/v1\/document\/list",
        "method": "GET",
        "permission": ["kb:doc:list"],
        "description": "list documents in a kb",
        "pre_processor": [RagflowKbService.check_ragflow_kb_permission],
        "straight_forward": True,
    },

    {
        "path_prefix": "\/v1\/document\/upload",
        "method": "POST",
        "permission": ["kb:doc:add"],
        "description": "upload a document to a kb",
        "pre_processor": [RagflowKbService.check_ragflow_kb_permission],
        "straight_forward": True,
    },
    {
        "path_prefix": "\/v1\/document\/run",
        "method": "POST",
        "permission": ["kb:doc:add"],
        "description": "parse documents",
        "straight_forward": True,
    },
    {
        "path_prefix": "\/v1\/document\/rm",
        "method": "POST",
        "permission": ["kb:doc:delete"],
        "description": "remove documents",
        "straight_forward": True,
    },
    {
        "path_prefix": "\/v1\/document\/rename",
        "method": "POST",
        "permission": ["kb:doc:add"],
        "description": "rename documents",
        "straight_forward": True,
    },    
    
    

    # tenant apis
    {
        "path_prefix": "\/v1\/tenant\/list",   # anyone can list his tenants(one user may belong to multiple tenants)
        "method": "GET",
        "description": "list all tenants for current user"
    },

    # user apis
    {
        "path_prefix": "\/v1\/user\/set_tenant_info",
        "method": "POST",
        "permission": "model:model:config",
        "description": "set the default LLMs for current tenant"
    },    
    {
        "path_prefix": "\/v1\/user\/tenant_info",
        "method": "GET",
        "permission": ["model:model:add", "model:model:list", "model:model:remove", "model:model:config"],
        "description": "list all default LLMs for current tenant"
    },    

    # any other apis
    {
        "path_prefix": "*",
        "method": "*",
        "straight_forward": True,
        "description": "any other ragflow apis"
    }
]    

ragflowController = APIRouter(prefix="/ragflow", tags=["Ragflow模型管理"])
ragflow_rule_handler = ProxyRuleHandler(RAGFLOW_RULES, ragflow_client)


@ragflowController.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def ragflow_proxy_all(
    full_path: str, 
    request: Request,     
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),    
    data_scope_sql: str = Depends(GetDataScope('RagflowKb')),
) -> Response:

    response = await ragflow_rule_handler.proxy_rule_executor(full_path, request, query_db, current_user, data_scope_sql)
    return response
