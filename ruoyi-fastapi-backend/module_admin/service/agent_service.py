import os
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from module_admin.dao.agent_dao import AgentDao
from module_admin.entity.vo.agent_vo import AgentQueryModel
from module_admin.entity.do.agent_do import SysAgent
from exceptions.exception import ServiceException, PermissionException
from utils.common_util import CamelCaseUtil
from module_admin.entity.vo.user_vo import CurrentUserModel
from loguru import logger


class AgentService:
    """
    智能体管理模块服务层
    """

    @classmethod
    async def get_agent_by_graph_id_service(cls, db: AsyncSession, graph_id: str):
        """
        根据graph_id获取智能体信息

        :param db: orm对象
        :param graph_id: 智能体graph_id
        :return: 智能体信息对象
        """
        try:
            agent_info = await AgentDao.get_agent_by_graph_id(db, graph_id)
            return agent_info
        except Exception as e:
            logger.error(f"获取智能体信息失败: {e}")
            raise e

    @classmethod
    async def get_agent_list_service(cls, db: AsyncSession, query_request: AgentQueryModel, agent_scope_sql: str):
        """
        获取所有智能体列表

        :param db: orm对象
        :param query_request: 查询参数
        :param agent_scope_sql: 智能体权限对应的查询sql语句
        :return: 智能体列表
        """
        try:
            # 1. 先查询本地数据库获取智能体列表
            agent_list = await AgentDao.get_agent_list(db, query_request, agent_scope_sql)
            
            # 2. 检查是否存在assistant_id为空的记录
            has_empty_assistant_id = any(agent.assistant_id == '' or agent.assistant_id is None for agent in agent_list)
            
            # 3. 只有当存在assistant_id为空的记录时，才向langgraph-api发起查询
            if has_empty_assistant_id:
                logger.info("检测到存在assistant_id为空的记录，开始调用langgraph_api获取assistants信息")
                
                langgraph_api_url = os.getenv('LANGGRAPH_API_URL', 'http://localhost:8000')
                api_url = f"{langgraph_api_url}/assistants/search"
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        api_url,
                        json={},
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"调用langgraph_api失败: {response.status_code} - {response.text}")
                        # 如果API调用失败，直接返回原有查询结果
                        return CamelCaseUtil.transform_result(agent_list)
                    
                    api_response = response.json()
                    logger.info(f"langgraph_api响应: {api_response}")

                # 4. 创建graph_id到assistant_id的映射
                assistant_mapping = {}
                for assistant in api_response:
                    if 'graph_id' in assistant and 'assistant_id' in assistant:
                        assistant_mapping[assistant['graph_id']] = assistant['assistant_id']

                # 5. 仅更新assistant_id为空的记录
                updated_count = 0
                for agent in agent_list:
                    # 只更新assistant_id为空或None的记录
                    if (agent.assistant_id == '' or agent.assistant_id is None) and agent.graph_id in assistant_mapping:
                        # 更新数据库中的assistant_id
                        await AgentDao.update_agent_assistant_id(
                            db, 
                            agent.graph_id, 
                            assistant_mapping[agent.graph_id]
                        )
                        # 更新内存中的对象
                        agent.assistant_id = assistant_mapping[agent.graph_id]
                        updated_count += 1
                        logger.info(f"已更新智能体 {agent.graph_id} 的assistant_id为: {assistant_mapping[agent.graph_id]}")
                    elif (agent.assistant_id == '' or agent.assistant_id is None) and agent.graph_id not in assistant_mapping:
                        # 记录没有找到对应assistant_id的智能体
                        logger.error(f"智能体 {agent.graph_id} 在langgraph_api响应中未找到对应的assistant_id")

                # 6. 提交数据库更改
                if updated_count > 0:
                    await db.commit()
                    logger.info(f"成功更新了 {updated_count} 个智能体的assistant_id")
                else:
                    logger.info("没有需要更新的智能体记录")
            else:
                logger.info("所有智能体都已有assistant_id，跳过langgraph_api调用")
            
            # 7. 返回查询结果
            agent_list = await AgentDao.get_agent_list(db, query_request, agent_scope_sql)
            return CamelCaseUtil.transform_result(agent_list)
            
        except httpx.TimeoutException as e:
            logger.error("调用langgraph_api超时")
            await db.rollback()
            # 超时时返回原有逻辑结果
            raise e
        except httpx.RequestError as e:
            logger.error(f"调用langgraph_api请求错误: {e}")
            await db.rollback()
            # 请求错误时返回原有逻辑结果
            raise e
        except Exception as e:
            logger.error(f"获取智能体列表失败: {e}")
            await db.rollback()
            raise e

    @classmethod
    async def search_agents(cls, db: AsyncSession, role_ids: List[int], request: AgentQueryModel) -> List[Dict[str, Any]]:
        """
        根据角色权限搜索智能体列表

        :param db: orm对象
        :param role_ids: 用户角色ID列表
        :param request: 搜索请求参数
        :return: 智能体列表，按name排序
        """
        try:
            # 获取智能体列表
            agents = await AgentDao.get_agents_by_role_ids(db, role_ids, request)
            
            # 转换为响应格式
            agent_list = []
            for agent in agents:
                agent_dict = {
                    "graph_id": agent.graph_id,
                    "name": agent.name,
                    "description": agent.description,
                    "status": agent.status,
                    "created_at": agent.created_at.isoformat() if agent.created_at else None,
                    "created_by": agent.created_by,
                    "remark": agent.remark,
                    "order_num": agent.order_num
                }
                agent_list.append(agent_dict)
            
            return agent_list
            
        except Exception as e:
            logger.error(f"搜索智能体列表失败: {e}")
            raise e

    @classmethod
    async def validate_agent_access(cls, db: AsyncSession, graph_id: str, role_ids: List[int]) -> bool:
        """
        验证用户是否有权限访问指定的智能体

        :param db: orm对象
        :param graph_id: 智能体graph_id
        :param role_ids: 用户角色ID列表
        :return: 是否有权限访问
        """
        try:
            # 调用DAO层的验证方法
            return await AgentDao.validate_agent_access_dao(db, graph_id, role_ids)
            
        except Exception as e:
            logger.error(f"验证智能体访问权限失败: {e}")
            return False

    @classmethod
    async def check_user_agent_scope_services(cls, query_db: AsyncSession, current_user: CurrentUserModel, target_agent_id_list: List[str]):
        """
        校验当前用户是否对于指定的智能体有操作权限
        
        :param query_db: orm对象
        :param current_user: 当前用户
        :param agent_id_list: 智能体id列表
        :return: 校验结果
        """
        # 校验目标智能体是否存在
        all_agent_list = await AgentService.get_agent_list_service(query_db, AgentQueryModel(), '1==1')
        if not set(target_agent_id_list).issubset(set([agent['graphId'] for agent in all_agent_list])):
            raise ServiceException(message='指定的智能体不存在')

        if current_user.user.admin:
            return
        if not set(target_agent_id_list).issubset(set(current_user.user.agent_ids)):
            raise PermissionException(data='', message=f'当前用户没有权限访问所有的智能体:{target_agent_id_list}')
                