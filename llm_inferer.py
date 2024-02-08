# -*- coding: utf-8 -*-
"""LLM inferer.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/19q3qvzHF_00DQ6r2rKCMqhUEJApm_T9w
"""

pip install accelerate

from transformers import AutoModelForCausalLM, AutoTokenizer


model_path = "kedarbhumkar/Mistral-7b-ft-122223"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    device_map="auto",
    torch_dtype='auto'
).eval()

# Prompt content: "hi"
messages = [
    {"role": "user", "content": "Give three tips for staying healthy ?"}
]

input_ids = tokenizer.apply_chat_template(conversation=messages, tokenize=True, add_generation_prompt=True, return_tensors='pt')
output_ids = model.generate(input_ids.to('cuda'))
response = tokenizer.decode(output_ids[0][input_ids.shape[1]:], skip_special_tokens=True)

# Model response: "Hello! How can I assist you today?"
print(response)



