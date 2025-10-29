from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from config.constant import CommonConstant
from exceptions.exception import ServiceException
from module_admin.dao.llm_config_dao import LlmConfigDao
from module_admin.entity.vo.common_vo import CrudResponseModel
from module_admin.entity.vo.llm_config_vo import DeleteLlmConfigModel, LlmConfigModel, LlmConfigPageQueryModel
from utils.common_util import CamelCaseUtil
from utils.page_util import PageResponseModel


class LlmConfigService:
    """
    LLM配置管理模块服务层
    """

    @classmethod
    async def get_llm_config_list_services(cls, query_db: AsyncSession, query_object: LlmConfigModel):
        """
        获取LLM配置列表信息service

        :param query_db: orm对象
        :param query_object: 查询参数对象
        :return: LLM配置列表信息对象
        """
        llm_config_list_result = await LlmConfigDao.get_llm_config_list(query_db, query_object)

        return CamelCaseUtil.transform_result(llm_config_list_result)

    @classmethod
    async def get_llm_config_list_by_page_services(cls, query_db: AsyncSession, query_object: LlmConfigPageQueryModel):
        """
        根据查询参数分页获取LLM配置列表信息service

        :param query_db: orm对象
        :param query_object: 查询参数对象
        :return: LLM配置列表信息对象
        """
        llm_config_list_result, count = await LlmConfigDao.get_llm_config_list_by_page(query_db, query_object)
        llm_config_list_result_dict = CamelCaseUtil.transform_result(llm_config_list_result)

        return PageResponseModel(
            **{
                'rows': llm_config_list_result_dict,
                'page_num': query_object.page_num,
                'page_size': query_object.page_size,
                'total': count,
                'has_next': query_object.page_num * query_object.page_size < count
            }
        )

    @classmethod
    async def check_llm_config_unique_services(cls, query_db: AsyncSession, page_object: LlmConfigModel):
        """
        校验LLM配置是否唯一service

        :param query_db: orm对象
        :param page_object: LLM配置对象
        :return: 校验结果
        """
        config_id = -1 if page_object.config_id is None else page_object.config_id
        llm_config = await LlmConfigDao.get_llm_config_detail_by_info(
            db=query_db, 
            llm_factory=page_object.llm_factory,
            llm_name=page_object.llm_name,
            model_type=page_object.model_type
        )
        if llm_config and llm_config.config_id != config_id:
            return CommonConstant.NOT_UNIQUE
        return CommonConstant.UNIQUE

    @classmethod
    async def add_llm_config_services(cls, query_db: AsyncSession, page_object: LlmConfigModel):
        """
        新增LLM配置信息service

        :param query_db: orm对象
        :param page_object: 新增LLM配置对象
        :return: 新增LLM配置校验结果
        """
        if not await cls.check_llm_config_unique_services(query_db, page_object):
            raise ServiceException(
                message=f'新增LLM配置失败，配置 {page_object.llm_factory}-{page_object.llm_name}-{page_object.model_type} 已存在'
            )
        
        # 设置创建时间
        page_object.created_at = datetime.now()
        
        try:
            await LlmConfigDao.add_llm_config_dao(query_db, page_object)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='新增成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def edit_llm_config_services(cls, query_db: AsyncSession, page_object: LlmConfigModel):
        """
        编辑LLM配置信息service

        :param query_db: orm对象
        :param page_object: 编辑LLM配置对象
        :return: 编辑LLM配置校验结果
        """
        if not await cls.check_llm_config_unique_services(query_db, page_object):
            raise ServiceException(
                message=f'修改LLM配置失败，配置 {page_object.llm_factory}-{page_object.llm_name}-{page_object.model_type} 已存在'
            )
        
        try:
            edit_llm_config = page_object.model_dump(exclude_unset=True)
            await LlmConfigDao.edit_llm_config_dao(query_db, edit_llm_config)
            await query_db.commit()
            return CrudResponseModel(is_success=True, message='更新成功')
        except Exception as e:
            await query_db.rollback()
            raise e

    @classmethod
    async def delete_llm_config_services(cls, query_db: AsyncSession, page_object: DeleteLlmConfigModel):
        """
        删除LLM配置信息service

        :param query_db: orm对象
        :param page_object: 删除LLM配置对象
        :return: 删除LLM配置校验结果
        """
        if page_object.config_ids:
            config_id_list = [int(config_id) for config_id in page_object.config_ids.split(',')]
            try:
                await LlmConfigDao.delete_llm_config_dao_by_ids(query_db, config_id_list)
                await query_db.commit()
                return CrudResponseModel(is_success=True, message='删除成功')
            except Exception as e:
                await query_db.rollback()
                raise e
        else:
            raise ServiceException(message='传入配置id为空')

    @classmethod
    async def llm_config_detail_services(cls, query_db: AsyncSession, config_id: int):
        """
        获取LLM配置详细信息service

        :param query_db: orm对象
        :param config_id: 配置id
        :return: 配置id对应的信息
        """
        llm_config = await LlmConfigDao.get_llm_config_by_id(query_db, config_id=config_id)
        if llm_config:
            result = CamelCaseUtil.transform_result(llm_config)

        else:
            result = LlmConfigModel(**dict())

        return result