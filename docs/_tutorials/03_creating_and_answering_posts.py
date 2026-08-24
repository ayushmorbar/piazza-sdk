"""Tutorial 3: Creating and Answering Posts.

This tutorial demonstrates how to create a new post, answer it as an instructor
(or student), and endorse it.

Run this script:
    python 03_creating_and_answering_posts.py
"""

import asyncio
import os

from piazza_sdk import Piazza, SessionConfig, SessionStateManager


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

        # 1. Create a Post
        print("Creating a new post...")  # noqa: T201
        created = await network.create_post(
            title="When is the SDK tutorial due?",
            content="I am having trouble finding the deadline for the SDK assignment.",
            post_type="question",
            folders=["logistics"],
            anonymous=True,
        )
        post_id = created.id
        print(f"Created post with ID: {post_id}")  # noqa: T201

        # 2. Get the newly created post
        post = await network.get_post(post_id)

        # 3. Answer the post
        # The 'revision' argument tracks edits. For a new answer, we typically use revision=0 or 1.
        print("\nAnswering the post...")  # noqa: T201
        await network.answer_post(
            post=post,
            content="The tutorial is not an assignment, it is just for fun!",
            is_instructor_answer=True,
            revision=1,
        )
        print("Answer submitted successfully.")  # noqa: T201

        # 4. Add a followup comment
        print("\nAdding a followup comment...")  # noqa: T201
        await network.create_followup(post=post, content="Oh, I see. Thank you!", anonymous=False)
        print("Followup added.")  # noqa: T201

        # 5. Resolve the post (mark as answered/resolved)
        print("\nResolving the post...")  # noqa: T201
        await network.resolve_post(post=post)
        print("Post resolved.")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
