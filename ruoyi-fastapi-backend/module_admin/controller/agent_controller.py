from fastapi import APIRouter, Depends, Body, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from config.get_db import get_db
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.agent_vo import AgentQueryModel, AgentResponse
from module_admin.service.agent_service import AgentService
from module_admin.service.login_service import LoginService
from module_admin.entity.vo.user_vo import CurrentUserModel
from utils.response_util import ResponseUtil
from loguru import logger
from fastapi import HTTPException
from module_admin.aspect.agent_scope import GetAgentScope

agentController = APIRouter(prefix='/langgraph', tags=['智能体管理'])


# 任何具有角色编辑、角色添加权限的人都可以访问该接口以便定义、修改角色的智能体时
@agentController.post('/assistants/search', dependencies=[Depends(CheckUserInterfaceAuth(['system:role:add', 'system:role:edit'], False))])
async def search_agents(
    request: Request,
    search_condition: AgentQueryModel,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    agent_scope_sql: str = Depends(GetAgentScope('SysAgent'))
):
    """
    搜索智能体列表接口
    
    根据用户角色权限返回可访问的智能体列表，支持按graph_id过滤，按name排序，支持limit和offset分页。
    """
    try:
        result = await AgentService.get_agent_list_service(db, search_condition, agent_scope_sql)
        return ResponseUtil.success(data=result)
        
    except Exception as e:
        logger.error(f"搜索智能体列表失败: {e}")
        raise HTTPException(status_code=500, detail="搜索智能体列表失败")


# @agentController.get('/assistants/{graph_id}', dependencies=[Depends(CheckUserInterfaceAuth('agent:get'))])
# async def get_agent_by_graph_id(
#     graph_id: str,
#     db: AsyncSession = Depends(get_db),
#     current_user: CurrentUserModel = Depends(LoginService.get_current_user)
# ):
#     """
#     根据graph_id获取智能体详情
    
#     :param graph_id: 智能体图ID
#     :param db: 数据库会话
#     :param current_user: 当前用户信息
#     :return: 智能体详情
#     """
#     try:
#         # 获取用户角色ID列表
#         role_ids = [role.role_id for role in current_user.user.role] if current_user.user and current_user.user.role else []
        
#         if not role_ids:
#             logger.warning(f"用户 {current_user.user.user_name if current_user.user else 'unknown'} 没有分配角色")
#             raise HTTPException(status_code=403, detail="用户没有分配角色")
        
#         # 验证用户是否有权限访问该智能体
#         has_access = await AgentService.validate_agent_access(db, graph_id, role_ids)
#         if not has_access:
#             logger.warning(f"用户 {current_user.user.user_name if current_user.user else 'unknown'} 无权访问智能体 {graph_id}")
#             raise HTTPException(status_code=403, detail="无权访问该智能体")
        
#         # 获取智能体信息
#         agent = await AgentService.get_agent_by_graph_id(db, graph_id)
#         if not agent:
#             raise HTTPException(status_code=404, detail="智能体不存在")
        
#         agent_dict = {
#             "id": agent.id,
#             "graph_id": agent.graph_id,
#             "name": agent.name,
#             "description": agent.description,
#             "role_id": agent.role_id,
#             "created_at": agent.created_at.isoformat() if agent.created_at else None,
#             "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
#         }
        
#         return ResponseUtil.success(data=agent_dict)
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"获取智能体详情失败: {e}")
#         raise HTTPException(status_code=500, detail="获取智能体详情失败")