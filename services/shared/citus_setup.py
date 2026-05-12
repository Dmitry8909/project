from sqlalchemy import text


async def add_citus_workers(conn, workers: list[str] | None = None):
    if not workers:
        workers = ["citus-worker-1", "citus-worker-2"]
    for worker in workers:
        try:
            await conn.execute(
                text(f"SELECT * from citus_add_node('{worker}', 5432)")
            )
        except Exception:
            pass


async def setup_citus_distribution(conn, workers: list[str] | None = None):
    try:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS citus"))
    except Exception:
        return

    if workers is not None:
        try:
            await add_citus_workers(conn, workers)
        except Exception:
            pass

    reference_tables = ["users", "subscriptions"]
    distributed_tables = {
        "posts": "author_id",
        "post_media": "post_id",
        "comments": "post_id",
        "likes": "post_id",
        "bookmarks": "user_id",
        "messages": "sender_id",
        "message_media": "message_id",
        "notifications": "user_id",
    }

    for table in reference_tables:
        try:
            await conn.execute(text(f"SELECT create_reference_table('{table}')"))
        except Exception:
            pass

    for table, col in distributed_tables.items():
        try:
            await conn.execute(
                text(f"SELECT create_distributed_table('{table}', '{col}')")
            )
        except Exception:
            pass
