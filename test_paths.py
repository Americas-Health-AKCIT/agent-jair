import os

def list_files():
    # List files in root
    print("Root directory:")
    for file in os.listdir('.'):
        if file.endswith('.py'):
            print(f"  {file}")
    
    # List files in pages directory
    print("\nPages directory:")
    if os.path.exists('pages'):
        for file in os.listdir('pages'):
            if file.endswith('.py'):
                print(f"  {file}")

list_files()