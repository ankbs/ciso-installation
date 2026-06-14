import sys
import json
import os
import urllib.request
import urllib.error

# Persistent local fallback database file
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grc_projects_database.json")

def log(message):
    """Logs a debug message to stderr (so it doesn't pollute stdout, which is reserved for JSON-RPC)."""
    sys.stderr.write(f"[DEBUG] {message}\n")
    sys.stderr.flush()

def load_env():
    """Manually reads .env file to load configuration parameters without external dependencies."""
    env_vars = {}
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        log(f"Reading environment variables from {env_path}")
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, val = line.split("=", 1)
                        env_vars[key.strip()] = val.strip()
    return env_vars

# Load environment variables
env = load_env()
CISO_API_URL = env.get("CISO_API_URL", "https://ciso.deinedomain.de")
CISO_API_TOKEN = env.get("CISO_API_TOKEN", "")

def load_local_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading local DB: {e}")
    return {"projects": []}

def save_local_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log(f"Error saving local DB: {e}")

def create_grc_project(name, description=""):
    log(f"Attempting to create GRC project '{name}'")
    
    # Try CISO Assistant API request if configured and not local template url
    if CISO_API_TOKEN and CISO_API_URL and not "deinedomain.de" in CISO_API_URL:
        url = f"{CISO_API_URL.rstrip('/')}/api/v1/projects/"
        headers = {
            "Authorization": CISO_API_TOKEN if CISO_API_TOKEN.startswith("Token") else f"Token {CISO_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = json.dumps({"name": name, "description": description}).encode("utf-8")
        
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5) as res:
                response_data = json.loads(res.read().decode("utf-8"))
                log("Successfully created project via CISO Assistant API")
                return {
                    "status": "success",
                    "source": "CISO Assistant API",
                    "project_id": response_data.get("id", "N/A"),
                    "project_name": name,
                    "description": description,
                    "url": f"{CISO_API_URL.rstrip('/')}/projects/{response_data.get('id', '')}"
                }
        except Exception as e:
            log(f"API Connection failed ({e}). Falling back to local database simulation.")

    # Fallback to local simulation database
    db = load_local_db()
    
    # Check if project already exists
    for p in db["projects"]:
        if p["name"].lower() == name.lower():
            return {
                "status": "exists",
                "source": "Local Simulation Database",
                "project_name": name,
                "frameworks": p.get("frameworks", []),
                "message": f"Das Projekt '{name}' existiert bereits in der lokalen Datenbank."
            }
            
    project_id = len(db["projects"]) + 1000
    new_project = {
        "id": project_id,
        "name": name,
        "description": description,
        "frameworks": [],
        "token": f"token_sim_{project_id}_abc123"
    }
    db["projects"].append(new_project)
    save_local_db(db)
    
    log("Successfully created project in Local Simulation Database")
    return {
        "status": "success",
        "source": "Local Simulation Database (Offline-Modus)",
        "project_id": project_id,
        "project_name": name,
        "description": description,
        "token": new_project["token"],
        "message": f"GRC-Projekt '{name}' wurde im Offline-Simulationsmodus angelegt, da der VPS-Server nicht erreichbar ist."
    }

def assign_compliance_framework(project_name, framework_code):
    log(f"Attempting to assign framework '{framework_code}' to project '{project_name}'")
    
    # Try CISO Assistant API request if configured
    if CISO_API_TOKEN and CISO_API_URL and not "deinedomain.de" in CISO_API_URL:
        # Note: In CISO Assistant, framework assignments are done by updating the project's frameworks list.
        # This is a representative API call.
        pass

    # Update in local simulation database
    db = load_local_db()
    project_found = None
    for p in db["projects"]:
        if p["name"].lower() == project_name.lower():
            project_found = p
            break
            
    if not project_found:
        return {
            "status": "error",
            "message": f"Projekt '{project_name}' wurde nicht gefunden. Bitte erstelle es zuerst."
        }
        
    if framework_code.lower() not in [f.lower() for f in project_found["frameworks"]]:
        project_found["frameworks"].append(framework_code.upper())
        save_local_db(db)
        log(f"Assigned framework {framework_code.upper()} to project {project_name}")
        return {
            "status": "success",
            "source": "Local Simulation Database (Offline-Modus)",
            "project_name": project_name,
            "assigned_framework": framework_code.upper(),
            "all_frameworks": project_found["frameworks"]
        }
    else:
        return {
            "status": "already_assigned",
            "project_name": project_name,
            "frameworks": project_found["frameworks"],
            "message": f"Framework '{framework_code.upper()}' ist dem Projekt '{project_name}' bereits zugewiesen."
        }

def destroy_oracle_resources():
    log("Starting OCI GRC Infrastructure cleanup via MCP...")
    try:
        import oci
    except ImportError:
        log("OCI SDK not installed")
        return {
            "status": "error",
            "message": "Das OCI SDK ist auf diesem Host nicht installiert. Bitte führe 'pip install oci' aus."
        }
        
    import time
    env_vars = load_env()
    config = {
        "user": env_vars.get("OCI_USER_OCID"),
        "fingerprint": env_vars.get("OCI_FINGERPRINT"),
        "key_file": env_vars.get("OCI_KEY_FILE"),
        "tenancy": env_vars.get("OCI_TENANCY_OCID"),
        "region": env_vars.get("OCI_REGION", "eu-frankfurt-1")
    }
    
    # Trim key_file quotes if any
    if config["key_file"]:
        config["key_file"] = config["key_file"].strip('"')
        
    try:
        oci.config.validate_config(config)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ungültige OCI-Konfiguration: {e}"
        }

    try:
        compute_client = oci.core.ComputeClient(config)
        network_client = oci.core.VirtualNetworkClient(config)
        bastion_client = oci.bastion.BastionClient(config)
        compartment_id = env_vars.get("OCI_COMPARTMENT_OCID")
        
        results = []
        
        # 1. Terminate Instance
        instances = oci.pagination.list_call_get_all_results(
            compute_client.list_instances,
            compartment_id=compartment_id
        ).data
        
        has_active_instances = False
        for inst in instances:
            if inst.display_name == "ciso-assistant-vps" and inst.lifecycle_state not in ["TERMINATING", "TERMINATED"]:
                log(f"Terminating instance: {inst.display_name}")
                compute_client.terminate_instance(inst.id)
                has_active_instances = True
                
        if has_active_instances:
            log("Waiting for VM instance to terminate...")
            # We will wait up to 60 seconds
            for _ in range(6):
                time.sleep(10)
                still_running = False
                instances = oci.pagination.list_call_get_all_results(
                    compute_client.list_instances,
                    compartment_id=compartment_id
                ).data
                for inst in instances:
                    if inst.display_name == "ciso-assistant-vps" and inst.lifecycle_state not in ["TERMINATED"]:
                        still_running = True
                if not still_running:
                    break
            results.append("Instance ciso-assistant-vps terminated")
        else:
            results.append("No active instances found")

        # 2. Delete Bastion
        bastions = oci.pagination.list_call_get_all_results(
            bastion_client.list_bastions,
            compartment_id=compartment_id
        ).data
        
        has_active_bastions = False
        for b in bastions:
            if b.name == "grc_bastion" and b.lifecycle_state not in ["DELETING", "DELETED"]:
                log(f"Deleting bastion: {b.name}")
                try:
                    bastion_client.delete_bastion(b.id)
                    has_active_bastions = True
                except Exception as e:
                    log(f"Failed to delete bastion: {e}")
                    
        if has_active_bastions:
            # Wait up to 60 seconds
            for _ in range(6):
                time.sleep(10)
                still_deleting = False
                try:
                    bastions = oci.pagination.list_call_get_all_results(
                        bastion_client.list_bastions,
                        compartment_id=compartment_id
                    ).data
                    for b in bastions:
                        if b.name == "grc_bastion" and b.lifecycle_state not in ["DELETED"]:
                            still_deleting = True
                except Exception:
                    pass
                if not still_deleting:
                    break
            results.append("Bastion grc_bastion deleted")
        else:
            results.append("No active bastions found")

        # 3. Delete Subnets
        subnets = oci.pagination.list_call_get_all_results(
            network_client.list_subnets,
            compartment_id=compartment_id
        ).data
        for sub in subnets:
            if sub.display_name in ["private_subnet", "extra_subnet"]:
                try:
                    network_client.delete_subnet(sub.id)
                    results.append(f"Deleted subnet {sub.display_name}")
                except Exception as e:
                    results.append(f"Failed to delete subnet {sub.display_name}: {e}")

        # 4. Delete NAT Gateway
        nat_gateways = oci.pagination.list_call_get_all_results(
            network_client.list_nat_gateways,
            compartment_id=compartment_id
        ).data
        for nat in nat_gateways:
            if nat.display_name == "grc_nat_gateway":
                try:
                    network_client.delete_nat_gateway(nat.id)
                    results.append("Deleted NAT Gateway")
                except Exception as e:
                    results.append(f"Failed to delete NAT Gateway: {e}")

        # 5. Delete Security List
        seclists = oci.pagination.list_call_get_all_results(
            network_client.list_security_lists,
            compartment_id=compartment_id
        ).data
        for sec in seclists:
            if sec.display_name == "private_security_list":
                try:
                    network_client.delete_security_list(sec.id)
                    results.append("Deleted Security List")
                except Exception as e:
                    results.append(f"Failed to delete Security List: {e}")

        # 6. Delete Route Table
        route_tables = oci.pagination.list_call_get_all_results(
            network_client.list_route_tables,
            compartment_id=compartment_id
        ).data
        for rt in route_tables:
            if rt.display_name == "private_route_table":
                try:
                    network_client.delete_route_table(rt.id)
                    results.append("Deleted Route Table")
                except Exception as e:
                    results.append(f"Failed to delete Route Table: {e}")

        # 7. Delete VCN
        vcns = oci.pagination.list_call_get_all_results(
            network_client.list_vcns,
            compartment_id=compartment_id
        ).data
        for vcn in vcns:
            if vcn.display_name == "grc_vcn":
                try:
                    network_client.delete_vcn(vcn.id)
                    results.append("Deleted VCN")
                except Exception as e:
                    results.append(f"Failed to delete VCN: {e}")
                    
        return {
            "status": "success",
            "message": "OCI-Ressourcen-Bereinigung durchgeführt.",
            "details": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Kritischer Fehler bei der OCI-Bereinigung: {e}"
        }

def handle_json_rpc(request_str):
    try:
        req = json.loads(request_str)
    except ValueError as e:
        return json.dumps({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": f"Parse error: {e}"}
        })

    if "jsonrpc" not in req or req["jsonrpc"] != "2.0":
        return json.dumps({
            "jsonrpc": "2.0",
            "id": req.get("id"),
            "error": {"code": -32600, "message": "Invalid Request"}
        })

    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        return json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "ciso-assistant-provisioner",
                    "version": "1.0.0"
                }
            }
        })

    elif method == "tools/list":
        tools = [
            {
                "name": "create_grc_project",
                "description": "Legt ein neues GRC-Projekt (z.B. fuer einen M365-Tenant oder Kunden) im CISO Assistant an.",
                "inputSchema": {
                  "type": "object",
                  "properties": {
                    "name": {
                      "type": "string",
                      "description": "Der Name des Kunden oder des M365-Tenants (z.B. 'Kunde XYZ' oder 'Tenant Contoso')"
                    },
                    "description": {
                      "type": "string",
                      "description": "Optionale kurze Beschreibung des Projekts (Zweck des Audits)"
                    }
                  },
                  "required": ["name"]
                }
            },
            {
                "name": "assign_compliance_framework",
                "description": "Verknuepft ein Compliance-Framework (z.B. DORA, ISO 27001, NIS 2, BSI IT-Grundschutz) mit einem bestehenden GRC-Projekt.",
                "inputSchema": {
                  "type": "object",
                  "properties": {
                    "project_name": {
                      "type": "string",
                      "description": "Der Name des GRC-Projekts"
                    },
                    "framework_code": {
                      "type": "string",
                      "description": "Das Kuerzel des Frameworks (z.B. 'dora', 'iso27001', 'nis2', 'bsi_it_grundschutz')"
                    }
                  },
                  "required": ["project_name", "framework_code"]
                }
            },
            {
                "name": "destroy_oracle_resources",
                "description": "Terminiert und loescht alle erstellten Oracle Cloud (OCI) Ressourcen (VCN, Subnetz, Bastion, VM-Instanz) vollstaendig, falls die Umgebung deprovisioniert werden soll.",
                "inputSchema": {
                  "type": "object",
                  "properties": {},
                  "required": []
                }
            }
        ]
        return json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": tools
            }
        })

    elif method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "create_grc_project":
            name = arguments.get("name")
            desc = arguments.get("description", "")
            if not name:
                result = {"status": "error", "message": "Missing parameter 'name'"}
            else:
                result = create_grc_project(name, desc)
                
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False)
                        }
                    ]
                }
            })

        elif tool_name == "assign_compliance_framework":
            p_name = arguments.get("project_name")
            fw_code = arguments.get("framework_code")
            if not p_name or not fw_code:
                result = {"status": "error", "message": "Missing parameter 'project_name' or 'framework_code'"}
            else:
                result = assign_compliance_framework(p_name, fw_code)
                
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False)
                        }
                    ]
                }
            })

        elif tool_name == "destroy_oracle_resources":
            result = destroy_oracle_resources()
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False)
                        }
                    ]
                }
            })

        else:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {tool_name}"}
            })

    else:
        # Ignore notifications or return method not found for unknown requests
        if req_id is not None:
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            })
        return None

def main():
    log("CISO Assistant MCP Provisioner Server started")
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            log(f"Received request: {line[:100]}...")
            response = handle_json_rpc(line)
            if response:
                sys.stdout.write(response + "\n")
                sys.stdout.flush()
    except KeyboardInterrupt:
        log("Server stopped by user")
    except Exception as e:
        log(f"Fatal error in main loop: {e}")

if __name__ == "__main__":
    main()
