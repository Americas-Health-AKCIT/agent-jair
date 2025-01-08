import os, dotenv, time
from models.cohere import command_r_plus_08_2024
from models.openai_models import gpt_4o, gpt_4o_mini
from models.mistral import mistral_small, mistral_large, open_mixtral_8x22b
from models.gemini import gemini_flash
from models.llama import llama_8B,Mistral_nemo_12B
dotenv.load_dotenv()

models = {  # Modelos disponíveis para utilizar
            "command_r_plus_08_2024": command_r_plus_08_2024,
            "GPT-4o": gpt_4o,
            "GPT-4o-mini": gpt_4o_mini,
            "Mistral_Small": mistral_small,
            "Mistral_Large": mistral_large,
            "Gemini_Flash": gemini_flash,
            "llama-3.1-8B": llama_8B,
            "Mistral-Nemo": Mistral_nemo_12B,
            "open-mixtral-8x22b": open_mixtral_8x22b,
        }


model_select = os.getenv("JUDGE_MODEL",None)

if model_select not in models.keys():
    raise ValueError(f"\n\nModel {model_select} not found, please select one of the following: {list(models.keys())} and set the 'JUDGE_MODEL' environment variable")


def run_prompt(prompt):
    tentativas = 0
    while tentativas < 5:
        try:
            return models[model_select](prompt)
        except Exception as e:
            tentativas += 1
            print(f"Error in model {model_select}, trying again... {tentativas}")
            time.sleep(0.5)
            
            if tentativas == 5:
                print(f'Tentativas em chamar o modelo {model_select} excedidas')
                raise e
