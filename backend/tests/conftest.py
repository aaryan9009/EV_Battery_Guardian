"""API tests run against a real, freshly-migrated PostgreSQL database (TEST_DATABASE_URL). Nothing is mocked."""
import os, pathlib, tempfile, pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
TEST_URL = os.environ.get("TEST_DATABASE_URL")
if TEST_URL:
    os.environ.update(DATABASE_URL=TEST_URL, JWT_SECRET="test-secret-not-for-production", ADMIN_EMAILS="admin@test.io",
                      MAX_UPLOAD_MB="1", MODEL_DIR=tempfile.mkdtemp(prefix="ev_models_"))

@pytest.fixture(scope="session", autouse=True)
def _migrated_db():
    if not TEST_URL: return
    from alembic import command
    from alembic.config import Config
    cfg = Config(str(ROOT / "alembic.ini")); cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.downgrade(cfg, "base"); command.upgrade(cfg, "head")      # clean schema via the real migration
