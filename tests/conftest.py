import pytest
from django.test import RequestFactory


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture(scope="session", autouse=True)
def _force_cascade_test_flush():
    """Force ``TRUNCATE ... CASCADE`` in the test-DB flush teardown.

    ``transaction=True`` tests tear down by flushing the DB (TRUNCATE). The
    shared ``django_tenancy`` table ``tenancy_module_membership`` (ADR-130
    multi-DB setup) FK-references ``auth_user`` but is excluded from Django's
    flush table list, so a non-CASCADE ``TRUNCATE`` aborts with
    "cannot truncate a table referenced in a foreign key constraint".
    ``CASCADE`` is safe here because the test DB is reset between runs anyway.
    """
    from django.db.backends.postgresql.operations import DatabaseOperations

    original_sql_flush = DatabaseOperations.sql_flush

    def _cascade_sql_flush(
        self, style, tables, *, reset_sequences=False, allow_cascade=False
    ):
        return original_sql_flush(
            self, style, tables, reset_sequences=reset_sequences, allow_cascade=True
        )

    DatabaseOperations.sql_flush = _cascade_sql_flush
    try:
        yield
    finally:
        DatabaseOperations.sql_flush = original_sql_flush
