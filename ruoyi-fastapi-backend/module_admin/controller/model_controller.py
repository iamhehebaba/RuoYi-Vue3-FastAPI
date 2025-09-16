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
@modelController.get('/v1/llm/factories', dependencies=[Depends(CheckUserInterfaceAuth(['model:model:add']))])
async def get_llm_factories(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    列出所有LLM factories
    """

    logger.info(f"用户 {current_user.user.user_name} 请求获取LLM factories列表")
    
    # 调用ModelService获取LLM factories数据
    llm_factories_data = await ModelService.get_llm_factories_service()
    
    logger.info("成功获取LLM factories列表")
    return ResponseUtil.success(data=llm_factories_data, msg="获取LLM factories列表成功")


# 任何具有模型添加权限的用户都可以查看自己的LLMs
@modelController.get('/v1/llm/my_llms', dependencies=[Depends(CheckUserInterfaceAuth(['model:model:add', 'model:model:list', 'model:model:remove', 'model:model:config'], False))])
async def get_my_llms(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    获取我的LLMs
    """

    logger.info(f"用户 {current_user.user.user_name} 请求获取我的LLMs列表")
    
    # 调用ModelService获取我的LLMs数据
    my_llms_data = await ModelService.get_my_llms_service()
    
    logger.info("成功获取我的LLMs列表")
    return ResponseUtil.success(data=my_llms_data, msg="获取我的LLMs列表成功")


# 任何具有模型删除权限的用户都可以删除LLM
@modelController.post('/v1/llm/delete_llm', dependencies=[Depends(CheckUserInterfaceAuth(['model:model:remove']))])
async def delete_llm(
    request: Request,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    删除LLM
    """

    logger.info(f"用户 {current_user.user.user_name} 请求删除LLM，请求数据: {payload}")
    
    # 调用ModelService删除LLM
    delete_result = await ModelService.delete_llm_service(payload)
    
    logger.info("成功删除LLM")
    return ResponseUtil.success(data=delete_result, msg="删除LLM成功")


# 任何具有模型添加权限的用户都可以设置API Key
@modelController.post('/v1/llm/set_api_key', dependencies=[Depends(CheckUserInterfaceAuth(['model:model:add']))])
async def set_api_key(
    request: Request,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    设置API Key
    """

    logger.info(f"用户 {current_user.user.user_name} 请求设置API Key，请求数据: {payload}")
    
    # 调用ModelService设置API Key
    set_result = await ModelService.set_api_key_service(payload)
    
    logger.info("成功设置API Key")
    return ResponseUtil.success(data=set_result, msg="设置API Key成功")


# 任何具有模型配置权限的用户都可以设置默认模型
@modelController.post('/v1/llm/set_default_model', dependencies=[Depends(CheckUserInterfaceAuth(['model:model:config']))])
async def set_default_model(
    request: Request,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    设置默认模型
    """

    logger.info(f"用户 {current_user.user.user_name} 请求设置默认模型，请求数据: {payload}")
    
    # 调用ModelService设置默认模型
    set_result = await ModelService.set_default_model_service(payload)
    
    logger.info("成功设置默认模型")
    return ResponseUtil.success(data=set_result, msg="设置默认模型成功")
