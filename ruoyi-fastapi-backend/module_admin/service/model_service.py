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