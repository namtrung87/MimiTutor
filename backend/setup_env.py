import os

def prepare_env():
    # Check if .env exists, if not, create a template or use parent one
    parent_env = ".env"
    target_env = "05_Mimi_HomeTutor/backend/.env"
    
    if os.path.exists(parent_env) and not os.path.exists(target_env):
        with open(parent_env, 'r') as src, open(target_env, 'w') as dst:
            dst.write(src.read())
            print(f"Copied .env to {target_env}")

if __name__ == "__main__":
    prepare_env()
