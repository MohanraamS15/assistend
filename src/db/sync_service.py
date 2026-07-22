import time

from sqlalchemy import text

from src.db.database import get_session
from src.logger import logger


def collect_insert_changes(session):
    result = session.exec(
        text("""
            SELECT
                s.sender_id,
                s.sender_entity
            FROM sender_id_mapping_staging s
            LEFT JOIN sender_id_mapping m
                ON s.sender_id = m.sender_id
            WHERE m.sender_id IS NULL;
        """)
    )

    return result.fetchall()


def collect_update_changes(session):
    result = session.exec(
        text("""
            SELECT
                m.sender_id,
                m.sender_entity AS old_entity,
                s.sender_entity AS new_entity
            FROM sender_id_mapping m
            JOIN sender_id_mapping_staging s
                ON m.sender_id = s.sender_id
            WHERE m.sender_entity <> s.sender_entity;
        """)
    )

    return result.fetchall()


def collect_delete_changes(session):
    result = session.exec(
        text("""
            SELECT
                m.sender_id,
                m.sender_entity
            FROM sender_id_mapping m
            WHERE NOT EXISTS (
                SELECT 1
                FROM sender_id_mapping_staging s
                WHERE s.sender_id = m.sender_id
            );
        """)
    )

    return result.fetchall()


def sync_database():

    logger.info("Starting database synchronization...")

    sync_start = time.perf_counter()

    with get_session() as session:

        try:

            # Collect changes before applying them
            insert_rows = collect_insert_changes(session)
            update_rows = collect_update_changes(session)
            delete_rows = collect_delete_changes(session)

            logger.info(f"Insert candidates : {len(insert_rows)}")
            logger.info(f"Update candidates : {len(update_rows)}")
            logger.info(f"Delete candidates : {len(delete_rows)}")

            # INSERT
            session.exec(
                text("""
                    INSERT INTO sender_id_mapping (sender_id, sender_entity)
                    SELECT
                        s.sender_id,
                        s.sender_entity
                    FROM sender_id_mapping_staging s
                    LEFT JOIN sender_id_mapping m
                        ON s.sender_id = m.sender_id
                    WHERE m.sender_id IS NULL;
                """)
            )

            # UPDATE
            session.exec(
                text("""
                    UPDATE sender_id_mapping m
                    SET sender_entity = s.sender_entity
                    FROM sender_id_mapping_staging s
                    WHERE m.sender_id = s.sender_id
                      AND m.sender_entity <> s.sender_entity;
                """)
            )

            # DELETE
            session.exec(
                text("""
                    DELETE FROM sender_id_mapping m
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM sender_id_mapping_staging s
                        WHERE s.sender_id = m.sender_id
                    );
                """)
            )

            session.commit()

            sync_time = time.perf_counter() - sync_start

            logger.info("Database synchronization completed.")
            logger.info(
                f"Synchronization Time : {sync_time:.2f} seconds"
            )

            return {
                "inserted": len(insert_rows),
                "updated": len(update_rows),
                "deleted": len(delete_rows),
                "insert_rows": insert_rows,
                "update_rows": update_rows,
                "delete_rows": delete_rows,
                "sync_time": sync_time,
            }

        except Exception:
            session.rollback()
            logger.exception("Database synchronization failed.")
            raise