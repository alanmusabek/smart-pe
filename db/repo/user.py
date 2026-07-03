from db.models.user import User
from db.repo.base import BaseDAO
from db.db_config import async_session_maker
from sqlalchemy import select, update

class UserDAO(BaseDAO):
    model = User

    # @classmethod
    # async def update_user(cls, id: int, data: SUserUpdate):
    #     async with async_session_maker() as session:
    #         final_data = data.dict(exclude_unset=True)

    #         query = update(cls.model).where(cls.model.id == id).values(**final_data)
    #         await session.execute(query)
    #         await session.commit()

    @classmethod
    async def get_user_profile(cls, user_id: int) -> SUserResponse:
        async with async_session_maker() as session:
            query = select(cls.model).where(cls.model.id == user_id)
            result = await session.execute(query)
            return result.scalars().one()