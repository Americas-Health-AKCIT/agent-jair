import os
import dotenv
dotenv.load_dotenv()

def command_r_plus_08_2024(prompt):    
    import cohere
    co = cohere.ClientV2(api_key=os.getenv("COHERE_API_KEY"))
    res = co.chat(
        model="command-r-plus-08-2024",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )
    return res.message.content[0].text # "The Ultimate Guide to API Design: Best Practices for Building Robust and Scalable APIs"
