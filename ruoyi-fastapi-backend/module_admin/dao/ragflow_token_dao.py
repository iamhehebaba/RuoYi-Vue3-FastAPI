from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timedelta
from typing import Optional
from module_admin.entity.do.ragflow_token_do import RagflowToken


class RagflowTokenDao:
    """Ragflow Token数据访问层"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_token_by_email(self, email: str) -> Optional[RagflowToken]:
        """根据邮箱获取token信息"""
        try:
            stmt = select(RagflowToken).where(RagflowToken.email == email)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            print(f"获取token失败: {e}")
            return None
    
    async def save_token(self, email: str, token: str) -> bool:
        """保存或更新token信息"""
        try:
            # 先查找是否存在
            existing_token = await self.get_token_by_email(email)
            
            if existing_token:
                # 更新现有记录
                existing_token.token = token
                existing_token.token_refresh_time = datetime.now()
            else:
                # 创建新记录
                new_token = RagflowToken(
                    email=email,
                    token=token,
                    token_refresh_time=datetime.now(),
                    create_time=datetime.now()
                )
                self.db.add(new_token)
            
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            print(f"保存token失败: {e}")
            return False
    
    async def delete_token_by_email(self, email: str) -> bool:
        """根据邮箱删除token信息"""
        try:
            stmt = delete(RagflowToken).where(RagflowToken.email == email)
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception as e:
            await self.db.rollback()
            print(f"删除token失败: {e}")
            return False
    
    def is_token_expired(self, token_refresh_time: datetime, expire_hours: int = 24) -> bool:
        """检查token是否过期"""
        if not token_refresh_time:
            return True
        
        expire_time = token_refresh_time + timedelta(hours=expire_hours)
        return datetime.now() > expire_time