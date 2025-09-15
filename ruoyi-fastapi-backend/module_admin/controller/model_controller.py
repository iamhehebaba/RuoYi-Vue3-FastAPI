from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from config.get_db import get_db
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.login_service import LoginService
from module_admin.service.model_service import ModelService
from utils.response_util import ResponseUtil
from utils.log_util import logger
from fastapi import HTTPException
from typing import Dict, Any

modelController = APIRouter(prefix='/ragflow', tags=['模型管理'])

# 任何具有模型添加权限的用户都可以查看系统的LLM factories
@modelController.get('/v1/llm/factories', dependencies=[Depends(CheckUserInterfaceAuth(['system:model:add']))])
async def get_llm_factories(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    列出所有LLM factories：利用RagflowClient向ragflow转发请求http://{{RAGFLOW_API_URL}}/v1/llm/factories,然后再把请求结果返回
    """

    logger.info(f"用户 {current_user.user.user_name} 请求获取LLM factories列表")
    
    # 调用ModelService获取LLM factories数据
    llm_factories_data = await ModelService.get_llm_factories_service()
    
    logger.info("成功获取LLM factories列表")
    return ResponseUtil.success(data=llm_factories_data, msg="获取LLM factories列表成功")


# 任何具有模型添加权限的用户都可以查看自己的LLMs
@modelController.get('/v1/llm/my_llms', dependencies=[Depends(CheckUserInterfaceAuth(['system:model:add', 'system:model:list', 'system:model:remove', 'system:model:config'], False))])
async def get_my_llms(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    获取我的LLMs：利用RagflowClient向ragflow转发请求http://{{RAGFLOW_API_URL}}/v1/llm/my_llms,然后再把请求结果返回
    """

    logger.info(f"用户 {current_user.user.user_name} 请求获取我的LLMs列表")
    
    # 调用ModelService获取我的LLMs数据
    my_llms_data = await ModelService.get_my_llms_service()
    
    logger.info("成功获取我的LLMs列表")
    return ResponseUtil.success(data=my_llms_data, msg="获取我的LLMs列表成功")


# 任何具有模型删除权限的用户都可以删除LLM
@modelController.post('/v1/llm/delete_llm', dependencies=[Depends(CheckUserInterfaceAuth(['system:model:remove']))])
async def delete_llm(
    request: Request,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    删除LLM：利用RagflowClient向ragflow转发请求http://{{RAGFLOW_API_URL}}/v1/llm/delete_llm,然后再把请求结果返回
    """

    logger.info(f"用户 {current_user.user.user_name} 请求删除LLM，请求数据: {payload}")
    
    # 调用ModelService删除LLM
    delete_result = await ModelService.delete_llm_service(payload)
    
    logger.info("成功删除LLM")
    return ResponseUtil.success(data=delete_result, msg="删除LLM成功")
