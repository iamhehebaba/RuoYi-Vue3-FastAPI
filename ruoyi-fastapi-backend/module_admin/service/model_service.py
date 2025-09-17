from utils.ragflow_util import RagflowClient
from utils.log_util import logger
from fastapi import HTTPException
from typing import Dict, Any


class ModelService:
    """
    模型服务类，处理与模型相关的业务逻辑
    """

    @classmethod
    async def get_llm_factories_service(cls) -> Dict[str, Any]:
        """
        获取LLM factories列表服务
        
        Returns:
            Dict[str, Any]: LLM factories数据
            
        Raises:
            HTTPException: 当请求失败时抛出异常
        """
        try:
            logger.info("开始获取LLM factories列表")
            
            # 创建RagflowClient实例
            ragflow_client = RagflowClient()
            
            # 发送GET请求到ragflow的/v1/llm/factories接口
            response = await ragflow_client.get('/v1/llm/factories')
            
            logger.info(f"成功获取LLM factories列表，返回数据: {response}")
            return response
            
        except Exception as e:
            logger.error(f"获取LLM factories列表失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"获取LLM factories列表失败: {str(e)}"
            )

    @classmethod
    async def get_my_llms_service(cls) -> Dict[str, Any]:
        """
        获取我的LLMs列表服务
        
        Returns:
            Dict[str, Any]: 我的LLMs数据
            
        Raises:
            HTTPException: 当请求失败时抛出异常
        """
        try:
            logger.info("开始获取我的LLMs列表")
            
            # 创建RagflowClient实例
            ragflow_client = RagflowClient()
            
            # 发送GET请求到ragflow的/v1/llm/my_llms接口
            response = await ragflow_client.get('/v1/llm/my_llms')
            
            logger.info(f"成功获取我的LLMs列表，返回数据: {response}")
            return response
            
        except Exception as e:
            logger.error(f"获取我的LLMs列表失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"获取我的LLMs列表失败: {str(e)}"
            )

    @classmethod
    async def delete_llm_service(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        删除LLM服务
        
        Args:
            payload: 删除LLM的请求数据
            
        Returns:
            Dict[str, Any]: 删除结果数据
            
        Raises:
            HTTPException: 当请求失败时抛出异常
        """
        try:
            logger.info(f"开始删除LLM，请求数据: {payload}")
            
            # 创建RagflowClient实例
            ragflow_client = RagflowClient()
            
            # 发送POST请求到ragflow的/v1/llm/delete_llm接口
            response = await ragflow_client.post('/v1/llm/delete_llm', json=payload)
            
            logger.info(f"成功删除LLM，返回数据: {response}")
            return response
            
        except Exception as e:
            logger.error(f"删除LLM失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"删除LLM失败: {str(e)}"
            )

    @classmethod
    async def set_api_key_service(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置API Key服务
        
        Args:
            payload: 设置API Key的请求数据
            
        Returns:
            Dict[str, Any]: 设置结果数据
            
        Raises:
            HTTPException: 当请求失败时抛出异常
        """
        try:
            logger.info(f"开始设置API Key，请求数据: {payload}")
            
            # 创建RagflowClient实例
            ragflow_client = RagflowClient()
            
            # 发送POST请求到ragflow的/v1/llm/set_api_key接口
            response = await ragflow_client.post('/v1/llm/set_api_key', json=payload)
            
            logger.info(f"成功设置API Key，返回数据: {response}")
            return response
            
        except Exception as e:
            logger.error(f"设置API Key失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"设置API Key失败: {str(e)}"
            )

    @classmethod
    async def set_default_model_service(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置默认模型服务
        
        Args:
            payload: 设置默认模型的请求数据
            
        Returns:
            Dict[str, Any]: 设置结果数据
            
        Raises:
            HTTPException: 当请求失败时抛出异常
        """
        try:
            logger.info(f"开始设置默认模型，请求数据: {payload}")
            
            # 创建RagflowClient实例
            ragflow_client = RagflowClient()
            
            # 发送POST请求到ragflow的/v1/user/set_tenant_info接口
            response = await ragflow_client.post('/v1/user/set_tenant_info', json=payload)
            
            logger.info(f"成功设置默认模型，返回数据: {response}")
            return response
            
        except Exception as e:
            logger.error(f"设置默认模型失败: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"设置默认模型失败: {str(e)}"
            )