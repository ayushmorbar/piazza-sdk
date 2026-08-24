"""Example usage of the Piazza SDK.

Demonstrates the modern async API with Pydantic dot-notation access.
"""

import asyncio

from piazza_sdk import Piazza, SessionConfig, SessionStateManager


async def main():
    """Example demonstrating basic Piazza SDK usage."""

    # Configure session
    config = SessionConfig(
        course_id="your_course_id",
        user_agent="example-app/1.0",
        timeout=30.0,
        retries=3,
        retry_delay=1.0,
    )

    try:
        # Create session
        async with SessionStateManager(config) as session:
            # Login
            print("Logging in...")
            await session.login(email="your_email@example.com", password="your_password")

            # Create Piazza client
            piazza = Piazza(session)

            # Get networks (classes) — returned as dicts from user_profile
            print("Getting classes...")
            classes = await piazza.get_user_classes()
            print(f"Found {len(classes)} classes:")
            for cls in classes:
                print(f"  - {cls.get('name', 'N/A')} (ID: {cls.get('nid', cls.get('id', 'N/A'))})")

            if not classes:
                print("No classes found. Exiting.")
                return

            # Get feed from first class
            print("Getting feed...")
            nid = classes[0].get("nid") or classes[0].get("id")
            network = piazza.network(nid)
            feed = await network.get_feed(limit=5)
            print(f"Feed contains {len(feed.feed)} posts")

            # Display posts using dot-notation (FeedItem fields: id, subject, created, type)
            for item in feed.feed:
                print(f"\nPost ID: {item.id}")
                print(f"Subject: {item.subject}")
                print(f"Created: {item.created}")
                print(f"Type: {item.type}")

                # Get full post details (Post fields: author, tags, children, etc.)
                full_post = await network.get_post(item.id)
                print(f"  - Author: {full_post.author}")
                print(f"  - Tags: {', '.join(full_post.tags)}")

            # Create a follow-up on the first post
            if feed.feed:
                print("\nCreating a follow-up...")
                await network.create_followup(
                    post=feed.feed[0].id,
                    content="This is an automated follow-up created by the Piazza SDK example.",
                    anonymous=False,
                )
                print("Follow-up created successfully!")

            # Mark a post as resolved (using the first post)
            print("\nMarking post as resolved...")
            await network.resolve_post(feed.feed[0].id)
            print("Post marked as resolved!")

            # Search for posts — returns Feed with .feed list of FeedItem
            print("\nSearching for posts...")
            search_results = await network.search("assignment")
            print(f"Found {len(search_results.feed)} posts matching 'assignment'")

            # Get statistics
            print("\nGetting class statistics...")
            stats = await network.get_statistics()
            print(f"  Posts: {stats.posts}, Resolved: {stats.resolved}, Users: {stats.users}")

            print("\n✅ All operations completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
