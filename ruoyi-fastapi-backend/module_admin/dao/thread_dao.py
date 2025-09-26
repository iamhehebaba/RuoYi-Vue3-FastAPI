from sqlalchemy import bindparam, func, or_, select, update  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from module_admin.entity.do.langgraphthread_do import LanggraphThread
from module_admin.entity.vo.thread_vo import ThreadSearchModel


class ThreadDao:
    """
    Thread管理模块数据库操作层
    """

    @classmethod
    async def get_thread_by_id(cls, db: AsyncSession, thread_id: str) -> Optional[LanggraphThread]:
        """
        根据thread_id获取thread信息

        :param db: orm对象
        :param thread_id: thread ID
        :return: thread信息对象
        """
        thread_info = (await db.execute(select(LanggraphThread).where(LanggraphThread.thread_id == thread_id))).scalars().first()
        return thread_info

    @classmethod
    async def create_thread(cls, db: AsyncSession, thread: LanggraphThread) -> LanggraphThread:
        """
        创建新的thread记录

        :param db: orm对象
        :param thread: thread对象
        :return: 创建的thread对象
        """
        db.add(thread)
        # await db.flush()  # 确保对象在Session中持久化
        # await db.refresh(thread)
        return thread

    @classmethod
    async def get_threads_by_graph_id(cls, db: AsyncSession, graph_id: str):
        """
        根据graph_id获取所有相关的thread列表

        :param db: orm对象
        :param graph_id: 智能体图ID
        :return: thread列表
        """
        threads = (await db.execute(
            select(LanggraphThread)
            .where(LanggraphThread.graph_id == graph_id)
            .order_by(LanggraphThread.created_at.desc())
        )).scalars().all()
        return threads

    @classmethod
    async def get_threads_by_user(cls, db: AsyncSession, created_by: str):
        """
        根据创建者获取thread列表

        :param db: orm对象
        :param created_by: 创建者
        :return: thread列表
        """
        threads = (await db.execute(
            select(LanggraphThread)
            .where(LanggraphThread.created_by == created_by)
            .order_by(LanggraphThread.created_at.desc())
        )).scalars().all()
        return threads

    @classmethod
    async def get_thread_list(cls, db: AsyncSession, request: ThreadSearchModel, data_scope_sql: str):
        """
        获取thread列表，按created_at降序排序，支持分页

        :param db: orm对象
        :param limit: 限制返回的记录数量
        :param offset: 偏移量
        :return: thread列表
        """
        threads = (await db.execute(
            select(LanggraphThread)
            .where(LanggraphThread.graph_id == request.metadata.get("graph_id") if request.metadata and request.metadata.get("graph_id") is not None else 1 == 1)
            .where(eval(data_scope_sql))
            .order_by(LanggraphThread.created_at.desc())
            .limit(request.limit)
            .offset(request.offset)
        )).scalars().all()
        return threads