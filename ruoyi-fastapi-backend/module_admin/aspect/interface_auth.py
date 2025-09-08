from fastapi import Depends, Request
from typing import List, Union, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from exceptions.exception import PermissionException
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.login_service import LoginService
from config.get_db import get_db
import importlib


class CheckUserInterfaceAuth:
    """
    校验当前用户是否具有相应的接口权限
    """

    def __init__(self, perm: Union[str, List], is_strict: bool = False):
        """
        校验当前用户是否具有相应的接口权限

        :param perm: 权限标识
        :param is_strict: 当传入的权限标识是list类型时，是否开启严格模式，开启表示会校验列表中的每一个权限标识，所有的校验结果都需要为True才会通过
        """
        self.perm = perm
        self.is_strict = is_strict

    def __call__(self, current_user: CurrentUserModel = Depends(LoginService.get_current_user)):
        user_auth_list = current_user.permissions
        if '*:*:*' in user_auth_list:
            return True
        if isinstance(self.perm, str):
            if self.perm in user_auth_list:
                return True
        if isinstance(self.perm, list):
            if self.is_strict:
                if all([perm_str in user_auth_list for perm_str in self.perm]):
                    return True
            else:
                if any([perm_str in user_auth_list for perm_str in self.perm]):
                    return True
        raise PermissionException(data='', message='该用户无此接口权限')


class CheckRoleInterfaceAuth:
    """
    根据角色校验当前用户是否具有相应的接口权限
    """

    def __init__(self, role_key: Union[str, List], is_strict: bool = False):
        """
        根据角色校验当前用户是否具有相应的接口权限

        :param role_key: 角色标识
        :param is_strict: 当传入的角色标识是list类型时，是否开启严格模式，开启表示会校验列表中的每一个角色标识，所有的校验结果都需要为True才会通过
        """
        self.role_key = role_key
        self.is_strict = is_strict

    def __call__(self, current_user: CurrentUserModel = Depends(LoginService.get_current_user)):
        user_role_list = current_user.user.role
        user_role_key_list = [role.role_key for role in user_role_list]
        if isinstance(self.role_key, str):
            if self.role_key in user_role_key_list:
                return True
        if isinstance(self.role_key, list):
            if self.is_strict:
                if all([role_key_str in user_role_key_list for role_key_str in self.role_key]):
                    return True
            else:
                if any([role_key_str in user_role_key_list for role_key_str in self.role_key]):
                    return True
        raise PermissionException(data='', message='该用户无此接口权限')

class CheckOwnershipInterfaceAuth:
    """
    校验当前用户是否是创建者
    """

    def __init__(
        self, 
        search_key_alias: str,
        query_alias: Optional[str] = '',
        created_by_alias: Optional[str] = 'created_by',
    ):
        """
        校验当前用户是否是创建者:通过搜索query_alias表的search_key_alias字段等于search_value, 并判断搜索结果记录的created_by_alias字段是否等于当前用户的user_id
        :param search_key_alias: query_alias表待搜索的字段别名
        :param query_alias: 所要查询表对应的sqlalchemy模型名称，默认为''
        :param created_by_alias: 创建者字段别名，默认为'created_by'
        """
        self.search_key_alias = search_key_alias
        self.query_alias = query_alias
        self.created_by_alias = created_by_alias

    async def __call__(
        self, 
        request: Request,
        current_user: CurrentUserModel = Depends(LoginService.get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        # 从URL路径参数中获取search_value
        search_value = request.path_params.get(self.search_key_alias)
        if not search_value:
            raise PermissionException(data='', message='缺少必要的路径参数')
        
        # 动态导入模型类
        try:
            # 根据query_alias动态导入对应的模型
            if self.query_alias:
                # 假设模型在module_admin.entity.do中
                module_path = f'module_admin.entity.do.{self.query_alias.lower()}_do'
                module = importlib.import_module(module_path)
                model_class = getattr(module, self.query_alias)
            else:
                raise PermissionException(data='', message='未指定查询模型')
        except (ImportError, AttributeError):
            raise PermissionException(data='', message='无效的查询模型')
        
        # 检查模型是否有指定的字段
        if not hasattr(model_class, self.search_key_alias):
            raise PermissionException(data='', message=f'模型{self.query_alias}不存在字段{self.search_key_alias}')
        
        if not hasattr(model_class, self.created_by_alias):
            raise PermissionException(data='', message=f'模型{self.query_alias}不存在字段{self.created_by_alias}')
        
        # 构建查询
        search_field = getattr(model_class, self.search_key_alias)
        created_by_field = getattr(model_class, self.created_by_alias)
        
        # 执行查询
        query = select(created_by_field).where(search_field == search_value)
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        
        if record is None:
            raise PermissionException(data='', message='记录不存在')
        
        # 检查当前用户是否是创建者
        current_user_name = current_user.user.user_name
        if record != current_user_name:
            raise PermissionException(data='', message='用户只能访问自己的数据')
        
        return True