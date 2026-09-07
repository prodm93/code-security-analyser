"""Build the minimal environment inherited by security scanners."""

import os
from collections.abc import Mapping


_ALLOWED_ENVIRONMENT_VARIABLES = frozenset(
    {
        # Executable lookup and platform runtime directories.
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "HOME",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "TMPDIR",
        "TMP",
        "TEMP",
        # Locale, certificate, and proxy configuration.
        "LANG",
        "LANGUAGE",
        "LC_ALL",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
        # Explicitly non-credential scanner configuration.
        "TRIVY_CACHE_DIR",
        "TRIVY_DB_REPOSITORY",
        "TRIVY_JAVA_DB_REPOSITORY",
        "TRIVY_CHECKS_BUNDLE_REPOSITORY",
        "TRIVY_SKIP_DB_UPDATE",
        "TRIVY_SKIP_CHECK_UPDATE",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
    }
)


def scanner_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return only operational variables that scanner processes require."""
    values = os.environ if source is None else source
    return {
        name: values[name] for name in _ALLOWED_ENVIRONMENT_VARIABLES if name in values
    }
