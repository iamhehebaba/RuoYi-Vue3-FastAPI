from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from module_admin.dao.thread_dao import ThreadDao
from module_admin.entity.do.langgraphthread_do import LanggraphThread
from module_admin.entity.vo.thread_vo import ThreadCreateModel, RunCreateModel, ThreadHistoryModel, ThreadSearchModel
from utils.langgraph_util import LanggraphApiClient
from utils.common_util import CamelCaseUtil
from utils.log_util import logger
from exceptions.exception import ModelValidatorException
from module_admin.entity.vo.user_vo import CurrentUserModel

import httpx


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
            api_client = LanggraphApiClient()
            api_response = await api_client.post("/threads", request.model_dump())

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
        except (httpx.TimeoutException, httpx.RequestError) as e:
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
            api_client = LanggraphApiClient()
            api_response = await api_client.post(f"/threads/{thread_id}/runs", request.model_dump())

            # 将snake_case响应转换回camelCase
            camel_result = CamelCaseUtil.transform_result(api_response)
            return camel_result
            
        except (httpx.TimeoutException, httpx.RequestError) as e:
            raise e
        except Exception as e:
            logger.error(f"运行thread失败: {e}")
            raise e

    @classmethod
    async def create_run_in_stream_service(cls, thread_id: str, request: RunCreateModel) -> AsyncGenerator[str, None]:
        """
        流式运行thread

        :param thread_id: thread ID
        :param request: 运行thread请求
        :return: 流式响应生成器
        """
        try:
            # 调用langgraph_api服务的流式接口
            api_client = LanggraphApiClient()
            async for chunk in api_client.post_stream(f"/threads/{thread_id}/runs/stream", request.model_dump()):
                yield chunk
                
        except (httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(f"流式运行thread失败: {e}")
            raise e
        except Exception as e:
            logger.error(f"流式运行thread失败: {e}")
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
            api_client = LanggraphApiClient()
            api_response = await api_client.get(f"/threads/{thread_id}/runs/{run_id}")

            # 将snake_case响应转换回camelCase
            camel_result = CamelCaseUtil.transform_result(api_response)
            return camel_result
            
        except (httpx.TimeoutException, httpx.RequestError) as e:
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
            api_client = LanggraphApiClient()
            api_response = await api_client.get(f"/threads/{thread_id}/runs/{run_id}/join")

            # 将snake_case响应转换回camelCase
            camel_result = CamelCaseUtil.transform_result(api_response)
            return camel_result
            
        except (httpx.TimeoutException, httpx.RequestError) as e:
            raise e
        except Exception as e:
            logger.error(f"获取运行结果失败: {e}")
            raise e

    @classmethod
    async def get_thread_history_service(cls, thread_id: str, request: ThreadHistoryModel) -> Dict[str, Any]:
        """
        获取thread历史记录

        :param thread_id: thread ID
        :param request: 获取历史记录请求
        :return: 历史记录信息
        """
        try:
            # 调用langgraph_api服务
            api_client = LanggraphApiClient()
            api_response = await api_client.post(f"/threads/{thread_id}/history", request.model_dump())

            # # 将snake_case响应转换回camelCase: not needed for conversation_history field itself
            # camel_result = CamelCaseUtil.transform_result(api_response)
            # return camel_result
            if len(api_response) > 0 and ('conversation_history' in api_response[0]['values']):
                return api_response[0]['values']['conversation_history']
            else:
                return []

        except (httpx.TimeoutException, httpx.RequestError) as e:
            raise e
        except Exception as e:
            logger.error(f"获取thread历史记录失败: {e}")
            raise e

    @classmethod
    async def _validate_thread_search_request(cls, body, current_user: CurrentUserModel):
        """
        校验thread搜索请求参数

        :param body: 搜索请求参数
        :return: None
        """
        try:
            import json
            if not body:
                logger.error("请求参数不能为空!")
                raise ModelValidatorException("请求参数不能为空!")

            thread_search_model = json.loads(body.decode('utf-8'))
            if thread_search_model.get("metadata") is None or thread_search_model.get("metadata").get("user_id") != current_user.user.user_id:
                logger.error("metadata.user_id必须存在并且等于当前用户的user_id!")
                raise ModelValidatorException("metadata.user_id必须存在并且等于当前用户的user_id!")
        except json.JSONDecodeError as e:
            logger.error(f"解析thread搜索请求参数失败: {e}")
            raise ModelValidatorException("请求参数格式错误!")

    @classmethod
    async def get_thread_list_service(cls, request: Request, db: AsyncSession, current_user: CurrentUserModel,data_scope_sql: str):
        """
        转发request给Langgraph API，获取thread列表，然后再进行基于权限的过滤

        :param request: 搜索请求参数
        :param db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据范围sql语句条件
        :return: thread列表
        """
        body = await request.body()
        await cls._validate_thread_search_request(body, current_user)

        api_client = LanggraphApiClient()

        api_response = await api_client.forward_raw_request(request, "/threads/search", body)
        return api_response