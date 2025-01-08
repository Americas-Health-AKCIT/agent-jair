import os
import dotenv
dotenv.load_dotenv()

def mistral_small(prompt):
    from mistralai import Mistral
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    res = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    return res.choices[0].message.content


def mistral_large(prompt):
    from mistralai import Mistral
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    res = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    return res.choices[0].message.content

def open_mixtral_8x22b(prompt):
    from mistralai import Mistral
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    res = client.chat.complete(
        model="open-mixtral-8x22b",
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    return res.choices[0].message.content