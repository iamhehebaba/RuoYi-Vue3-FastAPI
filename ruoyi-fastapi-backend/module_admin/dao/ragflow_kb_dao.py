from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from module_admin.entity.do.ragflow_kb_do import RagflowKb
from module_admin.entity.vo.ragflow_kb_vo import RagflowKbSearchModel, RagflowKbDeleteModel


class RagflowKbDao:
    """
    Ragflow知识库管理模块数据库操作层
    """

    @classmethod
    async def get_ragflow_kb_by_id(cls, db: AsyncSession, kb_id: str) -> Optional[RagflowKb]:
        """
        根据知识库ID获取知识库信息

        :param db: orm对象
        :param kb_id: 知识库ID
        :return: 知识库信息对象
        """
        kb_info = (await db.execute(select(RagflowKb).where(RagflowKb.id == kb_id))).scalars().first()
        return kb_info

    @classmethod
    async def create_ragflow_kb(cls, db: AsyncSession, kb: RagflowKb) -> RagflowKb:
        """
        创建新的知识库记录

        :param db: orm对象
        :param kb: 知识库对象
        :return: 创建的知识库对象
        """
        db.add(kb)
        await db.commit()
        await db.refresh(kb)
        return kb

    @classmethod
    async def delete_ragflow_kb_dao(cls, db: AsyncSession, kb: RagflowKbDeleteModel):
        """
        删除知识库数据库操作

        :param db: orm对象
        :param kb: 知识库删除对象
        :return:
        """
        await db.execute(delete(RagflowKb).where(RagflowKb.id == kb.id))
        await db.commit()

    @classmethod
    async def get_ragflow_kb_list(cls, db: AsyncSession, data_scope_sql: str) -> List[RagflowKb]:
        """
        获取知识库列表，按created_at降序排序，支持分页

        :param db: orm对象
        :param data_scope_sql: 数据权限SQL
        :return: 知识库列表
        """
        query = select(RagflowKb).where(eval(data_scope_sql))      
        kb_list = (await db.execute(query)).scalars().all()
        return kb_list

    @classmethod
    async def get_ragflow_kb_by_dept_id(cls, db: AsyncSession, dept_id: int) -> List[RagflowKb]:
        """
        根据部门ID获取知识库列表

        :param db: orm对象
        :param dept_id: 部门ID
        :return: 知识库列表
        """
        kb_list = (await db.execute(
            select(RagflowKb)
            .where(RagflowKb.dept_id == dept_id)
            .order_by(RagflowKb.created_at.desc())
        )).scalars().all()
        return kb_list

    @classmethod
    async def get_ragflow_kb_by_user(cls, db: AsyncSession, created_by: str) -> List[RagflowKb]:
        """
        根据创建者获取知识库列表

        :param db: orm对象
        :param created_by: 创建者
        :return: 知识库列表
        """
        kb_list = (await db.execute(
            select(RagflowKb)
            .where(RagflowKb.created_by == created_by)
            .order_by(RagflowKb.created_at.desc())
        )).scalars().all()
        return kb_list