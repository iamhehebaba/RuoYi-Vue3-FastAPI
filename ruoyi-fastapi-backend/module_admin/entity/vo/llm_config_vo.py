from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_validation_decorator import NotBlank, Size
from typing import Optional
from module_admin.annotation.pydantic_annotation import as_query


class LlmConfigModel(BaseModel):
    """
    LLM配置表对应pydantic模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    config_id: Optional[int] = Field(default=None, description='config主键')
    llm_factory: Optional[str] = Field(default=None, description='llm_factory')
    llm_name: Optional[str] = Field(default=None, description='llm_name')
    model_type: Optional[str] = Field(default=None, description='model_type')
    api_base: Optional[str] = Field(default=None, description='api_base')
    api_key: Optional[str] = Field(default=None, description='api_key')
    created_by: Optional[str] = Field(default=None, description='创建者')
    created_at: Optional[datetime] = Field(default=None, description='创建时间')

    @NotBlank(field_name='llm_factory', message='LLM厂商不能为空')
    @Size(field_name='llm_factory', min_length=0, max_length=100, message='LLM厂商长度不能超过100个字符')
    def get_llm_factory(self):
        return self.llm_factory

    @NotBlank(field_name='llm_name', message='LLM模型名称不能为空')
    @Size(field_name='llm_name', min_length=0, max_length=100, message='LLM模型名称长度不能超过100个字符')
    def get_llm_name(self):
        return self.llm_name

    @NotBlank(field_name='model_type', message='模型类型不能为空')
    @Size(field_name='model_type', min_length=0, max_length=50, message='模型类型长度不能超过50个字符')
    def get_model_type(self):
        return self.model_type

    @Size(field_name='api_base', min_length=0, max_length=500, message='API服务地址长度不能超过500个字符')
    def get_api_base(self):
        return self.api_base

    @Size(field_name='api_key', min_length=0, max_length=500, message='API密钥长度不能超过500个字符')
    def get_api_key(self):
        return self.api_key

    def validate_fields(self):
        self.get_llm_factory()
        self.get_llm_name()
        self.get_model_type()
        self.get_api_base()
        self.get_api_key()


@as_query
class LlmConfigQueryModel(LlmConfigModel):
    """
    LLM配置管理不分页查询模型
    """

    begin_time: Optional[str] = Field(default=None, description='开始时间')
    end_time: Optional[str] = Field(default=None, description='结束时间')


class DeleteLlmConfigModel(BaseModel):
    """
    删除LLM配置模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    config_ids: str = Field(default=None, description='需要删除的配置id')


class LlmConfigPageQueryModel(LlmConfigQueryModel):
    """
    LLM配置管理分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')