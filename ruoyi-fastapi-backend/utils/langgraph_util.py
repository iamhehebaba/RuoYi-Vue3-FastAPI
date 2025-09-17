import os
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from loguru import logger


class LanggraphApiClient:
    """
    Langgraph API客户端，用于统一处理对langgraph-api的HTTP请求
    """
    
    def __init__(self):
        self.base_url = os.getenv('LANGGRAPH_API_URL', 'http://localhost:8000')
        self.timeout = 30.0
        self.headers = {"Content-Type": "application/json"}
    
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