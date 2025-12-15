from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import and_, select, or_, update

from src.core.enums import ConnectionStatus
from src.core.exceptions import (
    AlreadyConnectedError,
    CannotJoinOwnCodeError,
    ConnectionNotFoundError,
    InvalidPairCodeError,
)
from src.core.utils.connections import generate_pair_code
from src.database.entities.connection import Connection


class ConnectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_pair_code(self, user_id: int) -> Connection:
        stmt = select(Connection).where(
            and_(
                or_(Connection.user1_id == user_id, Connection.user2_id == user_id),
                Connection.status.in_(
                    [ConnectionStatus.PENDING, ConnectionStatus.CONNECTED]
                ),
            )
        )

        result = await self.db.execute(stmt)
        connection = result.scalar_one_or_none()

        if connection:
            if connection.status == ConnectionStatus.CONNECTED:
                raise AlreadyConnectedError()
            return connection

        pair_code = generate_pair_code()

        # TODO: ADD INTEGRYERROR OR HANDLE PAIR CODE COLLISIONS
        new_connection = Connection(user1_id=user_id, pair_code=pair_code)
        self.db.add(new_connection)
        await self.db.commit()
        return new_connection

    async def join_connection(self, user_id: int, pair_code: str) -> Connection:

        get_connection_stmt = select(Connection).where(
            Connection.pair_code.ilike(pair_code)
        )

        result = await self.db.execute(get_connection_stmt)
        connection = result.scalar_one_or_none()

        if not connection or connection.status != ConnectionStatus.PENDING:
            raise InvalidPairCodeError()

        if connection.user1_id == user_id:
            raise CannotJoinOwnCodeError()

        disconnect_pending_stmt = (
            update(Connection)
            .where(
                Connection.user1_id == user_id,
                Connection.status == ConnectionStatus.PENDING,
            )
            .values(status=ConnectionStatus.DISCONNECTED)
        )

        await self.db.execute(disconnect_pending_stmt)

        connection.user2_id = user_id
        connection.status = ConnectionStatus.CONNECTED
        connection.connected_at = datetime.now(timezone.utc)

        await self.db.commit()
        return connection

    async def leave_connection(self, user_id: int):

        stmt = select(Connection).where(
            and_(
                or_(Connection.user1_id == user_id, Connection.user2_id == user_id),
                Connection.status == ConnectionStatus.CONNECTED,
            )
        )

        result = await self.db.execute(stmt)
        connection = result.scalar_one_or_none()

        if not connection:
            raise ConnectionNotFoundError()

        connection.status = ConnectionStatus.DISCONNECTED
        connection.disconnected_at = datetime.now(timezone.utc)

        await self.db.commit()
        return connection

    # async def get_active_connection(self, user_id: int) -> Optional[Connection]:
    #     stmt = select(Connection).where(
    #         or_(Connection.user1_id == user_id, Connection.user2_id == user_id),
    #         Connection.status == ConnectionStatus.CONNECTED,
    #     )

    #     result = await self.db.execute(stmt)
    #     return result.scalar_one_or_none()

    async def get_connection(
        self, user_id: int, status: Optional[ConnectionStatus] = None
    ) -> Optional[Connection]:
        stmt = select(Connection).where(
            or_(
                Connection.user1_id == user_id,
                Connection.user2_id == user_id,
            )
        )

        if status:
            stmt = stmt.where(Connection.status == status)

        stmt = stmt.order_by(Connection.created_at.desc()).limit(1)

        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()
