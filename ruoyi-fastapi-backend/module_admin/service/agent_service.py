from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, HTTPException
from typing import List, Dict, Any
from module_admin.dao.agent_dao import AgentDao
from module_admin.entity.vo.agent_vo import AgentQueryModel
from module_admin.entity.do.agent_do import SysAgent
from exceptions.exception import ServiceException, PermissionException
from utils.common_util import CamelCaseUtil, SqlalchemyUtil
from utils.langgraph_util import LanggraphApiClient
from module_admin.entity.vo.user_vo import CurrentUserModel
from loguru import logger
from collections import defaultdict



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
                
                try:
                    api_client = LanggraphApiClient()
                    api_response = await api_client.post("/assistants/search", {})
                except Exception as e:
                    logger.error(f"调用langgraph_api失败: {e}")
                    # 如果API调用失败，直接返回原有查询结果
                    return CamelCaseUtil.transform_result(agent_list)

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
            
        except (httpx.TimeoutException, httpx.RequestError) as e:
            await db.rollback()
            raise e
        except Exception as e:
            logger.error(f"获取智能体列表失败: {e}")
            await db.rollback()
            raise e

    @classmethod
    async def get_agents_for_current_user(cls, db: AsyncSession, current_user: CurrentUserModel) -> List[SysAgent]:
        """
        根据角色权限搜索智能体列表

        :param db: orm对象
        :param current_user: 当前用户对象
        :return: 智能体列表，按name排序
        """
        try:
            # 获取智能体列表
            if current_user.user.admin:
                agent_list = await AgentDao.get_agent_list(db, AgentQueryModel(), '1==1')
            else:
                role_id_list = [role.role_id for role in current_user.user.role]
                agent_list = await AgentDao.get_agents_by_role_ids(db, role_id_list)
            return agent_list
         
        except Exception as e:
            logger.error(f"搜索智能体列表失败: {e}")
            raise e

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
        if not set(target_agent_id_list).issubset(set(current_user.user.agent_ids)):
            raise PermissionException(data='', message=f'当前用户没有权限访问所有的智能体:{target_agent_id_list}')
                
    @classmethod
    async def filter_agent_by_permission(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        payload: Any) -> Any:

        """
        对智能体列表进行权限过滤，同时把存放在sys_agent中的agent信息作为metadata插入从langgraph返回的assistant list中

        :param full_path: 知识库路径
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param payload: 智能体列表
        :return: 过滤后的智能体列表
        """
        agent_list = await cls.get_agents_for_current_user(query_db, current_user)
        permitted_graph_id_list = [agent.graph_id for agent in agent_list]
        graph_id_to_agent = defaultdict(dict)
        for agent in agent_list:
            graph_id_to_agent[agent.graph_id] = agent
        
        # 检查payload是否为空或结构不完整
        if not payload or not isinstance(payload, list):
            logger.warning("payload为空或格式不正确")
            return payload
        
        # 过滤agent列表
        original_agents = payload
        filtered_agents = []
        
        for agent in original_agents:
            if isinstance(agent, dict) and "graph_id" in agent:
                graph_id = agent["graph_id"]
                if graph_id in permitted_graph_id_list:
                    agent["metadata"].update(SqlalchemyUtil.serialize_result(graph_id_to_agent[graph_id]))
                    # 保留有权限的智能体
                    filtered_agents.append(agent)
                else:
                    # 移除无权限的智能体并记录日志
                    logger.info(f"用户 {current_user.user.user_name} 无权限访问智能体: graphId={graph_id}，已从列表中移除")
            else:
                # agent结构不正确，记录日志但不添加到结果中
                logger.warning(f"智能体数据结构不正确: {agent}")
        
        # 更新payload
        payload = filtered_agents
        
        logger.info(f"智能体权限过滤完成，原始数量: {len(original_agents)}, 过滤后数量: {len(filtered_agents)}")
        
        return payload                