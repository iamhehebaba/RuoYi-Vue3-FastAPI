from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from module_admin.entity.do.langgraphthread_do import LanggraphThread


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
        await db.commit()
        await db.refresh(thread)
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