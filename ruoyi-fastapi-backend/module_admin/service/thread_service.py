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
from utils.string_util import StringUtil
from exceptions.exception import ModelValidatorException, ServiceException, PermissionException
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.agent_service import AgentService
from module_admin.service.ragflow_tenant_llm_service import RagflowTenantLLMService
from config.get_db import get_db_ragflow
from config.env import LlmConfig


import httpx


class ThreadService:

    REDIS_KEY_CHAT_LLM_API_BASE_URL = "llm_config:chat_llm_api_base_url:"
    REDIS_KEY_CHAT_LLM_API_KEY = "llm_config:chat_llm_api_key:"

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
    async def get_threads_for_current_user(cls, db: AsyncSession, current_user: CurrentUserModel):
        """
        根据当前用户获取thread列表

        :param db: orm对象
        :param current_user: 当前用户
        :return: thread列表
        """
        try:
            threads = await ThreadDao.get_threads_by_user(db, current_user.user.user_id)
            return threads
        except Exception as e:
            logger.error(f"根据当前用户获取thread列表失败: {e}")
            raise e

    @classmethod
    async def delete_thread_by_id(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        payload: Any) -> Any:
        """
        从数据库中删除thread记录
        
        :param full_path: delete thread url path
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param payload: delete thread response
        :return: 原来的payload
        """        

        try:
            thread_id = StringUtil.extract_regex_group(".*threads/(.*)", full_path, 1)
            if not thread_id:
                logger.error(f"从URL中提取thread_id失败: {full_path}")
                raise ServiceException(f"从URL中提取thread_id失败: {full_path}")
            
            # 4. 删除数据库记录
            delete_success = await ThreadDao.delete_thread_by_id(query_db, thread_id)
            if not delete_success:
                query_db.rollback()
                logger.error(f"删除thread记录失败: {thread_id}")
                raise ServiceException(f"删除thread记录失败: {thread_id}")
            else:
                await query_db.commit()
                return payload
                
        except Exception as e:
            await query_db.rollback()
            logger.error(f"删除thread失败: {e}")
            raise ServiceException(f"删除thread失败: {str(e)}")

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

    @classmethod
    async def validate_metadata_for_thread_creation(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        body: Any) -> Any:
        """
        校验metadata的合法性：是否存在，其中的user_id是否是当前用户的user_id
        
        :param full_path: 知识库路径
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param payload: 智能体列表
        :return: 校验结果
        """
        payload = None
        if body:
            try:
                import json
                payload = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = body

        if payload and isinstance(payload, dict) and "metadata" in payload:
            metadata = payload["metadata"]
            graph_id = metadata.get("graph_id")
            if graph_id is None:
                logger.error("metadata.graph_id字段不存在!")
                raise ModelValidatorException("metadata.graph_id字段不存在!")
            
            await AgentService.check_user_agent_scope_services(query_db, current_user, [graph_id])

            user_id = metadata.get("user_id")
            if user_id is None:
                logger.error("metadata.user_id字段不存在!")
                raise ModelValidatorException("metadata.user_id字段不存在!")
            elif user_id != current_user.user.user_id:
                logger.error("metadata.user_id必须等于当前用户的user_id!")
                raise ModelValidatorException("metadata.user_id必须等于当前用户的user_id!")

        else:
            logger.error("metadata字段不存在!")
            raise ModelValidatorException("metadata字段不存在!")

    @classmethod
    async def validate_metadata_for_thread_search(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        body: Any) -> Any:
        """
        校验metadata的合法性: user_id是否是当前用户的user_id
        
        :param full_path: 知识库路径
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param payload: 智能体列表
        :return: 校验结果
        """
        payload = None
        if body:
            try:
                import json
                payload = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = body

        if payload and isinstance(payload, dict) and "metadata" in payload:
            metadata = payload["metadata"]

            user_id = metadata.get("user_id")
            if user_id is None:
                logger.error("metadata.user_id字段不存在!")
                raise ModelValidatorException("metadata.user_id字段不存在!")
            elif user_id != current_user.user.user_id:
                logger.error("metadata.user_id必须等于当前用户的user_id!")
                raise ModelValidatorException("metadata.user_id必须等于当前用户的user_id!")
                
        else:
            logger.error("metadata字段不存在!")
            raise ModelValidatorException("metadata字段不存在!")                

    @classmethod
    async def connect_thread_with_agent(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        payload: Any) -> Any:
        """
        在通过langgraph api创建了thread之后，将thread与智能体关联起来（通过数据库表）
        
        :param full_path: create thread url path
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param payload: create thread response
        :return: 原来的payload
        """

        if not payload or not isinstance(payload, dict):
            logger.warning("payload为空或格式不正确")
            return payload

        thread_id = payload.get("thread_id")
        metadata = payload.get("metadata")
        if metadata and metadata.get("graph_id"):
            graph_id = metadata.get("graph_id")

        if thread_id and graph_id:
            try:
                thread_record = LanggraphThread(
                    thread_id=thread_id,
                    graph_id=graph_id,
                    user_id=current_user.user.user_id,
                    created_by=current_user.user.user_name,
                    created_at=datetime.now()
                )
                
                await ThreadDao.create_thread(query_db, thread_record)
                logger.info(f"Thread记录已保存到数据库: {thread_record.thread_id}")
                await query_db.commit()

            except Exception as e:
                logger.error(f"保存Thread记录到数据库时出错: {e}")
                raise ServiceException("出现数据库内部错误！")
        else:
            logger.error(f"thread_id或graph_id为空")
            raise ServiceException("Langgraph响应中thread_id或graph_id为空！")

        return payload
                
    @classmethod
    def get_thread_id_from_path(cls, full_path: str) -> str:
        """
        从路径中提取thread_id

        :param full_path: 知识库路径
        :return: thread_id
        """
        thread_id = StringUtil.extract_regex_group(".*threads/(.*)/(runs|history).*", full_path, 1)
        if not thread_id:
            thread_id = StringUtil.extract_regex_group(".*threads/(.*)", full_path, 1)
        return thread_id

    @classmethod
    async def validate_thread_permission(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        body: Any) -> Any:
        """
        校验当前用户对于指定的thread是否有权限

        :param full_path: 知识库路径
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param body: 请求体
        :return: 校验结果
        """

        thread_id_in_path = cls.get_thread_id_from_path(full_path)

        threads_for_current_user = await cls.get_threads_for_current_user(query_db, current_user)
        thread_ids_for_current_user = [thread.thread_id for thread in threads_for_current_user]

        if thread_id_in_path not in thread_ids_for_current_user:
            logger.error(f"当前用户没有权限访问thread_id为{thread_id_in_path}的thread")
            raise PermissionException(f"当前用户没有权限访问thread_id为{thread_id_in_path}的thread")

    @classmethod
    async def refresh_llm_config(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        body: Any) -> Any:
        """
        校验当前用户对于指定的thread是否有权限

        :param full_path: 知识库路径
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param body: 请求体
        :return: 校验结果
        """

        thread_id_in_path = cls.get_thread_id_from_path(full_path)
        payload = None
        if body:
            try:
                import json
                payload = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"解析请求体为JSON时出错。请求体：{body}，错误：{e}")
                raise ModelValidatorException(message=f"请求体不是一个合法的json对象！") 

        if payload and payload.get("config") and 'configurable' in payload["config"]:
            configurable = payload["config"]['configurable']
            
            # 提取llm_factory和llm_name
            chat_llm_factory = configurable.get('chat_llm_factory')
            chat_llm_name = configurable.get('chat_llm_name')
            
            if chat_llm_factory and chat_llm_name:
                try:
                    # special handling for VLLM model name due to ragflow bug: ragflow appends "___VLM" to the model name
                    ragflow_llm_name = chat_llm_name
                    if chat_llm_factory.lower() == "vllm":
                        ragflow_llm_name = chat_llm_name + "___VLLM"                    

                    # 调用RagflowTenantLLMService查询LLM配置
                    async for db in get_db_ragflow():
                        llm_config = await RagflowTenantLLMService.get_ragflow_tenant_llm_by_key_service(
                            db, chat_llm_factory, ragflow_llm_name
                        )
                    
                        if llm_config:
                            # refresh api_base_url & api_key in redis
                            redis_client = request.app.state.redis
                            if not llm_config.api_base:
                                llm_config.api_base = getattr(LlmConfig, f"{chat_llm_factory.replace('-', '_').lower()}_base_url")
                                logger.info(f"根据chat_llm_factory={chat_llm_factory}获取到LLM base_url={llm_config.api_base}")

                            await redis_client.set(ThreadService.REDIS_KEY_CHAT_LLM_API_BASE_URL+thread_id_in_path, llm_config.api_base, ex=60 * 3)
                            await redis_client.set(ThreadService.REDIS_KEY_CHAT_LLM_API_KEY+thread_id_in_path, llm_config.api_key if llm_config.api_key else '', ex=60 * 3)          
                            logger.info(f"成功刷新LLM配置: {chat_llm_factory}/{chat_llm_name}")
                        else:
                            logger.warning(f"未找到LLM配置: {chat_llm_factory}/{chat_llm_name}")
                        
                except Exception as e:
                    logger.error(f"查询LLM配置失败: {str(e)}")
                    raise ModelValidatorException(message=f"查询LLM配置失败: chat_llm_factory={chat_llm_factory}, chat_llm_name={chat_llm_name}", data=f"{str(e)}")
            else:
                raise ModelValidatorException(message=f"请求中缺少了模型信息！")        
        else:
            raise ModelValidatorException(message=f"请求中缺少了模型信息！")
