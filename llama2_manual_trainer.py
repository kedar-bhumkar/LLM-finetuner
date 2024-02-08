# -*- coding: utf-8 -*-
"""LLAMA2-manual-trainer.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1jrKQtpZ5xM22SRtXH-swzlLb_anI9L0K
"""

!pip install -q -U git+https://github.com/huggingface/transformers.git
!pip install -q -U git+https://github.com/huggingface/peft.git
!pip install -q -U git+https://github.com/huggingface/accelerate.git
!pip install -q trl xformers wandb datasets einops gradio sentencepiece bitsandbytes

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, HfArgumentParser, TrainingArguments, pipeline, logging, TextStreamer
from peft import LoraConfig, PeftModel, prepare_model_for_kbit_training, get_peft_model
import os,torch, wandb, platform, gradio, warnings
from datasets import load_dataset
from trl import SFTTrainer
from huggingface_hub import notebook_login

def print_system_specs():
    # Check if CUDA is available
    is_cuda_available = torch.cuda.is_available()
    print("CUDA Available:", is_cuda_available)
# Get the number of available CUDA devices
    num_cuda_devices = torch.cuda.device_count()
    print("Number of CUDA devices:", num_cuda_devices)
    if is_cuda_available:
        for i in range(num_cuda_devices):
            # Get CUDA device properties
            device = torch.device('cuda', i)
            print(f"--- CUDA Device {i} ---")
            print("Name:", torch.cuda.get_device_name(i))
            print("Compute Capability:", torch.cuda.get_device_capability(i))
            print("Total Memory:", torch.cuda.get_device_properties(i).total_memory, "bytes")
    # Get CPU information
    print("--- CPU Information ---")
    print("Processor:", platform.processor())
    print("System:", platform.system(), platform.release())
    print("Python Version:", platform.python_version())
print_system_specs()

# Pre trained model
model_name = "meta-llama/Llama-2-7b-hf"

# Dataset name
# dataset_name = "vicgalle/alpaca-gpt4"
dataset_name = "kedarbhumkar/alpaca-small50"

# Hugging face repository link to save fine-tuned model(Create new repository in huggingface,copy and paste here)
new_model = "https://huggingface.co/kedarbhumkar/LLAMA2-manual-1_3_2024"

notebook_login

# Load dataset (you can process it here)
dataset = load_dataset(dataset_name, split="train[0:10]")
dataset["text"][0]

# Load base model(llama-2-7b-hf) and tokenizer
bnb_config = BitsAndBytesConfig(
    load_in_4bit= True,
    bnb_4bit_quant_type= "nf4",
    bnb_4bit_compute_dtype= "bfloat16",
    bnb_4bit_use_double_quant= False,
)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map={"": 0}
)
model = prepare_model_for_kbit_training(model)
model.config.use_cache = False # silence the warnings. Please re-enable for inference!
model.config.pretraining_tp = 1
# Load LLaMA tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.add_eos_token = True
tokenizer.add_bos_token, tokenizer.add_eos_token

#monitering login
wandb.login(key="")
run = wandb.init(project='Fine tuning llama-2-7B', job_type="training", anonymous="allow")

peft_config = LoraConfig(
    lora_alpha= 8,
    lora_dropout= 0.1,
    r= 16,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj","gate_proj", "up_proj"]
)

training_arguments = TrainingArguments(
    output_dir= "./results",
    num_train_epochs= 3,
    per_device_train_batch_size= 8,
    gradient_accumulation_steps= 2,
    optim = "paged_adamw_8bit",
    save_steps= 1000,
    logging_steps= 30,
    learning_rate= 2e-4,
    weight_decay= 0.001,
    fp16= False,
    bf16= False,
    max_grad_norm= 0.3,
    max_steps= -1,
    warmup_ratio= 0.3,
    group_by_length= True,
    lr_scheduler_type= "linear",
    report_to="wandb",
)

# Setting sft parameters
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    peft_config=peft_config,
    max_seq_length= None,
    dataset_text_field="text",
    tokenizer=tokenizer,
    args=training_arguments,
    packing= False,
)

# Train model
trainer.train()

# Save the fine-tuned model
trainer.model.save_pretrained(new_model)
wandb.finish()
model.config.use_cache = True
model.eval()

def stream(user_prompt):
    runtimeFlag = "cuda:0"
    system_prompt = 'Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n'
    B_INST, E_INST = "### Instruction:\n", "### Response:\n"

    prompt = f"{system_prompt}{B_INST}{user_prompt.strip()}\n\n{E_INST}"

    inputs = tokenizer([prompt], return_tensors="pt").to(runtimeFlag)

    streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    # Despite returning the usual output, the streamer will also print the generated text to stdout.
    _ = model.generate(**inputs, streamer=streamer, max_new_tokens=500)

stream("what is newtons 2rd law and its formula")

# Clear the memory footprint
del model, trainer
torch.cuda.empty_cache()

base_model = AutoModelForCausalLM.from_pretrained(
    model_name, low_cpu_mem_usage=True,
    return_dict=True,torch_dtype=torch.float16,
    device_map= {"": 0})
model = PeftModel.from_pretrained(base_model, new_model)
model = model.merge_and_unload()

# Reload tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model.push_to_hub(new_model)
tokenizer.push_to_hub(new_model)