import time
from agentic_ai.core.llm.factory import LLMFactory

def verify_llm_rate_limit():
    """
    A simple script to verify the LLM rate limiting.
    """
    print("Verifying LLM rate limiting...")
    llm = LLMFactory.get_llm()
    
    if not hasattr(llm, '_call'):
        print("LLM not properly initialized. Cannot verify rate limit.")
        return

    # Make rapid calls to test rate limiting
    for i in range(5):
        start_time = time.time()
        print(f"Making call {i+1}...")
        response = llm._call(f"This is a test prompt {i+1}.")
        end_time = time.time()
        print(f"Response: {response}")
        print(f"Time taken: {end_time - start_time:.2f}s\n")

if __name__ == "__main__":
    verify_llm_rate_limit()