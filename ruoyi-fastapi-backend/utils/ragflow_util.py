import requests
import base64
import json
import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from config.env import RagflowConfig
from module_admin.dao.ragflow_dao import RagflowDao
from config.get_db import get_db

# 配置日志
logger = logging.getLogger(__name__)

# RSA公钥
RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp2Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOOUEfaS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVKRNLJpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK6olN4RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs2wIDAQAB
-----END PUBLIC KEY-----"""


class RagflowClient:
    """
    Ragflow客户端，用于与Ragflow服务器进行交互
    支持自动注册、登录、token管理和请求转发
    """

    def __init__(self):
        self.base_url = RagflowConfig.ragflow_api_url
        self.email = RagflowConfig.ragflow_email
        self.password = RagflowConfig.ragflow_password
        self.session = requests.Session()
        self.session.timeout = 30
        
    def _encrypt_password(self, password: str) -> str:
        """
        使用RSA公钥加密密码
        
        :param password: 明文密码
        :return: 加密后的密码（Base64编码）
        """
        try:
            # 加载RSA公钥
            public_key = serialization.load_pem_public_key(
                RSA_PUBLIC_KEY.encode('utf-8'),
                backend=default_backend()
            )
            
            # 第一步：对明文密码进行Base64编码（与JavaScript版本保持一致）
            password_base64 = base64.b64encode(password.encode('utf-8')).decode('utf-8')
            
            # 第二步：对Base64编码后的密码进行RSA加密
            encrypted = public_key.encrypt(
                password_base64.encode('utf-8'),
                padding.PKCS1v15()
            )
            
            # 第三步：对加密结果进行Base64编码
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"密码加密失败: {e}")
            raise

    async def _get_valid_token(self) -> Optional[str]:
        """获取有效的token，如果不存在或过期则重新登录"""
        try:
            async for db in get_db():
                dao = RagflowDao(db)
                
                # 检查是否存在有效token
                token_info = await dao.get_token_by_email(self.email)
                if token_info and not dao.is_token_expired(token_info.token_refresh_time):
                    return token_info.token
                
                # token不存在或已过期，重新登录
                return await self._login_and_save_token(db, dao)
            
        except Exception as e:
            logger.error(f"获取token失败: {e}")
            return None

    async def _register(self) -> bool:
        """
        注册用户
        
        :return: 注册是否成功
        """
        try:
            url = f"{self.base_url}/v1/user/register"
            encrypted_password = self._encrypt_password(self.password)
            
            payload = {
                "nickname": "service",
                "email": self.email,
                "password": encrypted_password
            }
            
            response = self.session.post(url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"用户 {self.email} 注册成功")
                return True
            else:
                logger.error(f"用户注册失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"注册过程中发生错误: {e}")
            return False

    async def refresh_token(self, db: AsyncSession) -> Optional[str]:
        """
        刷新token：删除过期token并重新认证
        
        :param db: 数据库会话
        :return: 新的token，如果刷新失败则返回None
        """
        try:
            # 删除过期的token
            dao = RagflowDao(db)
            await dao.delete_token_by_email(self.email)
            
            # 重新认证
            return await self._login_and_save_token(db, dao)
        except Exception as e:
            logger.error(f"刷新token失败: {e}")
            return None

    async def _login_and_save_token(self, db: AsyncSession, dao: RagflowDao) -> Optional[str]:
        """登录并保存token"""
        try:
            # 加密密码
            encrypted_password = self._encrypt_password(self.password)
            
            payload = {
                "email": self.email,
                "password": encrypted_password
            }
            
            response = requests.post(
                f"{self.base_url}/v1/user/login",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                # 从响应头获取token
                token = response.headers.get('authorization')
                if token:
                    # 保存token到数据库
                    await dao.save_token(self.email, token)
                    logger.info(f"用户 {self.email} 登录成功，token已保存")
                    return token
                else:
                    logger.error("登录成功但未获取到token")
                    return None
            else:
                logger.error(f"登录失败: {response.status_code} - {response.text}")
                # 如果是401错误，可能需要先注册
                if response.status_code == 401:
                    logger.info("尝试注册用户...")
                    if await self._register():
                        # 注册成功后重新登录
                        return await self._login_and_save_token(db, dao)
                return None
                
        except Exception as e:
            logger.error(f"登录过程中发生错误: {e}")
            return None

    async def _refresh_token_needed(self, response: requests.Response) -> bool:
        """
        判断是否需要刷新token
        
        :param response: 响应对象
        :return: 是否需要刷新token
        """
        need_refresh = (response.status_code == 401)
        if not need_refresh and response.status_code == 200:

            response_json = response.json()
            code = response_json['code']
            if code == 401:
                need_refresh = 'unauthorized' in response_json['message'].lower()
        return need_refresh

    async def _make_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """
        发送请求到Ragflow服务器
        
        :param method: HTTP方法（GET, POST等）
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        async for db in get_db():
            try:
                # 确保已认证
                token = await self._get_valid_token()
                if not token:
                    raise Exception("无法获取有效的认证token")
                
                # 设置认证头
                headers = kwargs.get('headers', {})
                headers['authorization'] = token
                kwargs['headers'] = headers
                
                # 构建完整URL
                url = f"{self.base_url}{path}"
                
                # 发送请求
                response = self.session.request(method, url, **kwargs)
                
                # 如果token过期（401错误），尝试重新认证
                if await self._refresh_token_needed(response):
                    logger.info("Token可能已过期，尝试重新认证")
                    # 刷新token
                    token = await self.refresh_token(db)
                    if token:
                        headers['authorization'] = token
                        kwargs['headers'] = headers
                        response = self.session.request(method, url, **kwargs)
                    else:
                        raise Exception("刷新token失败，无法继续请求")
                
                api_response = response.json()
                logger.info(f"ragflow 响应: {api_response}")
                return api_response                
                
            except Exception as e:
                logger.error(f"请求过程中发生错误: {e}")
                raise e

    async def get(self, path: str, **kwargs) -> requests.Response:
        """
        发送GET请求
        
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        return await self._make_request('GET', path, **kwargs)

    async def post(self, path: str, **kwargs) -> requests.Response:
        """
        发送POST请求
        
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        return await self._make_request('POST', path, **kwargs)

    async def put(self, path: str, **kwargs) -> requests.Response:
        """
        发送PUT请求
        
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        return await self._make_request('PUT', path, **kwargs)

    async def delete(self, path: str, **kwargs) -> requests.Response:
        """
        发送DELETE请求
        
        :param path: API路径
        :param kwargs: 其他请求参数
        :return: 响应对象
        """
        return await self._make_request('DELETE', path, **kwargs)


# 创建全局实例
ragflow_client = RagflowClient()