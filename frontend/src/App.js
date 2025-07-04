import React, { useState, useEffect } from "react";
import CodeEditor from "./components/editor";
import "./App.css";

function App() {
  const [code, setCode] = useState("// Write your code here...");
  const [language, setLanguage] = useState("python");
  const [runId, setRunId] = useState(null);
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState("light");
  const [testInput, setTestInput] = useState("");
  const [mode, setMode] = useState("editor");
  const [prompt, setPrompt] = useState("");

  const explainCode = async () => {
    try {
      setOutput("Explaining code...");
      const res = await fetch("https://synthide.onrender.com/explain-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
        code,
        language, // send current template shown in editor
    }),

      });
      const data = await res.json();
      setOutput(data.explanation || "No explanation received.");
    } catch (err) {
      setOutput("Error explaining the code.");
    }
  };

  useEffect(() => {
    const handleError = (event) => {
      console.error("Global error caught:", event.error || event.message);
      event.preventDefault();
    };

    const handleRejection = (event) => {
      console.error("Unhandled promise rejection:", event.reason);
      event.preventDefault();
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleRejection);

    return () => {
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleRejection);
    };
  }, []);

  useEffect(() => {
    const templates = {
      python: `def main():\n    # Write your code here\n    \nif __name__ == "__main__":\n    main()`,
      javascript: `function main() {\n    // Write your code here\n}\n\nmain();`,
      cpp: `#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your code here\n    return 0;\n}`,
      // java: `public class Main {\n    public static void main(String[] args) {\n        // Write your code here\n    }\n}`,
    };
    setCode(templates[language] || "// Start coding...");
  }, [language]);

  const sendCodeToBackend = async () => {
    setLoading(true);
    setOutput("");
    setRunId(null);
    try {
      const res = await fetch("https://synthide.onrender.com/run-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, language, input: testInput }),
      });
      const data = await res.json();
      setRunId(data.run_id);
    } catch (err) {
      setOutput("Error sending code to backend");
      setLoading(false);
    }
  };

  useEffect(() => {
  if (!runId) return;

  let retryCount = 0;
  const maxRetries = 15;
  const interval = setInterval(async () => {
    retryCount++;
    if (retryCount > maxRetries) {
      setOutput("Execution timed out or error occurred.");
      setLoading(false);
      clearInterval(interval);
      return;
    }

    try {
      const res = await fetch(`https://synthide.onrender.com/get-output/${runId}`);
      if (!res.ok) throw new Error("Network response not ok");

      const data = await res.json();

      // Update output even if it's an empty string
      if (data.output !== undefined) {
        setOutput(data.output);
        setLoading(false);
        clearInterval(interval);
      }
    } catch (err) {
      // Do NOT overwrite good output if error occurs later
      if (!output) {
        setOutput("Error fetching output");
      }
      setLoading(false);
      clearInterval(interval);
    }
  }, 1000);

  return () => clearInterval(interval);
}, [runId]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  return (
    <div
      className={`App ${theme}`}
      style={{
        height: "100vh",
        padding: 20,
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <h1>SynthIDE</h1>

      {/* Mode Selector */}
      <div style={{ display: "flex", gap: 10, marginBottom: 20 }}>
        <button
          onClick={() => setMode("editor")}
          style={{
            padding: "10px 20px",
            backgroundColor: mode === "editor" ? "#007bff" : "#ccc",
            color: mode === "editor" ? "#fff" : "#000",
            border: "none",
            borderRadius: 5,
            cursor: "pointer",
          }}
        >
          Code Editor
        </button>
        <button
          onClick={() => setMode("generator")}
          style={{
            padding: "10px 20px",
            backgroundColor: mode === "generator" ? "#007bff" : "#ccc",
            color: mode === "generator" ? "#fff" : "#000",
            border: "none",
            borderRadius: 5,
            cursor: "pointer",
          }}
        >
          Code Generator
        </button>
      </div>

      {/* Language & Theme Selector */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 20,
          marginBottom: 10,
        }}
      >
        <label htmlFor="language-select" style={{ fontWeight: "bold" }}>
          Select Language:
        </label>
        <select
          id="language-select"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          style={{
            padding: "5px 10px",
            fontSize: 14,
            borderRadius: 4,
            border: `1px solid ${theme === "dark" ? "#444" : "#ccc"}`,
            backgroundColor: theme === "dark" ? "#252526" : "#fff",
            color: theme === "dark" ? "#d4d4d4" : "#000",
            cursor: "pointer",
          }}
        >
          <option value="python">Python</option>
          <option value="javascript">JavaScript</option>
          <option value="cpp">C++</option>
          {/* <option value="java">Java</option> */}
        </select>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label htmlFor="theme-toggle" style={{ fontWeight: "bold" }}>
            {theme === "dark" ? "Light Mode" : "Dark Mode"}:
          </label>
          <input
            type="checkbox"
            id="theme-toggle"
            checked={theme === "dark"}
            onChange={toggleTheme}
            style={{ width: 40, height: 20, cursor: "pointer" }}
          />
        </div>
      </div>

      {/* Main View Logic */}
      {mode === "editor" && (
        <>
          <div
            style={{
              display: "flex",
              gap: 20,
              flex: 1,
              marginTop: 20,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                flex: 2,
                border: `1px solid ${theme === "dark" ? "#444" : "#ccc"}`,
                borderRadius: 8,
                padding: 10,
                backgroundColor: theme === "dark" ? "#1e1e1e" : "#fff",
              }}
            >
              <CodeEditor
                code={code}
                setCode={setCode}
                language={language}
                theme={theme}
              />
            </div>

            <div
              style={{
                flex: 1,
                border: `1px solid ${theme === "dark" ? "#444" : "#ccc"}`,
                borderRadius: 8,
                padding: 10,
                backgroundColor: theme === "dark" ? "#1e1e1e" : "#fff",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <label
                htmlFor="testInput"
                style={{ fontWeight: "bold", marginBottom: 5 }}
              >
                Test Input:
              </label>
              <textarea
                id="testInput"
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                style={{
                  flex: 1,
                  width: "100%",
                  fontFamily: "monospace",
                  fontSize: 14,
                  backgroundColor: theme === "dark" ? "#252526" : "#f5f5f5",
                  color: theme === "dark" ? "#d4d4d4" : "#000",
                  border: "1px solid",
                  borderColor: theme === "dark" ? "#333" : "#ccc",
                  borderRadius: 5,
                  padding: 10,
                  resize: "none",
                  minHeight: 300,
                }}
                placeholder="Enter test input here..."
              />
            </div>
          </div>

          <button
            onClick={sendCodeToBackend}
            className="run-btn"
            disabled={loading}
            style={{
              marginTop: 20,
              padding: "10px 20px",
              fontSize: 16,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Running..." : "Run Code"}
          </button>

          <button
            onClick={explainCode}
            className="run-btn"
            disabled={loading}
            style={{
              marginTop: 10,
              padding: "10px 20px",
              fontSize: 16,
              backgroundColor: "#28a745",
              color: "white",
              border: "none",
              borderRadius: 5,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            Explain Code
          </button>
        </>
      )}

      {mode === "generator" && (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "stretch",
          }}
        >
          <label style={{ fontWeight: "bold", marginBottom: 10 }}>
            Describe what code you want:
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            style={{
              width: "100%",
              minHeight: 150,
              fontSize: 16,
              fontFamily: "monospace",
              padding: 10,
              borderRadius: 5,
              backgroundColor: theme === "dark" ? "#252526" : "#f5f5f5",
              color: theme === "dark" ? "#d4d4d4" : "#000",
              border: `1px solid ${theme === "dark" ? "#444" : "#ccc"}`,
            }}
            placeholder="e.g. Code to check if a number is prime"
          />
          <button
            onClick={async () => {
              try {
                setOutput("Generating code...");
                const res = await fetch("https://synthide.onrender.com/generate-code", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ prompt, language, template: code, }),
                });
                const data = await res.json();
                setCode(data.code || "// No code generated.");
                setOutput("Code generated successfully.");
              } catch (err) {
                setOutput("Error generating code.");
              }
            }}
            style={{
              marginTop: 20,
              padding: "10px 20px",
              fontSize: 16,
              backgroundColor: "#007bff",
              color: "#fff",
              border: "none",
              borderRadius: 5,
              cursor: "pointer",
            }}
          >
            Generate Code
          </button>
        </div>
      )}

      <div
        className="output-box"
        style={{
          height: "12vh",
          overflowY: "auto",
          border: `1px solid ${theme === "dark" ? "#444" : "#ccc"}`,
          borderRadius: 8,
          padding: 10,
          marginTop: 10,
          backgroundColor: theme === "dark" ? "#1e1e1e" : "#fff",
          color: theme === "dark" ? "#d4d4d4" : "#000",
          whiteSpace: "pre-wrap",
        }}
      >
        <h3>Output:</h3>
        <pre style={{ margin: 0 }}>
          {output || (loading ? "Running..." : "No output yet")}
        </pre>
      </div>
    </div>
  );
}

export default App;
