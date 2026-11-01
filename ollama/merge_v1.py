import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, PreTrainedTokenizerFast

HERE = Path(__file__).resolve().parent
if len(sys.argv) == 4:
    base = sys.argv[1]
    adapter = sys.argv[2]
    out = sys.argv[3]
else:
    base = HERE / "llama-3-8b"
    adapter = HERE / "litlex-v1-adapter"
    out = HERE / "litlex-v1-merged"

model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.bfloat16, device_map="cpu")
model = PeftModel.from_pretrained(model, adapter)
model = model.merge_and_unload()
model.save_pretrained(out, safe_serialization=True)
tokenizer = PreTrainedTokenizerFast.from_pretrained(adapter)
tokenizer.save_pretrained(out)
print(f"-> {out}")
