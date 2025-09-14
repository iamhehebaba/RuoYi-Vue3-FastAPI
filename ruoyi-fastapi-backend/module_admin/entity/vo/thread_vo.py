from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, Dict, Any
from datetime import datetime


class ThreadCreateModel(BaseModel):
    """创建thread请求模型"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)
    
    graph_id: str = Field(..., description="智能体图ID")



class ThreadCreateResponseModel(BaseModel):
    """thread创建响应模型"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)
    
    thread_id: str = Field(..., description="thread ID")
    graph_id: str = Field(..., description="智能体图ID")
    assistant_id: Optional[str] = Field(None, description="assistant ID")
    created_at: Optional[str] = Field(None, description="创建时间")
    metadata: Optional[dict] = Field(None, description="元数据")
    status: Optional[str] = Field(None, description="状态")


class RunCreateModel(BaseModel):
    """thread运行请求模型"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)
    
    assistant_id: str = Field(..., description="assistant ID")
    input: Dict[str, Any] = Field(..., description="输入数据")


class ThreadHistoryModel(BaseModel):
    """获取thread历史记录请求模型"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)
    
    limit: int = Field(..., description="限制返回的历史记录数量")


class ThreadSearchModel(BaseModel):
    """搜索thread列表请求模型"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)
    
    limit: int = Field(..., description="限制返回的记录数量")
    offset: int = Field(..., description="偏移量")