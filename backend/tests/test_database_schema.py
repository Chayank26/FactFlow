from app import main


def test_database_schema_is_versioned_and_indexed():
    with main.get_connection() as connection:
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        indexes = {
            row["name"]
            for row in connection.execute("PRAGMA index_list('facts')").fetchall()
        }

    assert schema_version == 1
    assert "idx_facts_document_id" in indexes
    assert main.DB_PATH.exists()
