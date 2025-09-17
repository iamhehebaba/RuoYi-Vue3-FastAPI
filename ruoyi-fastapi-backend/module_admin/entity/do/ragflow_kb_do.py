from sqlalchemy import Column, String, DateTime, BigInteger
from datetime import datetime
from config.database import Base


class RagflowKb(Base):
    """ragflow知识库表"""
    __tablename__ = 'ragflow_kb'
    
    id = Column(String(100), primary_key=True, comment='知识库ID')
    dept_id = Column(BigInteger, comment='创建该知识库的部门ID')
    created_by = Column(String(64), comment='创建者')
    created_at = Column(DateTime, default=datetime.now(), comment='创建时间')