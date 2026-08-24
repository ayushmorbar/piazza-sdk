"""Tutorial 4: Advanced User Statistics.

This tutorial demonstrates how to retrieve and filter user data and statistics
for a class (useful for instructors or TAs).

Run this script:
    python 04_advanced_user_stats.py
"""

import asyncio
import os

from piazza_sdk import Piazza, SessionConfig, SessionStateManager
from piazza_sdk.models.enums import UserRole


async def main() -> None:
    config = SessionConfig(user_agent="piazza-sdk-tutorial/1.0")

    async with SessionStateManager(config) as session:
        email = os.environ.get("PIAZZA_EMAIL", "your_email@example.com")
        password = os.environ.get("PIAZZA_PASSWORD", "your_password")
        await session.login(email=email, password=password)

        piazza = Piazza(session)
        classes = await piazza.get_user_classes()
        if not classes:
            return

        network = piazza.network(classes[0]["nid"])
        print(f"Connected to Network ID: {classes[0]['nid']}\n")  # noqa: T201

        # 1. Fetch Class Statistics
        # Note: Depending on your role, some statistics might be hidden.
        print("Fetching course statistics...")  # noqa: T201
        stats = await network.get_statistics()
        if hasattr(stats, "students") and getattr(stats, "students"):
            print(f"Total Enrolled Students: {len(stats.students)}")  # noqa: T201

        # 2. Fetch Instructor/Staff Stats
        print("\nFetching Instructor Stats...")  # noqa: T201
        try:
            instructor_stats = await network.get_instructor_stats()
            print("Instructors retrieved successfully.")  # noqa: T201
            for uid, info in instructor_stats.items():
                print(f"  - UID: {uid} | Posts: {info.get('posts', 0)}")  # noqa: T201
        except Exception:  # noqa: BLE001
            print(  # noqa: T201
                "Could not retrieve instructor stats (you may need TA/Instructor privileges)."
            )

        # 3. Fetch All Users in the course
        print("\nFetching user list...")  # noqa: T201
        users = await network.get_users()

        # Filter for instructors only
        instructors = [u for u in users if u.role in {UserRole.PROFESSOR, UserRole.TA}]
        print(f"Found {len(instructors)} instructors/TAs.")  # noqa: T201
        for instr in instructors:
            print(f"  - {instr.name} ({instr.role})")  # noqa: T201

        # 4. Fetch Online Users
        print("\nChecking who is online...")  # noqa: T201
        online_users = await network.get_online_users()
        print(f"Currently online users: {len(online_users)}")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
