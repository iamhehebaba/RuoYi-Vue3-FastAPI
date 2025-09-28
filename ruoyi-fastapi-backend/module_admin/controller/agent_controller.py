from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import get_db, get_db_ragflow
from exceptions.exception import ModelValidatorException
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth, CheckOwnershipInterfaceAuth
from module_admin.entity.vo.agent_vo import AgentQueryModel
from module_admin.entity.vo.thread_vo import ThreadCreateModel, RunCreateModel, ThreadHistoryModel, ThreadSearchModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.agent_service import AgentService
from module_admin.service.thread_service import ThreadService
from module_admin.service.login_service import LoginService
from module_admin.aspect.agent_scope import GetAgentScope
from module_admin.aspect.data_scope import GetDataScope

from module_admin.service.ragflow_tenant_llm_service import RagflowTenantLLMService

from utils.response_util import ResponseUtil
from utils.log_util import logger

agentController = APIRouter(prefix='/langgraph', tags=['智能体管理'])

REDIS_KEY_CHAT_LLM_API_BASE_URL = "llm_config:chat_llm_api_base_url"
REDIS_KEY_CHAT_LLM_API_KEY = "llm_config:chat_llm_api_key"

async def _refresh_llm_config(request: Request, run_request: RunCreateModel, db_ragflow: AsyncSession):
    """
    从run_request.config中提取并添加LLM配置信息
    
    Args:
        run_request: 运行请求对象
        db_ragflow: 数据库会话
    """

    if run_request.config and 'configurable' in run_request.config:
        configurable = run_request.config['configurable']
        
        # 提取llm_factory和llm_name
        chat_llm_factory = configurable.get('chat_llm_factory')
        chat_llm_name = configurable.get('chat_llm_name')
        
        if chat_llm_factory and chat_llm_name:
            try:
                # 调用RagflowTenantLLMService查询LLM配置
                llm_config = await RagflowTenantLLMService.get_ragflow_tenant_llm_by_key_service(
                    db_ragflow, chat_llm_factory, chat_llm_name
                )
                
                if llm_config:
                    # refresh api_base_url & api_key in redis
                    redis_client = request.app.state.redis
                    await redis_client.set(REDIS_KEY_CHAT_LLM_API_BASE_URL, llm_config.api_base if llm_config.api_base else '')
                    await redis_client.set(REDIS_KEY_CHAT_LLM_API_KEY, llm_config.api_key if llm_config.api_key else '')          
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

    result = await AgentService.get_agent_list_service(db, search_condition, agent_scope_sql)
    return ResponseUtil.success(data=result)
        

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
    # 验证用户是否有权限访问指定的智能体
    await AgentService.check_user_agent_scope_services(db, current_user, [thread_request.graph_id])
            
    # 创建thread
    thread_result = await ThreadService.create_thread_service(
        db, 
        thread_request, 
        current_user.user.get_user_name()
    )
    
    logger.info(f"用户 {current_user.user.get_user_name()} 成功创建thread: {thread_result.get('threadId')}")
    
    return ResponseUtil.success(data=thread_result, msg="Thread创建成功")

    
        
@agentController.post('/threads/{thread_id}/runs', dependencies=[Depends(CheckOwnershipInterfaceAuth('thread_id', 'LanggraphThread'))])
async def create_run(
    request: Request,
    thread_id: str,
    run_request: RunCreateModel,
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    db_ragflow: AsyncSession = Depends(get_db_ragflow)
):
    """
    运行thread
    """
    
    # 刷新LLM配置
    await _refresh_llm_config(request, run_request, db_ragflow)

    # 运行thread
    run_result = await ThreadService.create_run_service(
        thread_id, 
        run_request
    )
    
    logger.info(f"用户 {current_user.user.get_user_name()} 成功创建了一个run: {run_result.get('runId')}")
    
    return ResponseUtil.success(data=run_result, msg="Run创建成功")

@agentController.post('/threads/{thread_id}/runs/stream', dependencies=[Depends(CheckOwnershipInterfaceAuth('thread_id', 'LanggraphThread'))])
async def create_run_in_stream(
    request: Request,
    thread_id: str,
    run_request: RunCreateModel,
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    db_ragflow: AsyncSession = Depends(get_db_ragflow)
):
    """
    流式运行thread
    """
    logger.info(f"用户 {current_user.user.get_user_name()} 开始流式运行thread: {thread_id}")
    
    # 刷新LLM配置
    await _refresh_llm_config(request, run_request, db_ragflow)
    
    # 流式运行thread
    stream_generator = ThreadService.create_run_in_stream_service(
        thread_id, 
        run_request
    )
    
    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@agentController.get('/threads/{thread_id}/runs/{run_id}', dependencies=[Depends(CheckOwnershipInterfaceAuth('thread_id', 'LanggraphThread'))])
async def get_run_status(
    request: Request,
    thread_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user)
):
    """
    获取运行状态
    """

    # 获取thread信息进行权限验证
    thread_info = await ThreadService.get_thread_by_id_service(db, thread_id)
    if not thread_info:
        return ResponseUtil.error(msg="Thread不存在")
    
    # 验证用户对智能体的访问权限
    graph_id = thread_info.get('graphId')
    await AgentService.check_user_agent_scope_services(db, current_user, [graph_id])
    
    # 调用服务层方法
    result = await ThreadService.get_run_status_service(thread_id, run_id)
    return ResponseUtil.success(data=result)

@agentController.get('/threads/{thread_id}/runs/{run_id}/join', dependencies=[Depends(CheckOwnershipInterfaceAuth('thread_id', 'LanggraphThread'))])
async def get_run_result(
    request: Request,
    thread_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user)
):
    """
    获取运行结果
    """
    # 获取thread信息进行权限验证
    thread_info = await ThreadService.get_thread_by_id_service(db, thread_id)
    if not thread_info:
        return ResponseUtil.error(msg="Thread不存在")
    
    # 验证用户对智能体的访问权限
    graph_id = thread_info.get('graphId')
    await AgentService.check_user_agent_scope_services(db, current_user, [graph_id])
    
    # 调用服务层方法
    result = await ThreadService.get_run_result_service(thread_id, run_id)
    return ResponseUtil.success(data=result)

@agentController.post('/threads/{thread_id}/history', dependencies=[Depends(CheckOwnershipInterfaceAuth('thread_id', 'LanggraphThread'))])
async def get_thread_history(
    request: Request,
    thread_id: str,
    history_request: ThreadHistoryModel,
    current_user: CurrentUserModel = Depends(LoginService.get_current_user)
):
    """
    获取thread历史记录
    """
    # 获取thread历史记录
    history_result = await ThreadService.get_thread_history_service(
        thread_id, 
        history_request
    )
    
    logger.info(f"用户 {current_user.user.get_user_name()} 成功获取thread历史记录: {thread_id}")
    
    return ResponseUtil.success(data=history_result, msg="获取历史记录成功")


@agentController.post('/threads/search')
async def get_thread_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
    data_scope_sql: str = Depends(GetDataScope('LanggraphThread', user_alias='created_by', self_enforced=True))
):
    """
    搜索thread列表
    """
    # 获取thread列表
    thread_list = await ThreadService.get_thread_list_service(
        request,
        db,
        current_user,
        data_scope_sql
    )
    
    logger.info(f"用户 {current_user.user.get_user_name()} 成功获取thread列表，返回 {len(thread_list)} 条记录")
    
    return JSONResponse(
        status_code=200,
        content=thread_list
    )


