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


