from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, Response
from typing import List, Any
from datetime import datetime
from module_admin.dao.ragflow_kb_dao import RagflowKbDao
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.entity.do.ragflow_kb_do import RagflowKb
from exceptions.exception import ServiceException, PermissionException
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
    async def create_ragflow_kb_service(cls, db: AsyncSession, kb_id: str, dept_id: int, user_id: int, user_name: str) -> RagflowKb:
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
                user_id=user_id,
                created_by=user_name,
                created_at=datetime.now()
            )
            
            # 保存到数据库
            created_kb = await RagflowKbDao.create_ragflow_kb(db, kb)
            
            # 返回响应模型
            logger.info(f"用户 {user_name} 创建知识库 {kb_id} 成功")
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
    async def post_process_create_kb(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        payload: Any) -> Any:

        """
        创建kb后，保存kb信息到本地表ragflow_kb

        :param full_path: 知识库路径
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param payload: 创建kb的响应数据
        :return: 原来的request
        """

        
        # 检查payload是否为空或结构不完整
        if not payload or not isinstance(payload, dict):
            logger.warning("payload为空或格式不正确")
            return payload
            
        if "data" not in payload or not isinstance(payload["data"], dict):
            logger.warning("payload.data不存在或格式不正确")
            return payload
            
        if "kb_id" not in payload["data"] or not isinstance(payload["data"]["kb_id"], str):
            logger.warning("payload.data.kb_id不存在或格式不正确")
            raise ServiceException(message="创建知识库的响应中，payload.data.kb_id不存在或响应格式不正确")
        
        kb_id = payload["data"]["kb_id"]

        await cls.create_ragflow_kb_service(query_db, kb_id, current_user.user.dept.dept_id, current_user.user.user_id, current_user.user.user_name)
        
        return payload

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
        根据权限设置（数据范围），通过service层过滤知识库列表

        :param full_path: 知识库路径
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param payload: 知识库列表
        :return: 过滤后的知识库列表
        """
        kb_list = await cls.get_ragflow_kb_list_service(query_db, data_scope_sql)
        kb_id_list = [kb.id for kb in kb_list]
        
        # 检查payload是否为空或结构不完整
        if not payload or not isinstance(payload, dict):
            logger.warning("payload为空或格式不正确")
            return payload
            
        if "data" not in payload or not isinstance(payload["data"], dict):
            logger.warning("payload.data不存在或格式不正确")
            return payload
            
        if "kbs" not in payload["data"] or not isinstance(payload["data"]["kbs"], list):
            logger.warning("payload.data.kbs不存在或格式不正确")
            return payload
        
        # 过滤kbs列表
        original_kbs = payload["data"]["kbs"]
        filtered_kbs = []
        
        for kb in original_kbs:
            if isinstance(kb, dict) and "id" in kb:
                kb_id = kb["id"]
                if kb_id in kb_id_list:
                    # 保留有权限的知识库
                    filtered_kbs.append(kb)
                else:
                    # 移除无权限的知识库并记录日志
                    logger.info(f"用户 {current_user.user.user_name} 无权限访问知识库: id={kb_id}，已从列表中移除")
            else:
                # kb结构不正确，记录日志但不添加到结果中
                logger.warning(f"知识库数据结构不正确: {kb}")
        
        # 更新payload
        payload["data"]["kbs"] = filtered_kbs
        payload["data"]["total"] = len(filtered_kbs)
        
        logger.info(f"知识库权限过滤完成，原始数量: {len(original_kbs)}, 过滤后数量: {len(filtered_kbs)}")
        
        return payload

    @classmethod
    async def check_ragflow_kb_permission(
        cls, 
        full_path: str, 
        request: Request,     
        query_db: AsyncSession,
        current_user: CurrentUserModel,    
        data_scope_sql: str,
        body: Any) -> Any:

        """
        根据权限设置（数据范围），通过service层检查用户是否有操作权限
        支持从form data或payload中获取kb_id

        :param full_path: 知识库路径
        :param request: 请求对象
        :param query_db: orm对象
        :param current_user: 当前用户
        :param data_scope_sql: 数据权限SQL
        :param body: 请求体数据，
        :return: 原始payload数据
        """
        kb_list = await cls.get_ragflow_kb_list_service(query_db, data_scope_sql)
        kb_id_list = [kb.id for kb in kb_list]
        
        target_kb_id = None
        
        # 尝试从form data中获取kb_id
        if request.method == 'POST':
            try:
                form_data = await request.form()
                if "kb_id" in form_data:
                    target_kb_id = form_data["kb_id"]
                    logger.info(f"从form data中获取到kb_id: {target_kb_id}")
            except Exception as e:
                logger.debug(f"无法解析form data: {str(e)}")
            
            # 如果form data中没有kb_id，尝试从payload中获取
            if not target_kb_id:
                payload = None
                if body:
                    try:
                        import json
                        payload = json.loads(body.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        payload = body
                if payload and isinstance(payload, dict) and "kb_id" in payload:
                    target_kb_id = payload["kb_id"]
                    logger.info(f"从payload中获取到kb_id: {target_kb_id}")
        elif request.method == 'GET':
            if 'kb_id' in request.query_params:
                target_kb_id = request.query_params['kb_id']
                logger.info(f"从query params中获取到kb_id: {target_kb_id}")
        
        # 如果仍然没有找到kb_id，记录警告并返回原始数据
        if not target_kb_id:
            logger.warning(f"未能从request中获取到kb_id, method: {request.method}")
            return request
        
        # 检查权限
        if target_kb_id not in kb_id_list:
            logger.info(f"用户 {current_user.user.user_name} 无权限访问知识库: id={target_kb_id}, 退出处理")
            raise PermissionException(data='', message=f'该用户无此知识库权限: {target_kb_id}')
        
        logger.info(f"用户 {current_user.user.user_name} 有权限访问知识库: id={target_kb_id}")
        return request