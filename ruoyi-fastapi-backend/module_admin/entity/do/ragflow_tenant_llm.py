from sqlalchemy import Column, String, DateTime, BigInteger
from datetime import datetime
from config.database import Base


class RagflowTenantLLM(Base):
    """ragflow租户LLM表"""
    __tablename__ = 'tenant_llm'
    
    tenant_id = Column(String(100), primary_key=True, comment='租户ID')
    llm_factory = Column(String(100), primary_key=True, comment='LLM工厂')
    llm_name = Column(String(100), primary_key=True, comment='LLM名称')
    model_type = Column(String(100), comment='模型类型')
    api_base = Column(String(255), comment='LLM API基础URL')
    api_key = Column(String(255), comment='LLM API密钥')
