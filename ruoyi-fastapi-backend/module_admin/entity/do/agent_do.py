from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from config.database import Base


class SysAgent(Base):
    """智能体信息表"""
    __tablename__ = 'sys_agent'
    
    # id = Column(Integer, primary_key=True, autoincrement=True, comment='智能体ID')
    graph_id = Column(String(100), primary_key=True, nullable=False, unique=True, comment='智能体图ID')
    assistant_id = Column(String(100), comment='助手ID')
    name = Column(String(100), nullable=False, comment='智能体名称')
    description = Column(Text, comment='智能体描述')
    status = Column(String(1), default='0', comment='状态（0正常 1停用）')
    remark = Column(String(500), comment='备注')
    order_num = Column(Integer, default=0, comment='排序')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    created_by = Column(String(64), comment='创建者')