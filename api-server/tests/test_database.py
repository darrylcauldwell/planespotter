"""Tests for the database connection's TLS setting."""
import ssl

import certifi

from app.database import ssl_setting


class TestSslSetting:
    """Tests for ssl_setting."""

    def test_plain_without_a_ca_certificate(self):
        """Test no CA certificate means a plain connection, as docker-compose's Postgres needs."""
        assert ssl_setting(None) is False

    def test_verify_ca_with_a_ca_certificate(self):
        """Test a CA certificate means TLS that checks the server's certificate but not its name."""
        context = ssl_setting(certifi.where())

        assert isinstance(context, ssl.SSLContext)
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is False
