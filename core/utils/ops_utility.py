import socket
import os

def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a local port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False

# Mapping of ports to descriptions and restart commands
SYSTEM_HEALTH_CONFIG = {
    3000: {
        "name": "Frontend (Next.js/React)",
        "fix_command": "npm run dev",
        "working_dir": "e:/Drive/Antigravitiy/Orchesta assistant"
    },
    8000: {
        "name": "Backend (FastAPI)",
        "fix_command": "python main.py",
        "working_dir": "e:/Drive/Antigravitiy/Orchesta assistant"
    },
    11434: {
        "name": "Ollama (Local LLM)",
        "fix_command": "ollama serve",
        "working_dir": "."
    }
}

def get_system_health_report() -> str:
    """Returns a formatted string of system health status."""
    report = []
    for port, info in SYSTEM_HEALTH_CONFIG.items():
        status = "✅ ONLINE" if is_port_open(port) else "❌ OFFLINE"
        line = f"- {info['name']} (Port {port}): {status}"
        if status == "❌ OFFLINE":
            line += f" -> [FIX]: Run `{info['fix_command']}` in {info['working_dir']}"
        report.append(line)
    return "\n".join(report)

if __name__ == "__main__":
    print("Checking system health...")
    print(get_system_health_report())
