import os
from dotenv import load_dotenv
from .base import BaseLLM
from .openai_llm import OpenAILLM
from .groq_llm import GroqLLM
from .ollama_llm import OllamaLLM

# Load environment variables
load_dotenv()

class LLMFactory:
    """Factory to create LLM instances based on available API keys."""
    _llm_instance = None
    _initialized = False

    @classmethod
    def get_llm(cls) -> BaseLLM:
        """Returns an LLM instance, preferring OpenAI if available, followed by Groq, then Ollama.
        Uses a singleton pattern to ensure only one LLM instance is created."""
        if cls._llm_instance is not None:
            return cls._llm_instance
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        use_ollama = os.getenv("USE_OLLAMA", "").lower() in ("true", "1", "yes", "y")
        ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")

        # Try Ollama first if explicitly set to be used
        if use_ollama and not cls._initialized:
            print("✓ Attempting to use Ollama LLM")
            try:
                cls._llm_instance = OllamaLLM(base_url=ollama_url)
                cls._initialized = True
                return cls._llm_instance
            except Exception as e:
                print(f"⚠️ Ollama initialization failed: {e}, falling back to cloud LLMs")

        # Try OpenAI
        if openai_api_key and not cls._initialized:
            cls._llm_instance = OpenAILLM(api_key=openai_api_key)
            if cls._llm_instance.openai_client:  # Check if client initialized successfully
                print("✓ Using OpenAI LLM")
                cls._initialized = True
                return cls._llm_instance
            print("⚠️ OpenAI initialization failed, falling back to Groq")
            cls._llm_instance = None

        # Fallback to Groq
        if groq_api_key and not cls._initialized:
            cls._llm_instance = GroqLLM(api_key=groq_api_key)
            if cls._llm_instance.groq_client:
                print("✓ Using Groq LLM")
                cls._initialized = True
                return cls._llm_instance
            print("⚠️ Groq initialization failed")
            cls._llm_instance = None
            
        # Final fallback to Ollama if not explicitly chosen before
        if not use_ollama and not cls._initialized:
            try:
                print("✓ Attempting to use Ollama LLM as final fallback")
                cls._llm_instance = OllamaLLM(base_url=ollama_url)
                cls._initialized = True
                return cls._llm_instance
            except Exception as e:
                print(f"⚠️ Ollama fallback initialization failed: {e}")
                cls._llm_instance = None
            
        # No valid LLM available
        if not cls._initialized:
            raise ValueError("No valid LLM available. Set OPENAI_API_KEY, GROQ_API_KEY, or ensure Ollama is running locally with USE_OLLAMA=true in .env")
        
        return cls._llm_instance