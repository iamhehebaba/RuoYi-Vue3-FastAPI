import os
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from loguru import logger
from fastapi import Request
import requests

from config.get_db import get_db

class LanggraphApiClient:
    """
    Langgraph API客户端，用于统一处理对langgraph-api的HTTP请求
    """
    
    def __init__(self):
        self.base_url = os.getenv('LANGGRAPH_API_URL', 'http://localhost:8000')
        self.timeout = 30.0
        self.headers = {"Content-Type": "application/json"}
        self.session = requests.Session()
        self.session.timeout = 30        
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送GET请求
        
        :param endpoint: API端点路径
        :param kwargs: 其他请求参数
        :return: API响应数据
        """
        url = f"{self.base_url}{endpoint}"
        return await self._make_request("GET", url, **kwargs)
    
    async def post(self, endpoint: str, json_data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        发送POST请求
        
        :param endpoint: API端点路径
        :param json_data: 请求体JSON数据
        :param kwargs: 其他请求参数
        :return: API响应数据
        """
        url = f"{self.base_url}{endpoint}"
        return await self._make_request("POST", url, json=json_data, **kwargs)
    
    async def post_stream(self, endpoint: str, json_data: Optional[Dict] = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        发送POST流式请求
        
        :param endpoint: API端点路径
        :param json_data: 请求体JSON数据
        :param kwargs: 其他请求参数
        :return: 异步生成器，逐行yield流式响应数据
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 合并默认headers和传入的headers
                request_headers = {**self.headers}
                if 'headers' in kwargs:
                    request_headers.update(kwargs.pop('headers'))
                
                # 设置流式请求的Accept头
                request_headers["Accept"] = "text/event-stream"
                
                async with client.stream(
                    method="POST",
                    url=url,
                    headers=request_headers,
                    json=json_data,
                    **kwargs
                ) as response:
                    if response.status_code != 200:
                        logger.error(f"调用langgraph_api流式请求失败: {response.status_code} - {await response.aread()}")
                        raise Exception(f"调用langgraph_api流式请求失败: {response.status_code}")
                    
                    async for chunk in response.aiter_text():
                        if chunk.strip():  # 过滤空行
                            yield chunk
                            
        except httpx.TimeoutException as e:
            logger.error("调用langgraph_api流式请求超时")
            raise e
        except httpx.RequestError as e:
            logger.error(f"调用langgraph_api流式请求错误: {e}")
            raise e
        except Exception as e:
            logger.error(f"调用langgraph_api流式请求失败: {e}")
            raise e
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        执行HTTP请求的通用方法
        
        :param method: HTTP方法
        :param url: 完整的请求URL
        :param kwargs: 请求参数
        :return: API响应数据
        :raises: httpx.TimeoutException, httpx.RequestError, Exception
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 合并默认headers和传入的headers
                request_headers = {**self.headers}
                if 'headers' in kwargs:
                    request_headers.update(kwargs.pop('headers'))
                
                response = await client.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    **kwargs
                )
                
                if response.status_code != 200:
                    logger.error(f"调用langgraph_api失败: {response.status_code} - {response.text}")
                    raise Exception(f"调用langgraph_api失败: {response.status_code}")
                
                api_response = response.json()
                logger.info(f"langgraph_api响应: {api_response}")
                return api_response
                
        except httpx.TimeoutException as e:
            logger.error("调用langgraph_api超时")
            raise e
        except httpx.RequestError as e:
            logger.error(f"调用langgraph_api请求错误: {e}")
            raise e
        except Exception as e:
            logger.error(f"调用langgraph_api失败: {e}")
            raise e

    async def forward_raw_request(self, request: Request, path: str, body: bytes) -> dict:
        """
        直接转发原始请求到Ragflow服务器，不解析和重构参数
        
        :param path: API路径
        :param method: HTTP方法
        :param query_params: 查询参数字典
        :param body: 原始请求体
        :param headers: 额外的请求头
        :return: 响应数据
        """
        async for db in get_db():        
            try:
                query_params = dict(request.query_params)
                
                # 获取原始请求头（排除一些不需要转发的头）
                original_headers = dict(request.headers)
                # 移除一些不应该转发的头
                headers_to_remove = ['host', 'content-length', 'authorization']
                for header in headers_to_remove:
                    original_headers.pop(header, None)
                
                # 检查是否为form data请求，确保Content-Type头被正确传递
                content_type = request.headers.get('content-type', '')
                if content_type:
                    # 保留Content-Type头以支持form data转发
                    original_headers['content-type'] = content_type

                # 设置认证头
                
                # 构建完整URL
                url = f"{self.base_url}{path}"
                
                # 准备请求参数
                kwargs = {
                    'headers': original_headers,
                    'timeout': 30
                }
                
                # 添加查询参数
                if request.query_params:
                    kwargs['params'] = dict(request.query_params)  
                
                # 添加请求体
                if body:
                    kwargs['data'] = body
                
                # 发送请求
                response = self.session.request(request.method, url, **kwargs)

                api_response = response.json()
                logger.info(f"ragflow 原始请求转发响应: {api_response}")
                return api_response                
                
            except Exception as e:
                logger.error(f"原始请求转发过程中发生错误: {e}")
                raise e            