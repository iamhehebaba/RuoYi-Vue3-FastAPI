from sqlalchemy import Column, String, DateTime
from datetime import datetime
from config.database import Base


class LanggraphThread(Base):
    """langgraph thread表"""
    __tablename__ = 'langgraph_thread'
    
    thread_id = Column(String(100), primary_key=True, nullable=False, comment='langgraph的thread_id，UUID字符串')
    graph_id = Column(String(100), nullable=False, comment='langgraph的graph_id，UUID字符串')
    assistant_id = Column(String(100), comment='langgraph的assistant_id，UUID字符串')
    created_by = Column(String(64), default='admin', comment='创建者')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')