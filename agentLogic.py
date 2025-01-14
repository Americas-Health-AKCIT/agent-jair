import dotenv
dotenv.load_dotenv()

import sys
print(sys.executable)

from utils.state import STATE_CLASS
from utils.get_requisition_details import get_requisition_details

def get_state():
    return STATE_CLASS()

state = get_state()

resumo = get_requisition_details(41002890, state) # Req do sample de agosto

print("Resumo: ", resumo)