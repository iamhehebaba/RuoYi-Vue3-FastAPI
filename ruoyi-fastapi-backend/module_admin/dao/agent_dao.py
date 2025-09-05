from sqlalchemy import bindparam, func, or_, select, update  # noqa: F401
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from module_admin.entity.do.agent_do import SysAgent
from module_admin.entity.do.role_do import SysRoleAgent
from module_admin.entity.vo.agent_vo import AgentQueryModel


class AgentDao:
    """
    智能体管理模块数据库操作层
    """

    # @classmethod
    # async def get_agent_by_id(cls, db: AsyncSession, agent_id: int):
    #     """
    #     根据智能体id获取智能体信息

    #     :param db: orm对象
    #     :param agent_id: 智能体id
    #     :return: 智能体信息对象
    #     """
    #     agent_info = (await db.execute(select(SysAgent).where(SysAgent.id == agent_id))).scalars().first()
    #     return agent_info

    @classmethod
    async def get_agent_by_graph_id(cls, db: AsyncSession, graph_id: str):
        """
        根据graph_id获取智能体信息

        :param db: orm对象
        :param graph_id: 智能体graph_id
        :return: 智能体信息对象
        """
        agent_info = (await db.execute(select(SysAgent).where(SysAgent.graph_id == graph_id))).scalars().first()
        return agent_info

    @classmethod
    async def get_agent_list(cls, db: AsyncSession, agent_query: AgentQueryModel, agent_scope_sql: str):
        """
        获取所有智能体列表

        :param db: orm对象
        :param agent_query: 搜索请求参数
        :return: 智能体列表信息
        """
        agent_result = (
            (
                await db.execute(
                    select(SysAgent)
                    .where(
                        SysAgent.graph_id == agent_query.graph_id if agent_query.graph_id is not None else True,
                        SysAgent.status == agent_query.status if agent_query.status else True,
                        SysAgent.name.like(f'%{agent_query.name}%') if agent_query.name else True,
                        eval(agent_scope_sql),
                    )
                    .order_by(SysAgent.order_num)
                    .distinct()
                )
            )
            .scalars()
            .all()
        )

        return agent_result

    @classmethod
    async def get_agents_by_role_ids(cls, db: AsyncSession, role_ids: List[int], request: AgentQueryModel):
        """
        根据角色ID列表和搜索请求获取智能体列表

        :param db: orm对象
        :param role_ids: 角色ID列表
        :param request: 搜索请求参数
        :return: 智能体列表信息，按name排序
        """
        query = select(SysAgent).join(
            SysRoleAgent, SysAgent.graph_id == SysRoleAgent.graph_id
        ).where(
            SysRoleAgent.role_id.in_(role_ids)
        )
        
        # 如果指定了graph_id，添加过滤条件
        if request.graph_id:
            query = query.where(SysAgent.graph_id == request.graph_id)
        
        # 按名称排序
        query = query.order_by(SysAgent.name)
        
        # 分页处理：使用offset和limit
        query = query.offset(request.offset).limit(request.limit)
        
        agent_result = (await db.execute(query)).scalars().all()
        return agent_result

    @classmethod
    async def count_agents_by_role_ids(cls, db: AsyncSession, role_ids: List[int], request: AgentQueryModel):
        """
        根据角色ID列表和搜索请求统计智能体数量

        :param db: orm对象
        :param role_ids: 角色ID列表
        :param request: 搜索请求参数
        :return: 智能体数量
        """
        from sqlalchemy import func
        
        query = select(func.count(SysAgent.id)).join(
            SysRoleAgent, SysAgent.graph_id == SysRoleAgent.graph_id
        ).where(
            SysRoleAgent.role_id.in_(role_ids)
        )
        
        # 如果指定了graph_id，添加过滤条件
        if request.graph_id:
            query = query.where(SysAgent.graph_id == request.graph_id)
        
        count = (await db.execute(query)).scalar()
        return count or 0

    @classmethod
    async def validate_agent_access_dao(cls, db: AsyncSession, graph_id: str, role_ids: List[int]) -> bool:
        """
        验证用户是否有权限访问指定智能体

        :param db: orm对象
        :param graph_id: 智能体graph_id
        :param role_ids: 用户角色ID列表
        :return: 是否有权限访问
        """
        from sqlalchemy import func
        
        query = select(func.count(SysRoleAgent.role_id)).where(
            SysRoleAgent.graph_id == graph_id,
            SysRoleAgent.role_id.in_(role_ids)
        )
        
        count = (await db.execute(query)).scalar()
        return count > 0