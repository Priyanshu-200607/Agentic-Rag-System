import os
import sys
import platform
import subprocess
import shutil
import venv

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(text):
    print(f"\n{'='*50}\n{text}\n{'='*50}")

def run_cmd(cmd, env=None, cwd=None):
    try:
        subprocess.check_call(cmd, env=env, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"\n[Error] Command failed: {' '.join(cmd)}")
        sys.exit(1)

def main():
    clear_screen()
    print_header("Department RAG System - Auto Installer")
    
    # 1. OS Detection
    os_name = platform.system()
    print(f"Detected OS: {os_name}")

    # 2. Select Installation Directory
    current_dir = os.path.abspath(os.path.dirname(__file__))
    print(f"\nCurrent directory: {current_dir}")
    install_path = input("Enter installation path [Press Enter to use current directory]: ").strip()
    
    if not install_path:
        install_path = current_dir
    else:
        install_path = os.path.abspath(install_path)
        if not os.path.exists(install_path):
            os.makedirs(install_path)
        if install_path != current_dir:
            print(f"Copying files to {install_path}...")
            # Simple copy logic (excluding .git and environments)
            for item in os.listdir(current_dir):
                if item in ['.git', 'backend/env', 'venv']:
                    continue
                s = os.path.join(current_dir, item)
                d = os.path.join(install_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

    # 3. Hardware Detection / Selection
    print_header("Hardware Acceleration Setup")
    print("This system auto-scales based on hardware. Please select your primary compute device:")
    print("1) NVIDIA GPU (CUDA) - Recommended for Windows/Linux Servers")
    print("2) Apple Silicon (M1/M2/M3 - MPS) - Recommended for Mac")
    print("3) CPU Only - Standard but slower")
    
    hw_choice = input("Enter choice (1/2/3) [Default: 3]: ").strip() or "3"

    # 4. Create Virtual Environment
    print_header("Setting up Virtual Environment")
    backend_dir = os.path.join(install_path, "backend")
    if not os.path.exists(backend_dir):
        print(f"[Error] 'backend' folder not found in {install_path}. Ensure you clone the full repo.")
        sys.exit(1)

    venv_dir = os.path.join(backend_dir, "env")
    print(f"Creating Python virtual environment in: {venv_dir}")
    venv.create(venv_dir, with_pip=True)

    # Determine pip path
    if os_name == "Windows":
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        python_exe = os.path.join(venv_dir, "bin", "python")

    # Upgrade pip
    run_cmd([python_exe, "-m", "pip", "install", "--upgrade", "pip"], cwd=backend_dir)

    # 5. Install Dependencies
    print_header("Installing Dependencies")
    
    # First, install base requirements
    req_path = os.path.join(backend_dir, "requirements.txt")
    print(f"Installing base packages from {req_path}...")
    run_cmd([pip_exe, "install", "-r", "requirements.txt"], cwd=backend_dir)

    # Second, install hardware-specific PyTorch (since sentence-transformers brings a generic one)
    if hw_choice == "1":
        print("\nInstalling PyTorch with CUDA support...")
        run_cmd([
            pip_exe, "install", "torch", "torchvision", "torchaudio", 
            "--index-url", "https://download.pytorch.org/whl/cu121"
        ], cwd=backend_dir)
        print("\nInstalling bitsandbytes for 8-bit quantization...")
        run_cmd([pip_exe, "install", "bitsandbytes"], cwd=backend_dir)
    elif hw_choice == "2":
        print("\nApple Silicon selected. PyTorch MPS support is included natively in the base installation.")
    else:
        print("\nCPU setup complete. Base PyTorch is installed.")

    print_header("Installation Complete!")
    print("To run the system:")
    print("1) Ensure Ollama is installed (https://ollama.com/) and running.")
    print(f"2) Open a terminal and navigate to: {backend_dir}")
    if os_name == "Windows":
        print("3) Run: env\\Scripts\\activate")
    else:
        print("3) Run: source env/bin/activate")
    print("4) Start the server: uvicorn api:app --reload")

if __name__ == "__main__":
    main()
