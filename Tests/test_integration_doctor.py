from Diagnostics.integration_doctor import REQUIRED_SPOTIFY_SCOPES, load_env, spotify_redirect_is_compatible
from lastfm_app.spotify import SCOPES


def test_spotify_redirect_accepts_explicit_ipv4_loopback() -> None:
    assert spotify_redirect_is_compatible("http://127.0.0.1:8765/callback")


def test_spotify_redirect_rejects_localhost_and_invalid_ports() -> None:
    assert not spotify_redirect_is_compatible("http://localhost:8765/callback")
    assert not spotify_redirect_is_compatible("http://127.0.0.1:not-a-port/callback")


def test_integration_doctor_scope_contract_matches_spotify_client() -> None:
    assert REQUIRED_SPOTIFY_SCOPES == set(SCOPES.split())


def test_load_env_parses_values_without_shell_evaluation(tmp_path) -> None:
    marker = tmp_path / "should-not-exist"
    env_path = tmp_path / ".env"
    env_path.write_text(
        f"PLAIN=value\nQUOTED='hello world'\nLITERAL=$(touch {marker})\n",
        encoding="utf-8",
    )

    values = load_env(env_path)

    assert values["PLAIN"] == "value"
    assert values["QUOTED"] == "hello world"
    assert values["LITERAL"].startswith("$(touch ")
    assert not marker.exists()
