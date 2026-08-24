"""Tutorial 2: Reading the Feed and Posts.

This tutorial demonstrates how to fetch the feed for a specific class,
filter posts, and retrieve full post details.

Run this script:
    python 02_reading_the_feed.py
"""

import asyncio
import os

from piazza_sdk import FolderFilter, Piazza, SessionConfig, SessionStateManager, UnreadFilter


async def main() -> None:
    config = SessionConfig(user_agent="piazza-sdk-tutorial/1.0")

    async with SessionStateManager(config) as session:
        # Use credentials from environment variables for safety
        email = os.environ.get("PIAZZA_EMAIL", "your_email@example.com")
        password = os.environ.get("PIAZZA_PASSWORD", "your_password")
        await session.login(email=email, password=password)

        piazza = Piazza(session)
        classes = await piazza.get_user_classes()
        if not classes:
            print("No classes found. Cannot continue.")  # noqa: T201
            return

        # 1. Connect to the first class
        first_class_nid = classes[0]["nid"]
        network = piazza.network(first_class_nid)
        print(f"Connected to Network ID: {first_class_nid}\n")  # noqa: T201

        # 2. Fetch the standard feed (most recent 10 posts)
        print("--- Standard Feed ---")  # noqa: T201
        feed = await network.get_feed(limit=10)
        for item in feed.feed:
            # We use normalized subject to clean any HTML tags
            print(f"[{item.type}] ID: {item.id} - {item.normalized().subject}")  # noqa: T201

        # 3. Filter feed for unread posts only
        print("\n--- Unread Posts ---")  # noqa: T201
        unread_feed = await network.get_filtered_feed(UnreadFilter())
        print(f"Found {len(unread_feed.feed)} unread posts.")  # noqa: T201

        # 4. Filter by folder (e.g., 'logistics' or 'hw1')
        print("\n--- Folder Search ('hw1') ---")  # noqa: T201
        folder_feed = await network.get_filtered_feed(FolderFilter("hw1"))
        print(f"Found {len(folder_feed.feed)} posts in folder 'hw1'.")  # noqa: T201

        # 5. Fetch a full post by ID (let's just fetch the first one from our standard feed)
        if feed.feed:
            post_id = feed.feed[0].id
            print(f"\n--- Full Post Details for {post_id} ---")  # noqa: T201
            post = await network.get_post(post_id)
            print(f"Title: {post.subject}")  # noqa: T201
            print(f"Author: {post.user_name}")  # noqa: T201
            print(f"Tags: {', '.join(post.tags)}")  # noqa: T201

            # Print followups (nested comments)
            if post.children:
                print(f"Followups: {len(post.children)}")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
