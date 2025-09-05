import os
import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from module_admin.dao.thread_dao import ThreadDao
from module_admin.entity.do.thread_do import LanggraphThread
from module_admin.entity.vo.thread_vo import ThreadCreateModel, ThreadCreateResponseModel, RunCreateModel
from module_admin.entity.vo.common_vo import CrudResponseModel
from utils.common_util import CamelCaseUtil, SnakeCaseUtil
from loguru import logger


class ThreadService:
    """
    Thread管理模块服务层
    """

    @classmethod
    async def create_thread_service(cls, db: AsyncSession, request: ThreadCreateModel, created_by: str) -> Dict[str, Any]:
        """
        创建新的thread

        :param db: orm对象
        :param request: 创建thread请求
        :param created_by: 创建者
        :return: 创建的thread信息
        """
        try:
            # 调用langgraph_api服务
            langgraph_api_url = os.getenv('LANGGRAPH_API_URL', 'http://localhost:8000')
            api_url = f"{langgraph_api_url}/threads"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    api_url,
                    json=request.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    logger.error(f"调用langgraph_api失败: {response.status_code} - {response.text}")
                    raise Exception(f"调用langgraph_api失败: {response.status_code}")
                
                api_response = response.json()
                logger.info(f"langgraph_api响应: {api_response}")

            # # 3. 将snake_case转换回camelCase
            # camel_case_response = CamelCaseUtil.snake_to_camel(api_response)
            
            # 4. 存储到数据库
            thread_record = LanggraphThread(
                thread_id=api_response.get('thread_id'),
                graph_id=request.graph_id,
                assistant_id=api_response.get('assistant_id') if hasattr(api_response, 'assistant_id') else None,
                created_by=created_by,
                created_at=datetime.now()
            )
            
            # return camel_case_response
            camel_result = CamelCaseUtil.transform_result(api_response)

            await ThreadDao.create_thread(db, thread_record)
            logger.info(f"Thread记录已保存到数据库: {thread_record.thread_id}")
            await db.commit()
            return camel_result
        except httpx.TimeoutException as e:
            logger.error("调用langgraph_api超时")
            await db.rollback()
            raise e
        except httpx.RequestError as e:
            logger.error(f"调用langgraph_api请求错误: {e}")
            await db.rollback()
            raise e
        except Exception as e:
            logger.error(f"创建thread失败: {e}")
            await db.rollback()
            raise e

    @classmethod
    async def get_thread_by_id_service(cls, db: AsyncSession, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        根据thread_id获取thread信息

        :param db: orm对象
        :param thread_id: thread ID
        :return: thread信息
        """
        try:
            thread_info = await ThreadDao.get_thread_by_id(db, thread_id)
            if thread_info:
                return CamelCaseUtil.transform_result([thread_info])[0]
            return None
        except Exception as e:
            logger.error(f"根据thread_id获取thread信息失败: {e}")
            raise e

    @classmethod
    async def get_threads_by_graph_id_service(cls, db: AsyncSession, graph_id: str):
        """
        根据graph_id获取所有相关的thread列表

        :param db: orm对象
        :param graph_id: 智能体图ID
        :return: thread列表
        """
        try:
            threads = await ThreadDao.get_threads_by_graph_id(db, graph_id)
            return CamelCaseUtil.transform_result(threads)
        except Exception as e:
            logger.error(f"根据graph_id获取thread列表失败: {e}")
            raise e

    @classmethod
    async def get_threads_by_user_service(cls, db: AsyncSession, created_by: str):
        """
        根据创建者获取thread列表

        :param db: orm对象
        :param created_by: 创建者
        :return: thread列表
        """
        try:
            threads = await ThreadDao.get_threads_by_user(db, created_by)
            return CamelCaseUtil.transform_result(threads)
        except Exception as e:
            logger.error(f"根据创建者获取thread列表失败: {e}")
            raise e

    @classmethod
    async def create_run_service(cls, thread_id: str, request: RunCreateModel) -> Dict[str, Any]:
        """
        运行thread

        :param thread_id: thread ID
        :param request: 运行thread请求
        :return: 运行结果
        """
        try:
            # # 将camelCase请求转换为snake_case
            # snake_case_request = SnakeCaseUtil.transform_result(request.model_dump())
            
            # 调用langgraph_api服务
            langgraph_api_url = os.getenv('LANGGRAPH_API_URL', 'http://localhost:8000')
            api_url = f"{langgraph_api_url}/threads/{thread_id}/runs"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    api_url,
                    json=request.model_dump(),
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    logger.error(f"调用langgraph_api失败: {response.status_code} - {response.text}")
                    raise Exception(f"调用langgraph_api失败: {response.status_code}")
                
                api_response = response.json()
                logger.info(f"langgraph_api响应: {api_response}")

            # 将snake_case响应转换回camelCase
            camel_result = CamelCaseUtil.transform_result(api_response)
            return camel_result
            
        except httpx.TimeoutException:
            logger.error("调用langgraph_api超时")
            raise e
        except httpx.RequestError as e:
            logger.error(f"调用langgraph_api请求错误: {e}")
            raise e
        except Exception as e:
            logger.error(f"运行thread失败: {e}")
            raise e

    @classmethod
    async def get_run_status_service(cls, thread_id: str, run_id: str) -> Dict[str, Any]:
        """
        获取运行状态

        :param thread_id: thread ID
        :param run_id: run ID
        :return: 运行状态信息
        """
        try:
            # 调用langgraph_api服务
            langgraph_api_url = os.getenv('LANGGRAPH_API_URL', 'http://localhost:8000')
            api_url = f"{langgraph_api_url}/threads/{thread_id}/runs/{run_id}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    api_url,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    logger.error(f"调用langgraph_api失败: {response.status_code} - {response.text}")
                    raise Exception(f"调用langgraph_api失败: {response.status_code}")
                
                api_response = response.json()
                logger.info(f"langgraph_api响应: {api_response}")

            # 将snake_case响应转换回camelCase
            camel_result = CamelCaseUtil.transform_result(api_response)
            return camel_result
            
        except httpx.TimeoutException:
            logger.error("调用langgraph_api超时")
            raise e
        except httpx.RequestError as e:
            logger.error(f"调用langgraph_api请求错误: {e}")
            raise e
        except Exception as e:
            logger.error(f"获取运行状态失败: {e}")
            raise e

    @classmethod
    async def get_run_result_service(cls, thread_id: str, run_id: str) -> Dict[str, Any]:
        """
        获取运行结果

        :param thread_id: thread ID
        :param run_id: run ID
        :return: 运行结果信息
        """
        try:
            # 调用langgraph_api服务
            langgraph_api_url = os.getenv('LANGGRAPH_API_URL', 'http://localhost:8000')
            api_url = f"{langgraph_api_url}/threads/{thread_id}/runs/{run_id}/join"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    api_url,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    logger.error(f"调用langgraph_api失败: {response.status_code} - {response.text}")
                    raise Exception(f"调用langgraph_api失败: {response.status_code}")
                
                api_response = response.json()
                logger.info(f"langgraph_api响应: {api_response}")

            # 将snake_case响应转换回camelCase
            camel_result = CamelCaseUtil.transform_result(api_response)
            return camel_result
            
        except httpx.TimeoutException:
            logger.error("调用langgraph_api超时")
            raise e
        except httpx.RequestError as e:
            logger.error(f"调用langgraph_api请求错误: {e}")
            raise e
        except Exception as e:
            logger.error(f"获取运行结果失败: {e}")
            raise e