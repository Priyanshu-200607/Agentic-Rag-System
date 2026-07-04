import os
import sys
import subprocess
import shutil
import venv

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(text):
    print(f"\n{'='*55}\n{text}\n{'='*55}")

def run_cmd(cmd, env=None, cwd=None):
    try:
        subprocess.check_call(cmd, env=env, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"\n[Error] Command failed: {' '.join(cmd)}")
        sys.exit(1)

def main():
    clear_screen()
    print_header("Department RAG System - Unified Auto Installer")
    
    # 1. OS & Environment Selection
    print("Please select your target Operating System / Environment:")
    print("1) Linux (Desktop/Local)")
    print("2) Mac (Apple Silicon or Intel)")
    print("3) Windows (Desktop/Local)")
    print("4) Server (Headless Cloud Node / Ubuntu Server)")
    
    os_choice = input("\nEnter choice (1/2/3/4): ").strip()
    if os_choice not in ["1", "2", "3", "4"]:
        print("Invalid choice. Exiting.")
        sys.exit(1)

    is_windows = (os_choice == "3")
    is_mac = (os_choice == "2")
    is_linux_or_server = (os_choice in ["1", "4"])

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
            print(f"Copying project files to {install_path}...")
            for item in os.listdir(current_dir):
                if item in ['.git', 'backend/env', 'venv']:
                    continue
                s = os.path.join(current_dir, item)
                d = os.path.join(install_path, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

    # 3. Create Virtual Environment
    print_header("Setting up Virtual Environment")
    backend_dir = os.path.join(install_path, "backend")
    if not os.path.exists(backend_dir):
        print(f"[Error] 'backend' folder not found. Are you running this from the repository root?")
        sys.exit(1)

    venv_dir = os.path.join(backend_dir, "env")
    print(f"Creating Python virtual environment in: {venv_dir}")
    venv.create(venv_dir, with_pip=True)

    # Determine pip and python paths based on chosen OS structure
    if is_windows:
        pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        pip_exe = os.path.join(venv_dir, "bin", "pip")
        python_exe = os.path.join(venv_dir, "bin", "python")

    # Upgrade pip
    run_cmd([python_exe, "-m", "pip", "install", "--upgrade", "pip"], cwd=backend_dir)

    # 4. Dependency Configuration (Version Pinned for Stability)
    print_header("Installing Core Dependencies")
    
    # Conflict-free pinned core dependencies common to all platforms
    core_packages = [
        "fastapi==0.110.0",
        "uvicorn==0.29.0",
        "python-multipart==0.0.9",
        "python-jose==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "chromadb==0.4.24",
        "ollama==0.1.7",
        "pypdf==4.1.0",
        "python-docx==1.1.0",
        "psutil==5.9.8",
        "sentence-transformers==2.5.1"
    ]
    
    # Install core packages safely
    run_cmd([pip_exe, "install"] + core_packages, cwd=backend_dir)

    print_header("Installing OS-Specific AI Acceleration Libraries")
    if is_linux_or_server or is_windows:
        print("Installing PyTorch 2.2.1 with CUDA 12.1 support...")
        # PyTorch with CUDA support (Crucial for Linux, Server, and Windows with NVIDIA GPUs)
        run_cmd([
            pip_exe, "install", 
            "torch==2.2.1+cu121", 
            "torchvision==0.17.1+cu121", 
            "torchaudio==2.2.1+cu121", 
            "--index-url", "https://download.pytorch.org/whl/cu121"
        ], cwd=backend_dir)
        
        # Bitsandbytes for 8-bit LLM optimization (highly recommended for Linux/Server)
        print("Installing bitsandbytes optimization (8-bit quantization)...")
        run_cmd([pip_exe, "install", "bitsandbytes==0.43.0"], cwd=backend_dir)
        
    elif is_mac:
        print("Installing PyTorch 2.2.1 with Native MPS (Apple Silicon) Support...")
        # PyTorch standard install contains native Apple Silicon (MPS) acceleration out of the box
        run_cmd([
            pip_exe, "install", 
            "torch==2.2.1", 
            "torchvision==0.17.1", 
            "torchaudio==2.2.1"
        ], cwd=backend_dir)
        print("Note: bitsandbytes is not supported on Mac. 8-bit quantization will be bypassed automatically.")

    # 5. Local LLM Setup (Ollama)
    print_header("Local LLM Setup (Ollama)")
    try:
        # Check if ollama CLI is installed globally
        subprocess.check_output(["ollama", "--version"], stderr=subprocess.STDOUT)
        print("Ollama engine detected on your system!")
        pull_choice = input("Would you like to automatically pull the 'llama3' model now? (y/n) [y]: ").strip().lower() or 'y'
        if pull_choice == 'y':
            print("Pulling llama3 model... (This may take a few minutes depending on your internet speed)")
            subprocess.run(["ollama", "pull", "llama3"])
            print("Model pulled successfully!")
        else:
            print("Skipping model pull.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[Warning] Ollama engine not detected on your system path.")
        print("You will need to manually install Ollama from https://ollama.com/ and run 'ollama pull llama3' before starting the server.")

    print_header("Installation Complete!")
    print("Everything is set up with strict, conflict-free versions specifically for your OS.")
    print("\nTo start the server:")
    print(f"1. Open a terminal in: {backend_dir}")
    if is_windows:
        print("2. Activate env:  env\\Scripts\\activate")
    else:
        print("2. Activate env:  source env/bin/activate")
    print("3. Start server:  uvicorn api:app --reload")
    
if __name__ == "__main__":
    main()
