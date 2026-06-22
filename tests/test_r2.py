"""Tests for R2 image storage — NO network calls.

TDD: these tests were written before the implementation.

Three groups:
  (a) No R2 config → local-dev fallback (write to instance/uploads/, no boto3 call).
  (b) public_url logic — both branches (local vs R2 domain).
  (c) R2 configured → upload_image calls put_object with bucket + uuid key.
"""

import os
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides):
    """Build a Settings object with test defaults, bypassing .env."""
    envs = {
        "SECRET_KEY": "test-secret",
        "FLASK_ENV": "testing",
        "_DATABASE_URL": "sqlite:///test.sqlite",
    }
    envs.update(overrides)
    # patch os.environ so Settings picks up our values
    with patch.dict(os.environ, envs, clear=False):
        from project.config import Settings

        return Settings(_env_file=None)


# ---------------------------------------------------------------------------
# (a) No R2 config: local-dev fallback
# ---------------------------------------------------------------------------


class TestLocalFallback:
    """When R2 env vars are absent, upload_image must use instance/uploads/."""

    def test_upload_writes_file_to_local_dir(self, tmp_path, monkeypatch):
        """upload_image writes bytes to instance/uploads/<key> when unconfigured."""
        # Ensure R2 env vars are absent
        for var in ("_R2_ACCOUNT_ID", "_R2_ACCESS_KEY_ID", "_R2_SECRET_ACCESS_KEY", "_R2_BUCKET"):
            monkeypatch.delenv(var, raising=False)

        # Reload config + storage with a patched INSTANCE_PATH
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        # Patch the uploads base dir so we write to tmp_path, not real instance/
        from project.utils.r2 import r2_storage

        monkeypatch.setattr(r2_storage, "UPLOADS_DIR", tmp_path / "uploads")

        # Reload settings so it sees fresh env
        from project.config import Settings

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        key = r2_storage.upload_image(b"fake-image-bytes")

        # Key must look like images/<hex>.jpg
        assert key.startswith("images/")
        assert key.endswith(".jpg")

        written_file = tmp_path / "uploads" / key
        assert written_file.exists()
        assert written_file.read_bytes() == b"fake-image-bytes"

    def test_upload_does_not_call_boto3_when_unconfigured(self, tmp_path, monkeypatch):
        """boto3.client must never be called when R2 is not configured."""
        for var in ("_R2_ACCOUNT_ID", "_R2_ACCESS_KEY_ID", "_R2_SECRET_ACCESS_KEY", "_R2_BUCKET"):
            monkeypatch.delenv(var, raising=False)

        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.utils.r2 import r2_storage

        monkeypatch.setattr(r2_storage, "UPLOADS_DIR", tmp_path / "uploads")

        from project.config import Settings

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        # Patch boto3.client to raise if called
        boto3_mock = MagicMock(side_effect=AssertionError("boto3.client must NOT be called when unconfigured"))
        monkeypatch.setattr(r2_storage, "boto3", MagicMock(client=boto3_mock))

        r2_storage.upload_image(b"bytes")

        boto3_mock.assert_not_called()

    def test_delete_removes_local_file_when_unconfigured(self, tmp_path, monkeypatch):
        """delete_object removes the local file when R2 is not configured."""
        for var in ("_R2_ACCOUNT_ID", "_R2_ACCESS_KEY_ID", "_R2_SECRET_ACCESS_KEY", "_R2_BUCKET"):
            monkeypatch.delenv(var, raising=False)

        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.utils.r2 import r2_storage

        uploads_dir = tmp_path / "uploads" / "images"
        uploads_dir.mkdir(parents=True)
        monkeypatch.setattr(r2_storage, "UPLOADS_DIR", tmp_path / "uploads")

        from project.config import Settings

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        # Create a fake uploaded file
        fake_key = "images/abc123.jpg"
        fake_file = tmp_path / "uploads" / fake_key
        fake_file.write_bytes(b"data")
        assert fake_file.exists()

        r2_storage.delete_object(fake_key)

        assert not fake_file.exists()

    def test_delete_ignores_missing_local_file(self, tmp_path, monkeypatch):
        """delete_object silently ignores a key that doesn't exist locally."""
        for var in ("_R2_ACCOUNT_ID", "_R2_ACCESS_KEY_ID", "_R2_SECRET_ACCESS_KEY", "_R2_BUCKET"):
            monkeypatch.delenv(var, raising=False)

        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.utils.r2 import r2_storage

        monkeypatch.setattr(r2_storage, "UPLOADS_DIR", tmp_path / "uploads")

        from project.config import Settings

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        # Should not raise
        r2_storage.delete_object("images/does-not-exist.jpg")


# ---------------------------------------------------------------------------
# (b) public_url logic
# ---------------------------------------------------------------------------


class TestPublicUrl:
    """public_url builds the correct URL in both R2 and local-dev modes."""

    def test_local_url_when_unconfigured(self, monkeypatch):
        """public_url returns a /uploads/<key> path when R2 is not configured."""
        for var in ("_R2_ACCOUNT_ID", "_R2_ACCESS_KEY_ID", "_R2_SECRET_ACCESS_KEY", "_R2_BUCKET"):
            monkeypatch.delenv(var, raising=False)

        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils.r2 import r2_storage

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        url = r2_storage.public_url("images/abc.jpg")
        assert url == "/uploads/images/abc.jpg"

    def test_r2_domain_url_when_configured(self, monkeypatch):
        """public_url returns https://<domain>/<key> when R2 domain is set."""
        monkeypatch.setenv("_R2_ACCOUNT_ID", "acc123")
        monkeypatch.setenv("_R2_ACCESS_KEY_ID", "key123")
        monkeypatch.setenv("_R2_SECRET_ACCESS_KEY", "secret123")
        monkeypatch.setenv("_R2_BUCKET", "globalify-images")
        monkeypatch.setenv("_R2_PUBLIC_DOMAIN", "img.globalify.com")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils.r2 import r2_storage

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        url = r2_storage.public_url("images/abc.jpg")
        assert url == "https://img.globalify.com/images/abc.jpg"

    def test_r2_url_without_public_domain_falls_back_to_local(self, monkeypatch):
        """public_url falls back to local path when domain is absent even if bucket configured."""
        monkeypatch.setenv("_R2_ACCOUNT_ID", "acc123")
        monkeypatch.setenv("_R2_ACCESS_KEY_ID", "key123")
        monkeypatch.setenv("_R2_SECRET_ACCESS_KEY", "secret123")
        monkeypatch.setenv("_R2_BUCKET", "globalify-images")
        monkeypatch.delenv("_R2_PUBLIC_DOMAIN", raising=False)
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils.r2 import r2_storage

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        url = r2_storage.public_url("images/abc.jpg")
        assert url == "/uploads/images/abc.jpg"


# ---------------------------------------------------------------------------
# (c) R2 configured: upload_image calls put_object
# ---------------------------------------------------------------------------


class TestR2Upload:
    """When R2 is fully configured, upload_image calls put_object correctly."""

    def test_upload_calls_put_object_with_correct_args(self, monkeypatch):
        """upload_image calls s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=ct)."""
        monkeypatch.setenv("_R2_ACCOUNT_ID", "acc123")
        monkeypatch.setenv("_R2_ACCESS_KEY_ID", "key123")
        monkeypatch.setenv("_R2_SECRET_ACCESS_KEY", "secret123")
        monkeypatch.setenv("_R2_BUCKET", "globalify-images")
        monkeypatch.setenv("_R2_PUBLIC_DOMAIN", "img.globalify.com")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils.r2 import r2_storage

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        # Mock the boto3 S3 client
        mock_s3 = MagicMock()
        mock_boto3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        monkeypatch.setattr(r2_storage, "boto3", mock_boto3)
        # Reset cached client so it rebuilds with our mock
        monkeypatch.setattr(r2_storage, "_s3_client", None)

        key = r2_storage.upload_image(b"image-data", content_type="image/jpeg")

        # Verify key format
        assert key.startswith("images/")
        assert key.endswith(".jpg")
        hex_part = key.split("/")[1].removesuffix(".jpg")
        assert len(hex_part) == 32  # uuid4().hex is 32 chars

        # Verify boto3 client was constructed with R2 endpoint
        mock_boto3.client.assert_called_once_with(
            "s3",
            endpoint_url="https://acc123.r2.cloudflarestorage.com",
            aws_access_key_id="key123",
            aws_secret_access_key="secret123",
            region_name="auto",
        )

        # Verify put_object called with correct bucket, key, body, content_type
        mock_s3.put_object.assert_called_once_with(
            Bucket="globalify-images",
            Key=key,
            Body=b"image-data",
            ContentType="image/jpeg",
        )

    def test_upload_returns_key_not_url(self, monkeypatch):
        """upload_image returns a storage key (no https:// prefix), not a full URL."""
        monkeypatch.setenv("_R2_ACCOUNT_ID", "acc123")
        monkeypatch.setenv("_R2_ACCESS_KEY_ID", "key123")
        monkeypatch.setenv("_R2_SECRET_ACCESS_KEY", "secret123")
        monkeypatch.setenv("_R2_BUCKET", "globalify-images")
        monkeypatch.setenv("_R2_PUBLIC_DOMAIN", "img.globalify.com")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils.r2 import r2_storage

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        mock_s3 = MagicMock()
        mock_boto3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        monkeypatch.setattr(r2_storage, "boto3", mock_boto3)
        monkeypatch.setattr(r2_storage, "_s3_client", None)

        key = r2_storage.upload_image(b"bytes")

        assert not key.startswith("http")

    def test_delete_calls_r2_delete_object_when_configured(self, monkeypatch):
        """delete_object calls s3.delete_object(Bucket=bucket, Key=key) when R2 configured."""
        monkeypatch.setenv("_R2_ACCOUNT_ID", "acc123")
        monkeypatch.setenv("_R2_ACCESS_KEY_ID", "key123")
        monkeypatch.setenv("_R2_SECRET_ACCESS_KEY", "secret123")
        monkeypatch.setenv("_R2_BUCKET", "globalify-images")
        monkeypatch.setenv("_R2_PUBLIC_DOMAIN", "img.globalify.com")
        monkeypatch.setenv("FLASK_ENV", "testing")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("_DATABASE_URL", "sqlite:///test.sqlite")

        from project.config import Settings
        from project.utils.r2 import r2_storage

        settings = Settings(_env_file=None)
        monkeypatch.setattr(r2_storage, "_settings", settings)

        mock_s3 = MagicMock()
        mock_boto3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        monkeypatch.setattr(r2_storage, "boto3", mock_boto3)
        monkeypatch.setattr(r2_storage, "_s3_client", None)

        r2_storage.delete_object("images/abc.jpg")

        mock_s3.delete_object.assert_called_once_with(
            Bucket="globalify-images",
            Key="images/abc.jpg",
        )


# ---------------------------------------------------------------------------
# (d) Settings: r2_is_configured property
# ---------------------------------------------------------------------------


class TestR2IsConfigured:
    """Settings.r2_is_configured returns True only when all required R2 vars are set."""

    def test_false_when_no_r2_vars(self, monkeypatch):
        for var in ("_R2_ACCOUNT_ID", "_R2_ACCESS_KEY_ID", "_R2_SECRET_ACCESS_KEY", "_R2_BUCKET"):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")

        from project.config import Settings

        settings = Settings(_env_file=None)
        assert settings.r2_is_configured is False

    def test_false_when_partial_r2_vars(self, monkeypatch):
        monkeypatch.setenv("_R2_ACCOUNT_ID", "acc123")
        monkeypatch.delenv("_R2_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("_R2_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("_R2_BUCKET", raising=False)
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")

        from project.config import Settings

        settings = Settings(_env_file=None)
        assert settings.r2_is_configured is False

    def test_true_when_all_r2_vars_present(self, monkeypatch):
        monkeypatch.setenv("_R2_ACCOUNT_ID", "acc123")
        monkeypatch.setenv("_R2_ACCESS_KEY_ID", "key123")
        monkeypatch.setenv("_R2_SECRET_ACCESS_KEY", "secret123")
        monkeypatch.setenv("_R2_BUCKET", "globalify-images")
        monkeypatch.setenv("SECRET_KEY", "test-secret")
        monkeypatch.setenv("FLASK_ENV", "testing")

        from project.config import Settings

        settings = Settings(_env_file=None)
        assert settings.r2_is_configured is True
