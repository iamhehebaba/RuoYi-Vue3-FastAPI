from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from module_admin.entity.do.ragflow_tenant_llm import RagflowTenantLLM


class RagflowTenantLLMDao:
    """
    Ragflow租户LLM管理模块数据库操作层
    """

    @classmethod
    async def get_ragflow_tenant_llm_by_key(cls, db: AsyncSession, llm_factory: str, llm_name: str) -> Optional[RagflowTenantLLM]:
        """
        根据完整主键获取租户LLM信息

        :param db: orm对象
        :param llm_factory: LLM工厂
        :param llm_name: LLM名称
        :return: 租户LLM信息对象
        """
        llm_info = (await db.execute(
            select(RagflowTenantLLM)
            .where(
                RagflowTenantLLM.llm_factory == llm_factory,
                RagflowTenantLLM.llm_name == llm_name
            )
        )).scalars().first()
        return llm_info

    @classmethod
    async def get_ragflow_tenant_llm_by_model_type(cls, db: AsyncSession, model_type: str) -> List[RagflowTenantLLM]:
        """
        根据模型类型获取LLM列表

        :param db: orm对象
        :param model_type: 模型类型
        :return: LLM列表
        """
        llm_list = (await db.execute(
            select(RagflowTenantLLM)
            .where(
                RagflowTenantLLM.model_type == model_type
            )
            .order_by(RagflowTenantLLM.llm_name)
        )).scalars().all()
        return llm_list