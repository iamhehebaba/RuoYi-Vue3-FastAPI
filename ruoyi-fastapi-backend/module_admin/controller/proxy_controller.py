import re
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Request, Response
from requests.models import Response as RequestsResponse

from fastapi.responses import JSONResponse, StreamingResponse
from module_admin.aspect.data_scope import GetDataScope

from config.get_db import get_db
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.service.login_service import LoginService
from module_admin.service.ragflow_kb_service import RagflowKbService
from module_admin.entity.vo.user_vo import CurrentUserModel
from utils.ragflow_util import ragflow_client
from utils.log_util import logger
from config.env import RagflowConfig

class ProxyRule(Dict[str, Any]):
    """用于类型提示的规则字典结构"""
    path_prefix: str  # 要匹配的前缀（相对于 /ragflow_model 的子路径，例如 /v1/llm/factories）
    method: str  # HTTP方法
    straight_forward: Optional[bool] = False  # 是否直接转发而没有任何分析处理
    stream_mode: Optional[bool] = False # 是否以流模式转发
    permission: Optional[Union[str, List[str]]]  # 需要的权限标识（字符串或列表）
    perm_strict: Optional[bool] = False # 权限为列表时是否要求全部满足
    upstream_path: Optional[str]  # 如果有值，则使用此路径替换path_prefix的值
    description: Optional[str] # 描述信息
    pre_processor: Optional[List[Callable[[str, Request, AsyncSession, CurrentUserModel, str, Any], Awaitable[Any]]]]  # 前处理函数
    post_processor: Optional[List[Callable[[str, Request, AsyncSession, CurrentUserModel, str, Any], Awaitable[Any]]]]  # 后处理函数


async def immediate_stream_wrapper(stream_generator: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """
    立即刷新的流式包装器，确保每个chunk都能立即发送给前端
    
    这个包装器解决了FastAPI StreamingResponse的内部缓冲延迟问题：
    1. 在每次yield后添加微小延迟，强制刷新内部缓冲区
    2. 确保第一个chunk能够立即发送，而不是等待更多数据
    3. 保持流式传输的实时性
    """
    logger.info("开始使用立即刷新流式包装器")
    
    first_chunk = True
    async for chunk in stream_generator:
        if chunk and chunk.strip():
            if first_chunk:
                logger.info("发送第一个流式chunk，启用立即刷新模式")
                first_chunk = False
            
            # 立即yield chunk
            yield chunk
            
            # 添加微小的异步延迟来强制刷新缓冲区
            # 这个延迟非常小（1ms），不会影响用户体验，但能确保数据立即发送
            # 让出事件循环，强制 FastAPI/Starlette 的 StreamingResponse 把当前 chunk 从内部缓冲区刷到 TCP 发送缓冲区；
            # 0.001 s 足够短，对吞吐影响可忽略，但能打断默认的“凑够 4 kB 再发”行为，实现首字节低延迟。
            await asyncio.sleep(0.001)
    logger.info("流式包装器处理完成")


class ProxyRuleHandler:
    """
    代理规则处理类，负责根据请求路径和方法匹配规则，以及权限校验。
    """

    def __init__(self, proxy_rules: List[ProxyRule], proxy_client):
        self.proxy_rules = proxy_rules
        self.proxy_client = proxy_client


    def _match_rule(self, sub_path: str, method: str) -> Optional[ProxyRule]:
        """
        按最长正则表达式匹配规则选取转发配置，method必须严格匹配。

        sub_path: 不含 /ragflow_model 前缀的真实子路径，例如 "/v1/llm/factories"
        method: HTTP方法，例如 "GET", "POST"
        """
        best: Optional[ProxyRule] = None
        best_match_length = 0
        
        for rule in self.proxy_rules:
            # method必须严格匹配
            if rule["method"].upper() != method.upper() and rule["method"] != "*":
                continue
                
            path_prefix_pattern = rule["path_prefix"]
            if not path_prefix_pattern:
                continue
                
            try:
                # 使用正则表达式从头开始匹配
                match = re.match(path_prefix_pattern, sub_path)
                if match:
                    # 获取匹配的长度
                    match_length = len(match.group(0))
                    # 选择匹配长度最长的规则
                    if match_length > best_match_length:
                        best = rule
                        best_match_length = match_length
            except re.error:
                # 如果正则表达式有错误，跳过这个规则
                continue
                
        return best


    async def _require_permission_for_path(
        self,
        request: Request,
        current_user: CurrentUserModel,
    ) -> bool:
        """
        动态依赖：基于路径匹配到的规则，复用现有依赖进行权限校验。
        找不到匹配规则时，默认拒绝（抛出 PermissionException）。
        """
        full_path: str = request.path_params.get("full_path", "")
        # sub_path 是相对于 /ragflow_model 的子路径，始终以 "/" 开头
        sub_path = "/" + full_path.lstrip("/")
        method = request.method
        
        rule = self._match_rule(sub_path, method)
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

    async def proxy_rule_executor(
        self,
        full_path: str, 
        request: Request,     
        query_db: AsyncSession = Depends(get_db),
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),    
        data_scope_sql: str = Depends(GetDataScope('RagflowKb')),
    ) -> Response:

        """
        匹配 RULES 并转发请求。
        """

        await self._require_permission_for_path(request, current_user)


        sub_path = "/" + full_path.lstrip("/")
        method = request.method
        rule = self._match_rule(sub_path, method)
        # 这里理论上一定能匹配，因为 _require_permission_for_path 已经做过一次匹配与校验
        assert rule is not None

        # try:
        # 确定实际转发的路径
        actual_path = sub_path
        if rule.get("upstream_path"):
            actual_path = rule["upstream_path"]
        
        body = await request.body()

        if rule.get("pre_processor"):
            for pre_processor in rule["pre_processor"]:
                await pre_processor(
                    full_path, request, query_db, current_user, data_scope_sql, body
                )

        # 获取原始请求头（排除一些不需要转发的头）
        original_headers = dict(request.headers)
        # 移除一些不应该转发的头
        headers_to_remove = ['host', 'content-length', 'authorization']
        for header in headers_to_remove:
            original_headers.pop(header, None)

        # 检查是否为通配符规则，如果是则直接转发原始请求
        if rule.get("straight_forward"):
            if rule.get("stream_mode"):
                # 使用立即刷新包装器包装流式生成器
                stream_generator = self.proxy_client.post_stream(actual_path, original_headers, body)
                wrapped_generator = immediate_stream_wrapper(stream_generator)
                
                # 优化的流式响应头配置，确保立即发送
                optimized_headers = {
                    # 基本流式响应头
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Connection": "keep-alive",
                    
                    # 传输编码优化
                    "Transfer-Encoding": "chunked",
                    "Content-Encoding": "identity",
                    
                    # CORS头
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Methods": "*",
                    
                    # 流式优化头
                    "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
                    "X-Content-Type-Options": "nosniff",
                }
                
                return StreamingResponse(
                    wrapped_generator,
                    media_type="text/event-stream",
                    headers=optimized_headers
                )
            else:
                # 直接转发原始请求，不解析和重构参数        
                query_params = dict(request.query_params)
                

                
                # 检查是否为form data请求，确保Content-Type头被正确传递
                content_type = request.headers.get('content-type', '')
                if content_type:
                    # 保留Content-Type头以支持form data转发
                    original_headers['content-type'] = content_type
                
                response_data = await self.proxy_client.forward_raw_request(
                    actual_path, method, query_params, body, original_headers
                )
        else:
            # 原有的处理逻辑：解析请求参数并重构
            # 提取请求信息
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
                response_data = await self.proxy_client.get(actual_path, **kwargs)
            elif method.upper() == 'POST':
                response_data = await self.proxy_client.post(actual_path, **kwargs)
            elif method.upper() == 'PUT':
                response_data = await self.proxy_client.put(actual_path, **kwargs)  
            elif method.upper() == 'DELETE':
                response_data = await self.proxy_client.delete(actual_path, **kwargs)
            else:
                # 其他方法暂不支持
                return JSONResponse(
                    status_code=405,
                    content={"code": 405, "message": f"Method {method} not allowed"}
                )
        
        logger.info(f"Ragflow API {method} {actual_path} 调用成功")
        
        # 如果配置了后处理函数，则调用进行后处理
        if rule.get("post_processor"):
            for post_processor in rule["post_processor"]:
                response_data = await post_processor(
                    full_path, request, query_db, current_user, data_scope_sql, response_data
                )
        
        # 
        # todo: return the response directly, not depending on the type again
        if isinstance(response_data, RequestsResponse):
            return response_data
        else:
            return JSONResponse(
                status_code=200,
                content=response_data
            )