from datetime import datetime
from fastapi import APIRouter, Depends, Request
from pydantic_validation_decorator import ValidateFields
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from config.enums import BusinessType
from config.get_db import get_db
from module_admin.annotation.log_annotation import Log
from module_admin.aspect.interface_auth import CheckUserInterfaceAuth
from module_admin.entity.vo.llm_config_vo import DeleteLlmConfigModel, LlmConfigModel, LlmConfigQueryModel
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.llm_config_service import LlmConfigService
from module_admin.service.login_service import LoginService
from utils.log_util import logger
from utils.page_util import PageResponseModel
from utils.response_util import ResponseUtil


llmConfigController = APIRouter(prefix='/system/llmconfig', dependencies=[Depends(LoginService.get_current_user)])


@llmConfigController.get(
    '/list',
    response_model=List[LlmConfigModel],
    dependencies=[Depends(CheckUserInterfaceAuth('model:model:list'))]
)
async def get_system_llm_config_list(
    request: Request,
    llm_config_query: LlmConfigQueryModel = Depends(LlmConfigQueryModel.as_query),
    query_db: AsyncSession = Depends(get_db),
):
    """
    获取LLM配置列表
    """
    llm_config_query_result = await LlmConfigService.get_llm_config_list_services(
        query_db, llm_config_query
    )
    logger.info('获取成功')

    return ResponseUtil.success(data=llm_config_query_result)


@llmConfigController.post('', dependencies=[Depends(CheckUserInterfaceAuth('model:model:add'))])
@ValidateFields(validate_model='add_llm_config')
@Log(title='LLM配置管理', business_type=BusinessType.INSERT)
async def add_system_llm_config(
    request: Request,
    add_llm_config: LlmConfigModel,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    新增LLM配置
    """
    add_llm_config.created_by = current_user.user.user_name
    add_llm_config.created_at = datetime.now()
    add_llm_config_result = await LlmConfigService.add_llm_config_services(query_db, add_llm_config)
    logger.info(add_llm_config_result.message)

    return ResponseUtil.success(msg=add_llm_config_result.message)


@llmConfigController.put('', dependencies=[Depends(CheckUserInterfaceAuth('model:model:add'))])
@ValidateFields(validate_model='edit_llm_config')
@Log(title='LLM配置管理', business_type=BusinessType.UPDATE)
async def edit_system_llm_config(
    request: Request,
    edit_llm_config: LlmConfigModel,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    编辑LLM配置
    """
    edit_llm_config_result = await LlmConfigService.edit_llm_config_services(query_db, edit_llm_config)
    logger.info(edit_llm_config_result.message)

    return ResponseUtil.success(msg=edit_llm_config_result.message)


@llmConfigController.delete('/{config_ids}', dependencies=[Depends(CheckUserInterfaceAuth('model:model:remove'))])
@Log(title='LLM配置管理', business_type=BusinessType.DELETE)
async def delete_system_llm_config(
    request: Request,
    config_ids: str,
    query_db: AsyncSession = Depends(get_db),
    current_user: CurrentUserModel = Depends(LoginService.get_current_user),
):
    """
    删除LLM配置
    """
    delete_llm_config = DeleteLlmConfigModel(configIds=config_ids)
    delete_llm_config_result = await LlmConfigService.delete_llm_config_services(query_db, delete_llm_config)
    logger.info(delete_llm_config_result.message)

    return ResponseUtil.success(msg=delete_llm_config_result.message)


@llmConfigController.get(
    '/{config_id}',
    response_model=LlmConfigModel,
    dependencies=[Depends(CheckUserInterfaceAuth('model:model:list'))]
)
async def query_detail_system_llm_config(
    request: Request,
    config_id: int,
    query_db: AsyncSession = Depends(get_db),
):
    """
    获取LLM配置详细信息
    """
    detail_llm_config_result = await LlmConfigService.llm_config_detail_services(query_db, config_id)
    logger.info(f'获取config_id为{config_id}的信息成功')

    return ResponseUtil.success(data=detail_llm_config_result)