from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional
from datetime import datetime


class ThreadCreateModel(BaseModel):
    """创建thread请求模型"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)
    
    graph_id: str = Field(..., description="智能体图ID")


class ThreadModel(BaseModel):
    """thread对应的pydantic模型"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)
    
    thread_id: Optional[str] = Field(None, description="thread ID")
    graph_id: Optional[str] = Field(None, description="智能体图ID")
    assistant_id: Optional[str] = Field(None, description="assistant ID")
    created_by: Optional[str] = Field(None, description="创建者")
    created_at: Optional[datetime] = Field(None, description="创建时间")


class ThreadResponseModel(BaseModel):
    """thread创建响应模型"""
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)
    
    thread_id: str = Field(..., description="thread ID")
    graph_id: str = Field(..., description="智能体图ID")
    assistant_id: Optional[str] = Field(None, description="assistant ID")
    created_at: Optional[str] = Field(None, description="创建时间")
    metadata: Optional[dict] = Field(None, description="元数据")
    status: Optional[str] = Field(None, description="状态")