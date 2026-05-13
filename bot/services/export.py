import csv
from io import StringIO

from sqlalchemy import select

from bot.models.user import User


async def export_users_csv(session) -> str:
    result = await session.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "tg_id", "username", "full_name", "is_active", "joined_at"])
    for user in users:
        writer.writerow([
            user.id,
            user.tg_id,
            user.username or "",
            user.full_name or "",
            user.is_active,
            user.joined_at.isoformat() if user.joined_at else "",
        ])
    return buffer.getvalue()