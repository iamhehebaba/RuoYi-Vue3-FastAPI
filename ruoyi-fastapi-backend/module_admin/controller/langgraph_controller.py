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
from utils.langgraph_client import langgraph_client
from utils.log_util import logger
from config.env import RagflowConfig
from module_admin.controller.proxy_controller import ProxyRule, ProxyRuleHandler
from module_admin.service.agent_service import AgentService
"""
基于 URL Path 的权限校验 + Langgraph API 转发

在一个统一的代理入口下：
1) 按不同 URL 前缀进行权限检查（可配置权限校验，支持严格模式）；
2) 通过 RagflowClient 转发请求到 Langgraph 服务，自动处理认证、注册、token刷新；
3) 最大化复用项目现有的 CheckUserInterfaceAuth。

使用方式：
- 可以根据需要调整 RULES 中的 path_prefix、权限设置。
"""


# 根据 model_controller.py 中的API配置转发规则
LANGGRAPH_RULES: List[ProxyRule] = [
    # langgraph apis
    {
        "path_prefix": "\/assistants\/search",
        "method": "POST",
        "straight_forward": True,
        "permission": ["system:role:add", "system:role:edit"],
        "perm_strict": False,
        "post_processor": AgentService.post_process_agent_search,
        "description": "search assistants"
    },       
    {
        "path_prefix": "\/threads",
        "method": "POST",
        "straight_forward": True,
        "description": "create a thread"
    },
    {
        "path_prefix": "\/threads/search",
        "method": "POST",
        "straight_forward": True,
        "description": "search threads"
    },    
    {
        "path_prefix": "\/threads\/.*\/runs",
        "method": "POST",
        "straight_forward": True,
        "description": "create a run"
    },   
    {
        "path_prefix": "\/threads\/.*\/runs\/stream",
        "method": "POST",
        "straight_forward": True,
        "description": "create a run in stream mode"
    },   
    {
        "path_prefix": "\/threads\/.*\/runs\/.*",
        "method": "GET",
        "straight_forward": True,
        "description": "get a run, including its status"
    },   
    {
        "path_prefix": "\/threads\/.*\/runs\/.*/join",
        "method": "GET",
        "straight_forward": True,
        "description": "wait and get a run's result"
    },       
    {
        "path_prefix": "\/threads\/.*\/history",
        "method": "POST",
        "straight_forward": True,
        "description": "wait and get a run's result"
    },           
]    

langgraphController = APIRouter(prefix="/proxy/langgraph", tags=["Langgraph API"])
langgraph_rule_handler = ProxyRuleHandler(LANGGRAPH_RULES, langgraph_client)



@langgraphController.api_route(
    "/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def langgraph_proxy_all(
    full_path: str, 
    request: Request,     
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),    
    data_scope_sql: str = Depends(GetDataScope('RagflowKb')),
) -> Response:

    response = await langgraph_rule_handler.proxy_rule_executor(full_path, request, query_db, current_user, data_scope_sql)
    return response
