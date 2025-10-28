from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String
from config.database import Base


class LlmConfig(Base):
    """
    LLM配置表
    """

    __tablename__ = 'llm_config'

    config_id = Column(Integer, primary_key=True, autoincrement=True, comment='config主键')
    llm_factory = Column(String(100), nullable=False, comment='llm_factory')
    llm_name = Column(String(100), nullable=False, comment='llm_name')
    model_type = Column(String(50), nullable=False, comment='model_type')
    api_base = Column(String(500), nullable=True, default=None, comment='api_base')
    api_key = Column(String(500), nullable=True, default=None, comment='api_key')
    created_by = Column(String(64), nullable=True, default='', comment='创建者')
    created_at = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')