import dotenv,os

dotenv.load_dotenv()

## 4bit pre quantized models we support for 4x faster downloading + no OOMs.
#    fourbit_models = [
#        "unsloth/Meta-Llama-3.1-8B-bnb-4bit",      # Llama-3.1 15 trillion tokens model 2x faster!
#        "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit",
#        "unsloth/Meta-Llama-3.1-70B-bnb-4bit",
#        "unsloth/Meta-Llama-3.1-405B-bnb-4bit",    # We also uploaded 4bit for 405b!
#        "unsloth/Mistral-Nemo-Base-2407-bnb-4bit", # New Mistral 12b 2x faster!
#        "unsloth/Mistral-Nemo-Instruct-2407-bnb-4bit",
#        "unsloth/mistral-7b-v0.3-bnb-4bit",        # Mistral v3 2x faster!
#        "unsloth/mistral-7b-instruct-v0.3-bnb-4bit",
#        "unsloth/Phi-3.5-mini-instruct",           # Phi-3.5 2x faster!
#        "unsloth/Phi-3-medium-4k-instruct",
#        "unsloth/gemma-2-9b-bnb-4bit",
#        "unsloth/gemma-2-27b-bnb-4bit",            # Gemma 2x faster!
#    ]


pipeline = None

if os.getenv("JUDGE_MODEL") in ['llama-3.1-8B', 'Mistral-Nemo']:
    import torch,transformers
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import get_chat_template

    if os.getenv("JUDGE_MODEL") == 'llama-3.1-8B':
        model, tokenizer = FastLanguageModel.from_pretrained( model_name = "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit", load_in_4bit = True )
    if os.getenv("JUDGE_MODEL") == 'Mistral-Nemo':
        model, tokenizer = FastLanguageModel.from_pretrained( model_name = "unsloth/Mistral-Nemo-Instruct-2407-bnb-4bit", load_in_4bit = True )
    
    FastLanguageModel.for_inference(model)
    tokenizer = get_chat_template(tokenizer)
    pipeline = transformers.pipeline( "text-generation", model=model, tokenizer=tokenizer)
    print("model loaded!")
    
    
def llama_8B(prompt):
    print("start resposta", len(prompt))
    outputs = pipeline( [ {"role": "user", "content": prompt}],
        temperature=0.1,
        top_k=1,       
        max_new_tokens=3000
    )
    print("end resposta", len(outputs[0]["generated_text"][-1]['content']))
    
    return outputs[0]["generated_text"][-1]['content']


def Mistral_nemo_12B(prompt):
    print("start resposta", len(prompt))
    outputs = pipeline( [ {"role": "user", "content": prompt}],
        temperature=0.1,
        top_k=1,       
        max_new_tokens=3000
    )
    print("end resposta", len(outputs[0]["generated_text"][-1]['content']))
    
    return outputs[0]["generated_text"][-1]['content']