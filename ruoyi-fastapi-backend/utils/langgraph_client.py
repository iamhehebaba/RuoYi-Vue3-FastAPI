import requests
import base64
import json
from loguru import logger
import asyncio
import re
import httpx
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime

from config.env import LanggraphConfig

class LanggraphClient:
    """
    Langgraph客户端，用于与Langgraph服务器进行交互
    """

    def __init__(self):
        self.base_url = LanggraphConfig.langgraph_api_url
        self.session = requests.Session()
        self.headers = {"Content-Type": "application/json"}
        self.session.timeout = 60 * 6
        
    async def _make_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """
        发送请求到Langgraph服务器
        
        :param method: HTTP方法（GET, POST等）
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        try:

            
            # 设置认证头
            headers = kwargs.get('headers', {})
            kwargs['headers'] = headers
            
            # 构建完整URL
            url = f"{self.base_url}{path}"
            
            # 发送请求
            response = self.session.request(method, url, **kwargs)
            
            api_response = response.json()
            logger.info(f"langgraph 响应: {api_response}")
            return api_response                
            
        except Exception as e:
            logger.error(f"请求过程中发生错误: {e}")
            raise e

    async def get(self, path: str, **kwargs) -> requests.Response:
        """
        发送GET请求
        
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        return await self._make_request('GET', path, **kwargs)

    async def post(self, path: str, **kwargs) -> requests.Response:
        """
        发送POST请求
        
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        return await self._make_request('POST', path, **kwargs)

    async def put(self, path: str, **kwargs) -> requests.Response:
        """
        发送PUT请求
        
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        return await self._make_request('PUT', path, **kwargs)

    async def delete(self, path: str, **kwargs) -> requests.Response:
        """
        发送DELETE请求
        
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        return await self._make_request('DELETE', path, **kwargs)

    async def forward_raw_request(self, path: str, method: str, query_params: dict, body: bytes, headers: dict = None) -> dict:
        """
        直接转发原始请求到Ragflow服务器，不解析和重构参数
        
        :param path: API路径
        :param method: HTTP方法
        :param query_params: 查询参数字典
        :param body: 原始请求体
        :param headers: 额外的请求头
        :return: 响应数据
        """
        try:
            request_headers = headers.copy() if headers else {}
            
            # 构建完整URL
            url = f"{self.base_url}{path}"
            
            # 准备请求参数
            kwargs = {
                'headers': request_headers,
                'timeout': self.session.timeout
            }
            
            # 添加查询参数
            if query_params:
                kwargs['params'] = query_params
            
            # 添加请求体
            if body:
                kwargs['data'] = body
            
            # 发送请求
            response = self.session.request(method.upper(), url, **kwargs)
            
            if response.status_code < 400 and response.status_code != 204:
                api_response = response.json()
                logger.info(f"langgraph 原始请求转发响应: {api_response}")
                return api_response                
            else:
                return response
        except Exception as e:
            logger.error(f"langgraph 原始请求转发过程中发生错误: {e}")
            raise e

    async def post_stream(self, path: str, headers: dict = None, body: bytes = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        发送POST流式请求
        
        :param path: API路径
        :param headers: 额外的请求头
        :param body: 原始请求体
        :param kwargs: 其他请求参数
        :return: 异步生成器，逐行yield流式响应数据
        """
        url = f"{self.base_url}{path}"
        
        try:
            async with httpx.AsyncClient(timeout=self.session.timeout) as client:

                request_headers = headers.copy() if headers else {}

                # 合并默认headers和传入的headers
                if 'headers' in kwargs:
                    request_headers.update(kwargs.pop('headers'))
                
                # 设置流式请求的Accept头
                request_headers["Accept"] = "text/event-stream"
                async with client.stream(
                    method="POST",
                    url=url,
                    headers=request_headers,
                    data=body,
                    **kwargs
                ) as response:
                    if response.status_code != 200:
                        logger.error(f"调用langgraph_api流式请求失败: {response.status_code}")
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
    

# 创建全局实例
langgraph_client = LanggraphClient()
