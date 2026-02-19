from rag.settings import Settings


def test_primary_provider_is_llama():
    settings = Settings()
    assert settings.primary_provider() == "llama_cpp"


def test_model_copy_can_override_requested_model():
    settings = Settings(llama_cpp={"llm_model": "qwen2.5:1.5b"})
    copied = settings.model_copy(deep=True)
    copied.llama_cpp.llm_model = "qwen3:4b"
    assert settings.llama_cpp.llm_model == "qwen2.5:1.5b"
    assert copied.llama_cpp.llm_model == "qwen3:4b"
