"""Tutorial 1: Getting Started with Piazza SDK.

This tutorial demonstrates how to authenticate, list your enrolled courses,
and fetch basic profile information using the Piazza SDK.

Run this script:
    python 01_getting_started.py
"""

import asyncio

from piazza_sdk import Piazza, SessionConfig, SessionStateManager
from piazza_sdk.exceptions import AuthenticationError


async def main() -> None:
    # 1. Configure the session
    # We do not need a specific course ID yet just to log in.
    config = SessionConfig(user_agent="piazza-sdk-tutorial/1.0", retries=3, retry_delay=1.0)

    # 2. Use the SessionStateManager to manage the connection pool and auth cookies
    async with SessionStateManager(config) as session:
        try:
            # IMPORTANT: Replace with your actual Piazza credentials or use .env
            print("Logging in...")  # noqa: T201
            await session.login(email="your_email@example.com", password="your_password")
            print("Login successful!\n")  # noqa: T201
        except AuthenticationError:
            print("Failed to authenticate. Please check your credentials.")  # noqa: T201
            return

        # 3. Create the top-level Piazza client
        piazza = Piazza(session)

        # 4. Fetch the user's profile
        profile = await piazza.get_user_profile()
        print(f"Welcome, {profile.get('name', 'User')}!")  # noqa: T201

        # 5. Fetch all enrolled classes
        print("\nYour Enrolled Classes:")  # noqa: T201
        classes = await piazza.get_user_classes()
        if not classes:
            print("  You are not enrolled in any classes.")  # noqa: T201
        for cls in classes:
            nid = cls.get("nid", "unknown")
            name = cls.get("course_name", cls.get("course_number", "Unnamed Class"))
            term = cls.get("term", "")
            print(f"  - {name} ({term}) [ID: {nid}]")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
