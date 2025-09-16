from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel
from typing import Optional, List
from datetime import datetime


class AgentModel(BaseModel):
    """
    智能体表对应的pydantic模型
    """
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    graph_id: Optional[str] = Field(None, description="智能体图ID") 
    assistant_id: Optional[str] = Field(None, description="智能体ID")
    name: Optional[str] = Field(None, description="智能体名称")
    status: Optional[str] = Field(None, description="状态")
    description: Optional[str] = Field(None, description="智能体描述")
    remark: Optional[str] = Field(None, description="备注")
    created_by: Optional[str] = Field(None, description="创建者")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    order_num: Optional[int] = Field(None, description="排序")


class AgentQueryModel(AgentModel):
    """智能体搜索请求模型"""

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    limit: Optional[int] = Field(5, description="返回记录数限制", ge=1, le=100)
    offset: Optional[int] = Field(0, description="偏移量", ge=0)



class AgentResponse(BaseModel):
    """智能体查询响应模型"""
    assistants: List[AgentModel] = Field(..., description="智能体列表")
    pagination: dict = Field(..., description="分页信息")