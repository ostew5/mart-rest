import os
from llama_cpp import Llama

llm = Llama.from_pretrained(
	repo_id="ggml-org/SmolLM3-3B-GGUF",
	filename="/models/SmolLM3-Q4_K_M.gguf",
)

resp = llm("Hello!", max_tokens=64, temperature=0.7)
print(resp["choices"][0]["text"])
