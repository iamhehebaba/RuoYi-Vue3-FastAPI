from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import get_db
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.agent_vo import AgentQueryModel
from module_admin.entity.vo.thread_vo import ThreadCreateModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.agent_service import AgentService
from module_admin.service.thread_service import ThreadService
from module_admin.service.login_service import LoginService
from module_admin.aspect.agent_scope import GetAgentScope

from utils.response_util import ResponseUtil
from utils.log_util import logger
from fastapi import HTTPException

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


@agentController.post('/threads')
async def create_thread(
    request: Request,
    thread_request: ThreadCreateModel,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user)
):
    """
    创建新的thread
    """
    try:
        # 验证用户是否有权限访问指定的智能体
        await AgentService.check_user_agent_scope_services(db, current_user, [thread_request.graph_id])
               
        # 创建thread
        thread_result = await ThreadService.create_thread_service(
            db, 
            thread_request, 
            current_user.user.user_id
        )
        
        logger.info(f"用户 {current_user.user.get_user_name()} 成功创建thread: {thread_result.get('threadId')}")
        
        return ResponseUtil.success(data=thread_result, msg="Thread创建成功")
        
    except Exception as e:
        logger.error(f"创建thread失败: {e}")
        return ResponseUtil.error(msg=f"创建thread失败: {str(e)}")


