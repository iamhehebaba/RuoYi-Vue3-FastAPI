from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from module_admin.entity.do.llm_config_do import LlmConfig
from module_admin.entity.vo.llm_config_vo import LlmConfigModel, LlmConfigPageQueryModel
from utils.page_util import PageUtil


class LlmConfigDao:
    """
    LLM配置管理模块数据库操作层
    """

    @classmethod
    async def get_llm_config_by_id(cls, db: AsyncSession, config_id: int):
        """
        根据配置id获取LLM配置信息

        :param db: orm对象
        :param config_id: 配置id
        :return: LLM配置信息对象（排除api_key字段）
        """
        llm_config_info = (
            await db.execute(
                select(
                    LlmConfig.config_id,
                    LlmConfig.llm_factory,
                    LlmConfig.llm_name,
                    LlmConfig.model_type,
                    LlmConfig.api_base,
                    LlmConfig.created_by,
                    LlmConfig.created_at
                ).where(LlmConfig.config_id == config_id)
            )
        ).first()

        return llm_config_info

    @classmethod
    async def get_llm_config_detail_by_info(cls, db: AsyncSession, llm_config: LlmConfigModel):
        """
        根据LLM配置参数获取配置信息

        :param db: orm对象
        :param llm_config: LLM配置参数对象
        :return: LLM配置信息对象
        """
        llm_config_info = (
            await db.execute(
                select(LlmConfig).where(
                    LlmConfig.llm_factory == llm_config.llm_factory if llm_config.llm_factory else True,
                    LlmConfig.llm_name == llm_config.llm_name if llm_config.llm_name else True,
                    LlmConfig.model_type == llm_config.model_type if llm_config.model_type else True,
                )
            )
        ).scalars().first()

        return llm_config_info

    @classmethod
    async def get_llm_config_list(cls, db: AsyncSession, query_object: LlmConfigModel):
        """
        根据查询参数获取LLM配置列表信息

        :param db: orm对象
        :param query_object: 查询参数对象
        :return: LLM配置列表信息对象数组（排除api_key字段）
        """
        llm_config_result = (
            await db.execute(
                select(
                    LlmConfig.config_id,
                    LlmConfig.llm_factory,
                    LlmConfig.llm_name,
                    LlmConfig.model_type,
                    LlmConfig.api_base,
                    LlmConfig.created_by,
                    LlmConfig.created_at
                ).where(
                    LlmConfig.config_id == query_object.config_id if query_object.config_id is not None else True,
                    LlmConfig.llm_factory.like(f'%{query_object.llm_factory}%') if query_object.llm_factory else True,
                    LlmConfig.llm_name.like(f'%{query_object.llm_name}%') if query_object.llm_name else True,
                    LlmConfig.model_type == query_object.model_type if query_object.model_type else True,
                )
                .order_by(LlmConfig.llm_factory.asc())
            )
        ).all()

        return llm_config_result

    @classmethod
    async def get_llm_config_list_by_page(cls, db: AsyncSession, query_object: LlmConfigPageQueryModel):
        """
        根据查询参数分页获取LLM配置列表信息

        :param db: orm对象
        :param query_object: 查询参数对象
        :return: LLM配置列表信息对象
        """
        # 查询数据
        llm_config_result = (
            await db.execute(
                select(LlmConfig)
                .where(
                    LlmConfig.config_id == query_object.config_id if query_object.config_id is not None else True,
                    LlmConfig.llm_factory.like(f'%{query_object.llm_factory}%') if query_object.llm_factory else True,
                    LlmConfig.llm_name.like(f'%{query_object.llm_name}%') if query_object.llm_name else True,
                    LlmConfig.model_type == query_object.model_type if query_object.model_type else True,
                )
                .order_by(LlmConfig.config_id.desc())
                .offset(PageUtil.get_page_index(query_object.page_num, query_object.page_size))
                .limit(query_object.page_size)
            )
        ).scalars().all()

        # 查询总数
        count_result = (
            await db.execute(
                select(func.count(LlmConfig.config_id))
                .where(
                    LlmConfig.config_id == query_object.config_id if query_object.config_id is not None else True,
                    LlmConfig.llm_factory.like(f'%{query_object.llm_factory}%') if query_object.llm_factory else True,
                    LlmConfig.llm_name.like(f'%{query_object.llm_name}%') if query_object.llm_name else True,
                    LlmConfig.model_type == query_object.model_type if query_object.model_type else True,
                )
            )
        ).scalar()

        return llm_config_result, count_result

    @classmethod
    async def add_llm_config_dao(cls, db: AsyncSession, llm_config: LlmConfigModel):
        """
        新增LLM配置数据库操作

        :param db: orm对象
        :param llm_config: LLM配置对象
        :return: 新增校验结果
        """
        db_llm_config = LlmConfig(**llm_config.model_dump())
        db.add(db_llm_config)
        await db.flush()

        return db_llm_config

    @classmethod
    async def edit_llm_config_dao(cls, db: AsyncSession, llm_config: dict):
        """
        编辑LLM配置数据库操作

        :param db: orm对象
        :param llm_config: 需要更新的LLM配置字典
        :return: 编辑校验结果
        """

        await db.execute(update(LlmConfig), [llm_config])

    @classmethod
    async def delete_llm_config_dao(cls, db: AsyncSession, llm_config: LlmConfigModel):
        """
        删除LLM配置数据库操作

        :param db: orm对象
        :param llm_config: LLM配置对象
        :return: 删除校验结果
        """
        await db.execute(delete(LlmConfig).where(LlmConfig.config_id == llm_config.config_id))

    @classmethod
    async def delete_llm_config_dao_by_ids(cls, db: AsyncSession, config_ids: List[int]):
        """
        根据配置id列表批量删除LLM配置数据库操作

        :param db: orm对象
        :param config_ids: 配置id列表
        :return: 删除校验结果
        """
        await db.execute(delete(LlmConfig).where(LlmConfig.config_id.in_(config_ids)))