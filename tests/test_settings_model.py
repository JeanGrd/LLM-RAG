from rag.settings import Settings


def test_primary_provider_is_ollama():
    settings = Settings()
    assert settings.primary_provider() == "ollama"


def test_model_copy_can_override_requested_model():
    settings = Settings(ollama={"llm_model": "qwen2.5:1.5b"})
    copied = settings.model_copy(deep=True)
    copied.ollama.llm_model = "qwen3:4b"
    assert settings.ollama.llm_model == "qwen2.5:1.5b"
    assert copied.ollama.llm_model == "qwen3:4b"
