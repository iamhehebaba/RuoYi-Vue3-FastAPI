from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, Response
from typing import List, Any
from datetime import datetime
from module_admin.dao.ragflow_kb_dao import RagflowKbDao
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.entity.do.ragflow_kb_do import RagflowKb
from exceptions.exception import ServiceException
from utils.response_util import ResponseUtil
from utils.log_util import logger


class RagflowKbService:
    """
    Ragflow知识库管理模块服务层
    """

    @classmethod
    async def get_ragflow_kb_by_id_service(cls, db: AsyncSession, kb_id: str) -> RagflowKb:
        """
        根据知识库ID获取知识库信息service层

        :param db: orm对象
        :param kb_id: 知识库ID
        :return: 知识库信息
        """
        kb_info = await RagflowKbDao.get_ragflow_kb_by_id(db, kb_id)
        if kb_info:
            return kb_info
        return None

    @classmethod
    async def create_ragflow_kb_service(cls, db: AsyncSession, kb_id: str, dept_id: int, current_user: str) -> RagflowKb:
        """
        创建知识库service层

        :param db: orm对象
        :param kb_id: 知识库ID
        :param dept_id: 部门ID
        :param current_user: 当前用户
        :return: 创建的知识库信息
        """
        try:
            # 检查知识库ID是否已存在
            existing_kb = await RagflowKbDao.get_ragflow_kb_by_id(db, kb_id)
            if existing_kb:
                raise ServiceException(message=f"知识库ID {kb_id} 已存在")

            # 创建知识库对象
            kb = RagflowKb(
                id=kb_id,
                dept_id=dept_id,
                created_by=current_user,
                created_at=datetime.now()
            )
            
            # 保存到数据库
            created_kb = await RagflowKbDao.create_ragflow_kb(db, kb)
            
            # 返回响应模型
            
            logger.info(f"用户 {current_user} 创建知识库 {kb_id} 成功")
            return created_kb
            
        except Exception as e:
            logger.error(f"创建知识库时发生未知错误: {str(e)}")
            raise ServiceException(message="创建知识库失败")

    @classmethod
    async def delete_ragflow_kb_service(cls, db: AsyncSession, kb_id: str, current_user: str):
        """
        删除知识库service层

        :param db: orm对象
        :param kb_id: 知识库ID
        :param current_user: 当前用户
        :return:
        """
        try:
            # 检查知识库是否存在
            existing_kb = await RagflowKbDao.get_ragflow_kb_by_id(db, kb_id)
            if not existing_kb:
                raise ServiceException(message=f"知识库ID {kb_id} 不存在")
            
            # 执行删除操作
            await RagflowKbDao.delete_ragflow_kb_dao(db, kb_id)
            
            logger.info(f"用户 {current_user} 删除知识库 {kb_id} 成功")
            
        except Exception as e:
            logger.error(f"删除知识库时发生未知错误: {str(e)}")
            raise ServiceException(message="删除知识库失败")

    @classmethod
    async def get_ragflow_kb_list_service(cls, db: AsyncSession, data_scope_sql: str) -> List[RagflowKb]:
        """
        获取知识库列表service层

        :param db: orm对象
        :param request: 搜索请求参数
        :param data_scope_sql: 数据权限SQL
        :return: 知识库列表
        """
        try:
            kb_list = await RagflowKbDao.get_ragflow_kb_list(db, data_scope_sql)
            return kb_list
            
        except Exception as e:
            logger.error(f"获取知识库列表时发生错误: {str(e)}")
            raise ServiceException(message="获取知识库列表失败")

    @classmethod
    async def get_ragflow_kb_by_dept_id_service(cls, db: AsyncSession, dept_id: int) -> List[RagflowKb]:
        """
        根据部门ID获取知识库列表service层

        :param db: orm对象
        :param dept_id: 部门ID
        :return: 知识库列表
        """
        try:
            kb_list = await RagflowKbDao.get_ragflow_kb_by_dept_id(db, dept_id)
            return kb_list
            
        except Exception as e:
            logger.error(f"根据部门ID获取知识库列表时发生错误: {str(e)}")
            raise ServiceException(message="获取知识库列表失败")

    @classmethod
    async def get_ragflow_kb_by_user_service(cls, db: AsyncSession, created_by: str) -> List[RagflowKb]:
        """
        根据创建者获取知识库列表service层

        :param db: orm对象
        :param created_by: 创建者
        :return: 知识库列表
        """
        try:
            kb_list = await RagflowKbDao.get_ragflow_kb_by_user(db, created_by)
            return kb_list
            
        except Exception as e:
            logger.error(f"根据创建者获取知识库列表时发生错误: {str(e)}")
            raise ServiceException(message="获取知识库列表失败")

    @classmethod
    async def filter_ragflow_kb_by_permission(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        payload: Any) -> Any:

        """
        过滤知识库列表根据权限service层

        :param full_path: 知识库路径
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param payload: 知识库列表
        :return: 过滤后的知识库列表
        """
        return payload