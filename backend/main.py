from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import tempfile
import uuid
import threading
import os
import re
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

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://synthide.vercel.app"],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
)


# ====================
# CODE EXECUTION LOGIC
# ====================
class CodeRequest(BaseModel):
    code: str
    language: str
    input: str = ""

code_outputs = {}

@app.post("/run-code")
async def run_code(request: CodeRequest):
    run_id = str(uuid.uuid4())
    code_outputs[run_id] = ""
    threading.Thread(target=execute_code, args=(request.code, request.language, run_id, request.input)).start()
    return {"run_id": run_id}

@app.get("/get-output/{run_id}")
async def get_output(run_id: str):
    return {"output": code_outputs.get(run_id, "No such run ID.")}

def execute_code(code: str, language: str, run_id: str, input_data: str = ""):
    try:
        if language == "java":
            temp_dir = tempfile.mkdtemp()
            file_path = os.path.join(temp_dir, "Main.java")
            with open(file_path, "w") as f:
                f.write(code)
        else:
            with tempfile.NamedTemporaryFile(mode="w+", suffix=get_file_extension(language), delete=False) as tmp_file:
                tmp_file.write(code)
                tmp_file.flush()
                file_path = tmp_file.name

        cmd = get_command(language, file_path, run_id)
        if not cmd:
            return

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
        )
        stdout, _ = process.communicate(input=input_data)
        code_outputs[run_id] = stdout

    except Exception as e:
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
    elif language == "java":
        class_name = os.path.basename(filename).replace(".java", "")
        compile_cmd = ["javac", filename]
        compile_process = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if compile_process.returncode != 0:
            code_outputs[run_id] = compile_process.stdout
            return []
        return ["java", "-cp", os.path.dirname(filename), class_name]
    else:
        code_outputs[run_id] = f"Unsupported language: {language}"
        return []

# ====================
# CODE EXPLANATION LOGIC
# ====================
class ExplainRequest(BaseModel):
    code: str
    language: str

@app.post("/explain-code")
def explain_code(req: ExplainRequest):
    prompt = f"Explain this {req.language} code:\n\n{req.code}\n\nExplanation:"
    print("Received /explain-code request")
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
        print(f"Error calling OpenAI API: {e}")
        return {"explanation": f"Error: {str(e)}"}

# ====================
# CODE GENERATION LOGIC
# ====================
class GenerateRequest(BaseModel):
    prompt: str
    language: str

def wrap_in_main(code: str, language: str) -> str:
    code = code.strip()

    if language == "python":
        indented_code = code.replace('\n', '\n    ')
        return f"""def main():
    {indented_code}

if __name__ == "__main__":
    main()"""

    elif language == "cpp":
        indented_code = code.replace('\n', '\n    ')
        return f"""#include <iostream>
using namespace std;

int main() {{
    {indented_code}
    return 0;
}}"""

    elif language == "java":
        indented_code = code.replace('\n', '\n        ')
        return f"""public class Main {{
    public static void main(String[] args) {{
        {indented_code}
    }}
}}"""

    elif language == "javascript":
        indented_code = code.replace('\n', '\n    ')
        return f"""function main() {{
    {indented_code}
}}

main();"""

    else:
        return f"Unsupported language: {language}"

@app.post("/generate-code")
def generate_code(req: GenerateRequest):
    user_prompt = (
        f"Write only the raw {req.language} code logic for the following task. "
        "Do not add comments, explanation, or markdown. No formatting. Just clean code lines. "
        f"Task: {req.prompt}"
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

        # Clean markdown `` wrappers if present
        cleaned_code = re.sub(r"^```[a-z]*\n?|```$", "", raw_code, flags=re.IGNORECASE).strip()

        # Wrap appropriately
        final_code = wrap_in_main(cleaned_code, req.language.lower())

        return {"code": final_code}

    except Exception as e:
        return {"code": f"Error: {str(e)}"}
