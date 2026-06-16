#!/usr/bin/env python3
import sys, os, re, json, shutil, subprocess
from datetime import datetime

AUDIT_LOG = "/var/log/ciso-onboarding/setup-audit.jsonl"
COMPOSE_PATH = "/home/ubuntu/ciso-assistant/docker-compose.yml"

def log_audit(entry):
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")

def run_migrations():
    print("Checking for pending GRC database migration updates...")
    installation_dir = "/home/ubuntu/ciso-installation"
    ciso_dir = "/home/ubuntu/ciso-assistant"
    history_file = "/home/ubuntu/ciso-assistant/applied_migrations.txt"
    
    if not os.path.exists(installation_dir):
        return
        
    # Get all python update scripts matching grc_update_*.py
    migration_files = []
    for f in os.listdir(installation_dir):
        if f.startswith("grc_update_") and f.endswith(".py"):
            migration_files.append(f)
            
    if not migration_files:
        print("No migration scripts found matching grc_update_*.py.")
        return
        
    migration_files.sort() # Run them sequentially (ordered by name/date)
    
    # Read already executed migrations
    applied = set()
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            for line in f:
                applied.add(line.strip())
                
    for script in migration_files:
        if script not in applied:
            print(f"Executing new migration script: {script}...")
            try:
                # Copy script into the CISO Assistant mounted db directory
                shutil.copy2(os.path.join(installation_dir, script), os.path.join(ciso_dir, "db", script))
                
                # Execute script inside the backend docker container
                cmd = ["docker", "compose", "exec", "-T", "backend", "python", f"db/{script}"]
                r = subprocess.run(cmd, cwd=ciso_dir, capture_output=True, text=True)
                
                if r.returncode == 0:
                    print(f"[SUCCESS] Migration script {script} executed successfully.")
                    # Add to history
                    with open(history_file, "a") as hf:
                        hf.write(f"{script}\n")
                else:
                    print(f"[ERROR] Migration script {script} failed with exit code {r.returncode}.")
                    print(r.stderr)
            except Exception as e:
                print(f"[ERROR] Failed to run migration script {script}: {e}")

def patch(compose_path, public_url, public_host):
    with open(compose_path, "r") as f:
        old_content = f.read()
    content = old_content
    content = re.sub(r'(- ALLOWED_HOSTS=).*', rf'\g<1>backend,localhost,{public_host}', content)
    content = re.sub(r'(- CISO_ASSISTANT_URL=).*', rf'\g<1>{public_url}', content)
    content = re.sub(r'(- CSRF_TRUSTED_ORIGINS=).*', r'\g<1>https://trycloudflare.com,https://*.trycloudflare.com', content)
    content = re.sub(r'(- PUBLIC_BACKEND_API_EXPOSED_URL=).*', rf'\g<1>{public_url}/api', content)
    content = re.sub(r'(- ORIGIN=).*', rf'\g<1>{public_url}', content)
    content = re.sub(r'(localhost:443, )[a-z0-9-]+\.trycloudflare\.com(:443 \{)', rf'\g<1>{public_host}\g<2>', content)
    
    if old_content == content:
        print("Configuration is already up to date. No restart needed.")
        # Try running migrations even if compose layout was up to date
        run_migrations()
        return

    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    backup = f"/opt/ciso-setup-archive/{ts}/docker-compose.yml"
    os.makedirs(os.path.dirname(backup), exist_ok=True)
    shutil.copy2(compose_path, backup)
    
    with open(compose_path, "w") as f:
        f.write(content)
    try:
        r = subprocess.run(["docker", "compose", "config", "--quiet"],
            cwd=os.path.dirname(compose_path), capture_output=True, timeout=30)
        valid = r.returncode == 0
    except Exception:
        valid = False
    if not valid:
        shutil.copy2(backup, compose_path)
        print("VALIDATION FAILED - backup restored")
        log_audit({"timestamp": datetime.utcnow().isoformat()+"Z", "step":"patch_ciso_compose","status":"failed","public_url":public_url})
        sys.exit(1)
    
    print("Validation OK. Applying changes via docker compose...")
    try:
        subprocess.run(["docker", "compose", "up", "-d"], cwd=os.path.dirname(compose_path), check=True)
        print("Docker containers successfully updated.")
        log_audit({"timestamp": datetime.utcnow().isoformat()+"Z", "step":"patch_ciso_compose","status":"success","public_url":public_url,"public_host":public_host,"backup_path":backup})
        
        # Execute any new database updates
        run_migrations()

        # Trigger email notification if script exists
        mail_script = "/usr/local/bin/send-tunnel-url-mail.sh"
        if os.path.exists(mail_script):
            print("Triggering email notification...")
            subprocess.run([mail_script, public_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error applying changes: {e}")
        shutil.copy2(backup, compose_path)
        subprocess.run(["docker", "compose", "up", "-d"], cwd=os.path.dirname(compose_path))
        sys.exit(1)

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    if not url:
        m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', open("/var/log/cloudflared.log").read())
        url = m.group(0) if m else None
    if not url:
        print("No URL found"); sys.exit(1)
    host = url.replace("https://", "")
    patch(COMPOSE_PATH, url, host)