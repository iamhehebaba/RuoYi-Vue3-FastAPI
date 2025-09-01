from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from module_admin.dao.agent_dao import AgentDao
from module_admin.entity.vo.agent_vo import AgentQueryModel
from module_admin.entity.do.agent_do import SysAgent
from utils.common_util import CamelCaseUtil
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
            logger.error(f"根据graph_id获取智能体信息失败: {e}")
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

        agent_list = await AgentDao.get_agent_list(db, query_request, agent_scope_sql)

        # todo: maybe need to do transformation by calling CamelCaseUtil.transform_result if necessary by frontend
        return CamelCaseUtil.transform_result(agent_list)

        # return agent_list


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
                    "role_id": agent.role_id,
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
            agent = await AgentDao.get_agent_by_graph_id(db, graph_id)
            if not agent:
                return False
            
            # 检查用户角色是否有权限访问该智能体
            return agent.role_id in role_ids
            
        except Exception as e:
            logger.error(f"验证智能体访问权限失败: {e}")
            return False