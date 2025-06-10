/* eslint-disable no-template-curly-in-string */

import React, { useEffect } from "react";
import MonacoEditor, { useMonaco } from "@monaco-editor/react";

export default function CodeEditor({ language, code, setCode, theme }) {
  const monaco = useMonaco();

  useEffect(() => {
    if (!monaco) return;
  if (!language || !["python", "javascript", "cpp", "java"].includes(language)) return;

  const disposable = monaco.languages.registerCompletionItemProvider(language, {
      provideCompletionItems: () => {
        let suggestions = [];

        if (language === "python") {
          suggestions = [
            {
              label: "print",
              kind: monaco.languages.CompletionItemKind.Function,
              insertText: "print(${1})",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Print statement",
            },
            {
              label: "for loop",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText: "for ${1:item} in ${2:iterable}:\n\t${3:pass}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "For loop",
            },
            {
              label: "if statement",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText: "if ${1:condition}:\n\t${2:pass}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "If statement",
            },
            {
              label: "def function",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "def ${1:function_name}(${2:args}):\n\t${3:pass}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Function definition",
            },
            {
              label: "class",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "class ${1:ClassName}(${2:object}):\n\tdef __init__(self, ${3:args}):\n\t\t${4:pass}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Class definition",
            },
          ];
        } else if (language === "javascript") {
          suggestions = [
            {
              label: "console.log",
              kind: monaco.languages.CompletionItemKind.Function,
              insertText: "console.log(${1});",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Console log",
            },
            {
              label: "for loop",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "for (let ${1:i} = 0; ${1:i} < ${2:array}.length; ${1:i}++) {\n\t${3:// code}\n}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "For loop",
            },
            {
              label: "function",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "function ${1:functionName}(${2:args}) {\n\t${3:// code}\n}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Function declaration",
            },
            {
              label: "arrow function",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "const ${1:functionName} = (${2:args}) => {\n\t${3:// code}\n};",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Arrow function",
            },
            {
              label: "if statement",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "if (${1:condition}) {\n\t${2:// code}\n}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "If statement",
            },
          ];
        } else if (language === "cpp") {
          suggestions = [
            {
              label: "include iostream",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText: "#include <iostream>",
              documentation: "Include iostream header",
            },
            {
              label: "main function",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "int main() {\n\t${1:// code}\n\treturn 0;\n}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Main function",
            },
            {
              label: "for loop",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n\t${3:// code}\n}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "For loop",
            },
            {
              label: "cout",
              kind: monaco.languages.CompletionItemKind.Function,
              insertText: "std::cout << ${1:output} << std::endl;",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Print to console",
            },
          ];
        } else if (language === "java") {
          suggestions = [
            {
              label: "main method",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "public static void main(String[] args) {\n\t${1:// code}\n}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Main method",
            },
            {
              label: "class",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "public class ${1:ClassName} {\n\tpublic ${1:ClassName}() {\n\t\t${2:// constructor}\n\t}\n}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Class definition",
            },
            {
              label: "for loop",
              kind: monaco.languages.CompletionItemKind.Snippet,
              insertText:
                "for (int ${1:i} = 0; ${1:i} < ${2:n}; ${1:i}++) {\n\t${3:// code}\n}",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "For loop",
            },
            {
              label: "System.out.println",
              kind: monaco.languages.CompletionItemKind.Function,
              insertText: "System.out.println(${1});",
              insertTextRules:
                monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              documentation: "Print statement",
            },
          ];
        }

        return { suggestions };
      },
    });
    return()=>{
      disposable.dispose();
    }
  }, [monaco, language]);

  return (
    <MonacoEditor
      height="400px"
      language={language}
      value={code}
      onChange={(value) => setCode(value)}
      theme={theme === "dark" ? "vs-dark" : "light"}
      options={{
        fontSize: 16,
        minimap: { enabled: false },
        suggestOnTriggerCharacters: true,
        quickSuggestions: true,
      }}
    />
  );
}
