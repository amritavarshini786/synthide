from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import tempfile
import uuid
import threading
import os
import re
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# Initialize FastAPI app
app = FastAPI()
subprocess.run(
    ["python3", "main.py"],
    timeout=3,  # Automatically kill it after 3 seconds
)
# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["https://synthide.vercel.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================
# DB INIT & LOGGING
# ====================
def init_db():
    conn = sqlite3.connect("usage.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            language TEXT,
            timestamp TEXT,
            ip TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def log_event(event_type, language, ip):
    conn = sqlite3.connect("usage.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO usage_stats (event_type, language, timestamp, ip) VALUES (?, ?, ?, ?)",
        (event_type, language, datetime.utcnow().isoformat(), ip)
    )
    conn.commit()
    conn.close()

# ====================
# CODE EXECUTION
# ====================
class CodeRequest(BaseModel):
    code: str
    language: str
    input: str = ""

code_outputs = {}

@app.post("/run-code")
async def run_code(request: CodeRequest, http_request: Request):
    run_id = str(uuid.uuid4())
    code_outputs[run_id] = ""  # placeholder to track execution status

    log_event("run_code", request.language, http_request.client.host)

    threading.Thread(
        target=execute_code,
        args=(request.code, request.language, run_id, request.input)
    ).start()

    return {"run_id": run_id}

@app.get("/get-output/{run_id}")
async def get_output(run_id: str):
    output = code_outputs.get(run_id)
    if output is None:
        return {"output": ""}
    return {"output": output}

def execute_code(code: str, language: str, run_id: str, input_data: str = ""):
    print(f"[EXECUTE] Running {language} code for run_id={run_id}")
    try:
        if language == "java":
            code_outputs[run_id] = "Java is not supported currently."
            return

        with tempfile.NamedTemporaryFile(mode="w+", suffix=get_file_extension(language), delete=False) as tmp_file:
            tmp_file.write(code)
            tmp_file.flush()
            file_path = tmp_file.name

        cmd = get_command(language, file_path, run_id)
        if not cmd:
            print(f"[EXECUTE] Invalid command for language: {language}")
            return

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
        )

        stdout, _ = process.communicate(input=input_data)
        print(f"[EXECUTE] Output for {run_id}:\n{stdout}")
        code_outputs[run_id] = stdout or "[No output]"

    except Exception as e:
        print(f"[ERROR] Code execution failed for {run_id}: {str(e)}")
        code_outputs[run_id] = f"Error during execution: {str(e)}"

def get_file_extension(language: str) -> str:
    return {
        "python": ".py",
        "javascript": ".js",
        "cpp": ".cpp",
        "java": ".java"
    }.get(language, ".txt")

def get_command(language: str, filename: str, run_id: str):
    if language == "python":
        return ["python", filename]
    elif language == "javascript":
        return ["node", filename]
    elif language == "cpp":
        exe_file = filename + ".exe"
        compile_cmd = ["g++", filename, "-o", exe_file]
        compile_process = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if compile_process.returncode != 0:
            code_outputs[run_id] = compile_process.stdout
            return []
        return [exe_file]
    else:
        code_outputs[run_id] = f"Unsupported language: {language}"
        return []

# ====================
# CODE EXPLANATION
# ====================
class ExplainRequest(BaseModel):
    code: str
    language: str

@app.post("/explain-code")
def explain_code(req: ExplainRequest):
    prompt = f"Explain this {req.language} code:\n\n{req.code}\n\nExplanation:"
    print("[EXPLAIN] Request received.")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that explains code."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.5,
        )
        explanation = response.choices[0].message.content.strip()
        return {"explanation": explanation}
    except Exception as e:
        print(f"[ERROR] Explanation failed: {e}")
        return {"explanation": f"Error: {str(e)}"}

# ====================
# CODE GENERATION
# ====================
class GenerateRequest(BaseModel):
    prompt: str
    language: str
    template: str

@app.post("/generate-code")
def generate_code(req: GenerateRequest):
    user_prompt = (
        f"You are to generate complete {req.language} code for the following task.\n\n"
        f"Base Template:\n{req.template}\n\n"
        f"Task:\n{req.prompt}\n\n"
        "Generate code in the same format as the template. Do not add explanations or markdown. Only output valid code."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a code-only generator assistant. Never return explanations or markdown."},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=300,
            temperature=0.3,
        )

        raw_code = response.choices[0].message.content.strip()
        cleaned_code = re.sub(r"^```[a-z]*\n?|```$", "", raw_code, flags=re.IGNORECASE).strip()

        log_event("generate_code", req.language, "unknown")
        print("[GENERATE] Code generated successfully.")
        return {"code": cleaned_code or "// No code returned by AI."}

    except Exception as e:
        print(f"[ERROR] Code generation failed: {e}")
        return {"code": f"Error: {str(e)}"}

# ====================
# STATS ENDPOINT
# ====================
@app.get("/stats")
def get_stats():
    conn = sqlite3.connect("usage.db")
    c = conn.cursor()

    total_runs = c.execute("SELECT COUNT(*) FROM usage_stats WHERE event_type = 'run_code'").fetchone()[0]
    total_generations = c.execute("SELECT COUNT(*) FROM usage_stats WHERE event_type = 'generate_code'").fetchone()[0]
    unique_users = c.execute("SELECT COUNT(DISTINCT ip) FROM usage_stats").fetchone()[0]

    conn.close()

    return {
        "total_code_runs": total_runs,
        "total_code_generations": total_generations,
        "unique_users": unique_users
    }

# Optional: root route to confirm server is up
@app.get("/")
def root():
    return {"message": "SynthIDE backend is running. Use /run-code, /generate-code, /stats, etc."}
