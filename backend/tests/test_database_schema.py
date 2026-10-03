from app import main


def test_database_schema_is_versioned_and_indexed():
    with main.get_connection() as connection:
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        indexes = {
            row["name"]
            for row in connection.execute("PRAGMA index_list('facts')").fetchall()
        }

    assert schema_version == 3
    assert "idx_facts_document_id" in indexes
    assert main.DB_PATH.exists()


def test_upgrade_preserves_version_one_documents_and_facts():
    # Recreate the legacy tables inside this test's isolated database.
    with main.get_connection() as connection:
        connection.execute('DROP TABLE facts')
        connection.execute('DROP TABLE documents')
        connection.execute('CREATE TABLE documents (id TEXT PRIMARY KEY, filename TEXT, size_bytes INTEGER, content_type TEXT, stored_path TEXT, created_at TEXT, status TEXT)')
        connection.execute('CREATE TABLE facts (id TEXT PRIMARY KEY, document_id TEXT, claim TEXT, source_page INTEGER, source_text TEXT, created_at TEXT)')
        connection.execute("INSERT INTO documents VALUES ('doc', 'old.pdf', 10, 'application/pdf', ?, 'now', 'processed')", (str(main.UPLOADS_DIR / "old.pdf"),))
        connection.execute("INSERT INTO facts VALUES ('fact', 'doc', 'An existing claim.', 1, 'An existing claim.', 'now')")
        connection.execute('PRAGMA user_version = 1')
    main.init_db()
    main.init_db()
    with main.get_connection() as connection:
        fact = connection.execute("SELECT * FROM facts WHERE id = 'fact'").fetchone()
        assert fact['claim'] == 'An existing claim.'
        assert fact['extraction_method'] == 'native'
        assert connection.execute("SELECT extraction_error FROM documents WHERE id = 'doc'").fetchone()[0] is None
        assert connection.execute('PRAGMA user_version').fetchone()[0] == 3
