from rag.settings import Settings


def test_primary_provider_respects_explicit_provider():
    settings = Settings(model={"provider": "ollama"})
    assert settings.primary_provider() == "ollama"


def test_primary_provider_auto_uses_legacy_routing_flag():
    assert Settings(model={"provider": "auto"}, rag={"use_cloud_first": True}).primary_provider() == "cloud"
    assert (
        Settings(model={"provider": "auto"}, rag={"use_cloud_first": False}).primary_provider()
        == "ollama"
    )


def test_model_copy_can_override_requested_model():
    settings = Settings(model={"provider": "ollama", "name": "qwen2.5:1.5b"})
    copied = settings.model_copy(deep=True)
    copied.model.name = "qwen3:4b"
    assert settings.model.name == "qwen2.5:1.5b"
    assert copied.model.name == "qwen3:4b"
