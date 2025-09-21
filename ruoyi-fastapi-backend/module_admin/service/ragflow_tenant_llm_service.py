from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from module_admin.dao.ragflow_tenant_llm_dao import RagflowTenantLLMDao
from module_admin.entity.do.ragflow_tenant_llm import RagflowTenantLLM
from exceptions.exception import ServiceException
from utils.log_util import logger


class RagflowTenantLLMService:
    """
    Ragflow租户LLM管理模块服务层
    """

    @classmethod
    async def get_ragflow_tenant_llm_by_key_service(cls, db: AsyncSession, llm_factory: str, llm_name: str) -> Optional[RagflowTenantLLM]:
        """
        根据完整主键获取租户LLM信息service层

        :param db: orm对象
        :param llm_factory: LLM工厂
        :param llm_name: LLM名称
        :return: 租户LLM信息
        """
        try:
            llm_info = await RagflowTenantLLMDao.get_ragflow_tenant_llm_by_key(db, llm_factory, llm_name)
            return llm_info
        except Exception as e:
            logger.error(f"根据主键获取租户LLM信息时发生错误: {str(e)}")
            raise ServiceException(message="获取租户LLM信息失败")

    @classmethod
    async def get_ragflow_tenant_llm_by_model_type_service(cls, db: AsyncSession, model_type: str) -> List[RagflowTenantLLM]:
        """
        根据模型类型获取LLM列表service层

        :param db: orm对象
        :param model_type: 模型类型
        :return: LLM列表
        """
        try:
            llm_list = await RagflowTenantLLMDao.get_ragflow_tenant_llm_by_model_type(db, model_type)
            return llm_list
        except Exception as e:
            logger.error(f"根据模型类型获取LLM列表时发生错误: {str(e)}")
            raise ServiceException(message="获取LLM列表失败")

