from diffusers import StableDiffusionPipeline
from huggingface_hub import hf_hub_download
import torch
import peft

base_model_path = "runwayml/stable-diffusion-v1-5"
lora_weights_file_path = hf_hub_download(repo_id="Jiho0o0/diff_kfood_finetuned", filename="pytorch_lora_weights.safetensors")
lora_weights_path = "Jiho0o0/diff_kfood_finetuned"

pipe = StableDiffusionPipeline.from_pretrained(base_model_path, torch_dtype=torch.float16).to("cuda")
pipe.load_lora_weights(lora_weights_path)

image = pipe('Kimchi Jjigae (Kimchi Stew)').images[0]
image.show()
