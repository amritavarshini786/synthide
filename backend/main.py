from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import tempfile
import uuid
import threading
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

# Load environment variables
load_dotenv()

# OpenAI setup
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# FastAPI app initialization
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging to Supabase
def log_event(event_type, language, ip, run_id=None, output=None):
    supabase.table("usage_stats").insert({
        "event_type": event_type,
        "language": language,
        "timestamp": datetime.utcnow().isoformat(),
        "ip": ip,
        "run_id": run_id,
        "output": output
    }).execute()

# Request Models
class CodeRequest(BaseModel):
    code: str
    language: str
    input: str = ""

class ExplainRequest(BaseModel):
    code: str
    language: str

class GenerateRequest(BaseModel):
    prompt: str
    language: str
    template: str

# Endpoint: Run Code
@app.post("/run-code")
async def run_code(request: CodeRequest, http_request: Request):
    run_id = str(uuid.uuid4())
    threading.Thread(
        target=execute_code,
        args=(request.code, request.language, run_id, request.input, http_request.client.host)
    ).start()
    return {"run_id": run_id}

# Endpoint: Get Output (from Supabase)
@app.get("/get-output/{run_id}")
async def get_output(run_id: str):
    result = supabase.table("usage_stats").select("output").eq("run_id", run_id).execute()
    if result.data:
        return {"output": result.data[0]["output"]}
    return {"output": "⏳ Still running or output not found."}

# Execute code in subprocess
def execute_code(code: str, language: str, run_id: str, input_data: str = "", ip: str = "unknown"):
    print(f"[EXECUTE] Running {language} code for run_id={run_id}")
    try:
        if language == "java":
            output = "Java is not supported currently."
            log_event("run_code", language, ip, run_id, output)
            return

        with tempfile.NamedTemporaryFile(mode="w+", suffix=get_file_extension(language), delete=False) as tmp_file:
            tmp_file.write(code)
            tmp_file.flush()
            file_path = tmp_file.name

        cmd = get_command(language, file_path, run_id)
        if not cmd:
            log_event("run_code", language, ip, run_id, "[Invalid command or compilation failed]")
            return

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
        )
        stdout, _ = process.communicate(input=input_data)
        output = stdout or "[No output]"

    except Exception as e:
        output = f"Error during execution: {str(e)}"

    log_event("run_code", language, ip, run_id, output)
    print(f"[EXECUTE] Output for {run_id}:\n{output}")

# Helpers

def get_file_extension(language: str) -> str:
    return {
        "python": ".py",
        "javascript": ".js",
        "cpp": ".cpp",
        "java": ".java"
    }.get(language, ".txt")

import platform

def get_command(language: str, filename: str, run_id: str):
    if language == "python":
        return ["python", filename]
    
    elif language == "javascript":
        return ["node", filename]
    
    elif language == "cpp":
        # Determine the output binary name based on OS
        if platform.system() == "Windows":
            exe_file = filename.replace(".cpp", "") + ".exe"
        else:
            exe_file = filename.replace(".cpp", "")

        # Compile the C++ code
        compile_cmd = ["g++", filename, "-o", exe_file]
        compile_process = subprocess.run(
            compile_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # If compilation fails
        if compile_process.returncode != 0:
            error_output = compile_process.stdout.strip()
            print(f"[COMPILE ERROR] {error_output}")
            log_event("run_code", "cpp", "compile", run_id, error_output)
            return []

        # Make the binary executable on Linux/macOS
        if platform.system() != "Windows":
            try:
                os.chmod(exe_file, 0o755)
            except Exception as chmod_error:
                print(f"[CHMOD ERROR] Failed to chmod {exe_file}: {chmod_error}")

        return [exe_file]
    
    else:
        return []

# Endpoint: Explain Code
@app.post("/explain-code")
def explain_code(req: ExplainRequest):
    prompt = f"Explain this {req.language} code in simple language, briefly, only give explanation, no other lines:\n\n{req.code}\n\nExplanation:"
    models = [
        "deepseek-ai/deepseek-coder:33b-instruct",
        "google/codegemma-7b-it",
        "meta-llama/codellama-70b-instruct",
        "phind/phind-codellama-34b",
        "mistralai/mixtral-8x7b-instruct",
    ]
    for model in models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that explains code."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.5,
            )
            explanation = response.choices[0].message.content.strip()
            return {"explanation": explanation}
        except Exception as e:
            continue
    return {"explanation": "not currently available"}

# Endpoint: Generate Code
@app.post("/generate-code")
def generate_code(req: GenerateRequest):
    user_prompt = (
        f"You are a professional {req.language} developer. "
        f"Generate only valid, clean, runnable code in this language.\n\n"
        f"Use this base template:\n{req.template}\n\n"
        f"Task:\n{req.prompt}\n\n"
        "⚠️ Do NOT include explanations, markdown, or comments unless asked. Just output the code file content."
    )
    models = [
        "deepseek-ai/deepseek-coder:33b-instruct",
        "google/codegemma-7b-it",
        "meta-llama/codellama-70b-instruct",
        "phind/phind-codellama-34b",
        "mistralai/mixtral-8x7b-instruct",
    ]
    for model in models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a code-only generator assistant. Never return explanations or markdown."},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4000,
                temperature=0.3,
            )
            raw_code = response.choices[0].message.content.strip()
            cleaned_code = re.sub(r"^```[a-z]*\n?|```$", "", raw_code, flags=re.IGNORECASE).strip()
            log_event("generate_code", req.language, "unknown")
            return {"code": cleaned_code or "// No code returned by AI."}
        except Exception as e:
            continue
    return {"code": "not currently available"}

# Endpoint: Stats
@app.get("/stats")
def get_stats():
    all_data = supabase.table("usage_stats").select("*").execute().data
    total_runs = sum(1 for d in all_data if d["event_type"] == "run_code")
    total_generations = sum(1 for d in all_data if d["event_type"] == "generate_code")
    unique_users = len(set(d["ip"] for d in all_data if d["ip"]))
    return {
        "total_code_runs": total_runs,
        "total_code_generations": total_generations,
        "unique_users": unique_users
    }

# Root endpoint
@app.get("/")
def root():
    return {"message": "SynthIDE backend is running. Use /run-code, /generate-code, /stats, etc."}
