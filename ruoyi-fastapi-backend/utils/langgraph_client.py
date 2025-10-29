import requests
import base64
import json
from loguru import logger
import asyncio
import re
import httpx
from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import atexit
import socket
import urllib.parse

from config.env import LanggraphConfig

# 全局异步HTTP客户端实例，用于流式请求
_global_async_client: Optional[httpx.AsyncClient] = None

def _test_connection(url: str) -> bool:
    """测试网络连接是否可用"""
    try:
        parsed_url = urllib.parse.urlparse(url)
        host = parsed_url.hostname
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
        
        # 创建socket连接测试
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5秒超时
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            logger.debug(f"网络连接测试成功: {host}:{port}")
            return True
        else:
            logger.warning(f"网络连接测试失败: {host}:{port}, 错误码: {result}")
            return False
            
    except Exception as e:
        logger.warning(f"网络连接测试异常: {e}")
        return False


def _get_global_async_client() -> httpx.AsyncClient:
    """获取全局异步HTTP客户端，使用连接池和持久连接"""
    global _global_async_client
    
    if _global_async_client is None:
        try:
            # 创建连接池配置，优化性能
            limits = httpx.Limits(
                max_keepalive_connections=10,  # 减少连接池大小
                max_connections=50,            # 减少最大连接数
                keepalive_expiry=30.0          # 保持连接30秒
            )
            
            # 设置超时配置，与原requests.Session保持一致
            timeout = httpx.Timeout(
                connect=10.0,   # 连接超时
                read=30.0,     # 读取超时
                write=10.0,     # 写入超时
                pool=5.0        # 连接池超时
            )
            
            _global_async_client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                verify=False,  # 禁用SSL验证，与原requests.Session保持一致
                follow_redirects=True,
                http2=True  # 启用HTTP/2
            )
            
            logger.info("全局异步HTTP客户端初始化成功")
            
            # 注册退出时清理函数
            atexit.register(_cleanup_global_client)
            
        except Exception as e:
            logger.error(f"初始化全局异步HTTP客户端失败: {e}")
            # 如果初始化失败，返回None，让调用方处理
            return None
    
    return _global_async_client

def _cleanup_global_client():
    """清理全局客户端"""
    global _global_async_client
    if _global_async_client is not None:
        try:
            # 在事件循环中安全地关闭客户端
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_global_async_client.aclose())
            else:
                loop.run_until_complete(_global_async_client.aclose())
            logger.info("全局异步HTTP客户端已清理")
        except Exception as e:
            logger.warning(f"清理全局异步HTTP客户端时发生错误: {e}")
        finally:
            _global_async_client = None

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
        发送POST流式请求（带连接测试和降级机制）
        
        :param path: API路径
        :param headers: 额外的请求头
        :param body: 原始请求体
        :param kwargs: 其他请求参数
        :return: 异步生成器，逐行yield流式响应数据
        """
        url = f"{self.base_url}{path}"
        
        # 首先测试网络连接
        if not _test_connection(url):
            logger.warning(f"网络连接测试失败，将使用同步requests方法作为备选方案: {url}")
            # 降级到同步requests方法
            async for line in self._fallback_stream_request(url, headers, body, **kwargs):
                yield line
            return
        
        try:
            # 使用全局异步客户端，避免每次创建新连接
            client = _get_global_async_client()
            if client is None:
                logger.warning("异步客户端初始化失败，使用同步requests方法作为备选方案")
                async for line in self._fallback_stream_request(url, headers, body, **kwargs):
                    yield line
                return
                
            logger.debug(f"开始流式请求到: {url}")

            request_headers = headers.copy() if headers else {}

            # 合并默认headers和传入的headers
            if 'headers' in kwargs:
                request_headers.update(kwargs.pop('headers'))
            
            # 设置流式请求的Accept头和其他优化头
            request_headers.update({
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            })
            
            logger.debug(f"请求头: {request_headers}")
            
            # 使用流式请求，简化处理逻辑
            async with client.stream(
                method="POST",
                url=url,
                headers=request_headers,
                content=body,
                **kwargs
            ) as response:
                if response.status_code != 200:
                    logger.error(f"调用langgraph_api流式请求失败: {response.status_code}")
                    raise Exception(f"调用langgraph_api流式请求失败: {response.status_code}")
                
                logger.debug(f"流式响应头: {response.headers}")
                
                # 使用简单直接的aiter_text()方式，添加流结束检测机制
                empty_chunk_count = 0
                max_empty_chunks = 5  # 连续5个空chunk后认为流结束
                
                async for chunk in response.aiter_text():
                    if chunk.strip():  # 有内容的chunk
                        empty_chunk_count = 0  # 重置空chunk计数
                        logger.debug(f"yield 流式数据: {chunk}")
                        yield chunk
                        
                        # # 检测常见的流结束标记
                        # if chunk.strip() in ['[DONE]', 'data: [DONE]', '{"done": true}']:
                        #     logger.info("检测到流结束标记，立即关闭连接")
                        #     break
                    else:
                        # 空chunk计数
                        empty_chunk_count += 1
                        logger.debug(f"收到空chunk，计数: {empty_chunk_count}")
                        
                        # 连续收到多个空chunk，可能是流结束
                        if empty_chunk_count >= max_empty_chunks:
                            logger.info(f"连续收到{max_empty_chunks}个空chunk，认为流已结束，关闭连接")
                            break
                
                logger.info("异步流式响应处理完成，连接已关闭")
                            
        except httpx.TimeoutException as e:
            logger.error(f"调用langgraph_api流式请求超时: {e}, URL: {url}")
            logger.warning("异步请求超时，尝试使用同步requests方法作为备选方案")
            async for line in self._fallback_stream_request(url, headers, body, **kwargs):
                yield line
        except httpx.ConnectError as e:
            logger.error(f"调用langgraph_api流式请求连接错误: {e}, URL: {url}")
            logger.warning("异步连接失败，使用同步requests方法作为备选方案")
            async for line in self._fallback_stream_request(url, headers, body, **kwargs):
                yield line
        except httpx.RequestError as e:
            logger.error(f"调用langgraph_api流式请求错误: {e}, URL: {url}")
            logger.warning("异步请求失败，使用同步requests方法作为备选方案")
            async for line in self._fallback_stream_request(url, headers, body, **kwargs):
                yield line
        except Exception as e:
            logger.error(f"调用langgraph_api流式请求失败: {e}, URL: {url}")
            logger.warning("异步请求异常，使用同步requests方法作为备选方案")
            async for line in self._fallback_stream_request(url, headers, body, **kwargs):
                yield line
    
    async def _fallback_stream_request(self, url: str, headers: dict = None, body: bytes = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        备选的同步流式请求方法
        当异步请求失败时使用此方法作为降级方案
        """
        try:
            logger.info(f"使用同步requests方法进行流式请求: {url}")
            
            # 准备请求头
            request_headers = headers.copy() if headers else {}
            request_headers.update({
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            })
            
            # 使用requests.Session进行流式请求
            session = requests.Session()
            session.verify = False  # 禁用SSL验证
            
            try:
                response = session.post(
                    url,
                    headers=request_headers,
                    data=body,
                    stream=True,
                    timeout=300  # 5分钟超时
                )
                
                if response.status_code != 200:
                    logger.error(f"同步流式请求失败: {response.status_code}")
                    raise Exception(f"同步流式请求失败: {response.status_code}")
                
                # 逐行读取响应，添加流结束检测
                empty_line_count = 0
                max_empty_lines = 5  # 连续5个空行后认为流结束
                
                for line in response.iter_lines(decode_unicode=True):
                    if line and line.strip():
                        empty_line_count = 0  # 重置空行计数
                        yield line
                        
                        # 检测常见的流结束标记
                        if line.strip() in ['[DONE]', 'data: [DONE]', '{"done": true}']:
                            logger.info("同步流式请求检测到结束标记，立即关闭连接")
                            break
                    else:
                        # 空行计数
                        empty_line_count += 1
                        logger.debug(f"同步流式请求收到空行，计数: {empty_line_count}")
                        
                        # 连续收到多个空行，可能是流结束
                        if empty_line_count >= max_empty_lines:
                            logger.info(f"同步流式请求连续收到{max_empty_lines}个空行，认为流已结束，关闭连接")
                            break
                
                logger.info("同步流式响应处理完成，连接已关闭")
                
            finally:
                # 确保session被正确关闭
                try:
                    session.close()
                    logger.debug("同步requests session已关闭")
                except Exception as close_error:
                    logger.warning(f"关闭同步session时出现错误: {close_error}")
                    
        except Exception as e:
            logger.error(f"同步流式请求也失败了: {e}")
            raise e
    

# 创建全局实例
langgraph_client = LanggraphClient()
