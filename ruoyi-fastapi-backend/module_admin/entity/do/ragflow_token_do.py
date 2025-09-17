from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text
from config.database import Base


class RagflowToken(Base):
    """
    Ragflow认证token表
    """

    __tablename__ = 'ragflow_token'

    email = Column(String(100), primary_key=True, comment='注册邮箱')
    nickname = Column(String(100), nullable=True, comment='昵称')
    encoded_password = Column(String(100), nullable=False, comment='密码')
    token = Column(Text, comment='认证token')
    token_refresh_time = Column(DateTime, nullable=False, comment='token刷新时间')
    create_time = Column(DateTime, comment='创建时间', default=datetime.now())
