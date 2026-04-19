from config.settings.base import build_https_trusted_origins, merge_public_host_contract


def test_build_https_trusted_origins_normalizes_unique_hosts():
    assert build_https_trusted_origins(["app.example.com", "app.example.com", ""]) == [
        "https://app.example.com"
    ]


def test_merge_public_host_contract_appends_render_hostname():
    allowed_hosts, trusted_origins = merge_public_host_contract(
        ["octobox.app"],
        ["https://octobox.app"],
        extra_hosts=["octobox.onrender.com"],
    )

    assert allowed_hosts == ["octobox.app", "octobox.onrender.com"]
    assert trusted_origins == ["https://octobox.app", "https://octobox.onrender.com"]
