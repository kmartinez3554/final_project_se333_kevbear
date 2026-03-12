# SE333 Final Project — AI-Powered Testing Agent

An intelligent testing agent built with **Model Context Protocol (MCP)** that automatically generates, executes, and iterates on JUnit 5 test cases to maximise code coverage on a Java Maven project.

---

## Project Structure

```
se333-mcp-server/          # MCP server (Python / FastMCP)
│   main.py                # Server entrypoint — all MCP tools defined here

se333-demo/                # Client workspace (Java Maven project)
│   pom.xml                # Maven config with JaCoCo plugin
│   .github/
│       prompts/
│           tester.prompt.md   # Agent prompt — drives the testing loop
│   src/
│       main/java/com/se333/demo/   # Application source code
│       test/java/com/se333/demo/   # Generated test classes
```

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| VS Code | Latest | https://code.visualstudio.com |
| Node.js | 18+ LTS | https://nodejs.org |
| Python | 3.11+ | https://python.org |
| uv | Latest | https://astral.sh/uv |
| Java JDK | 11+ | https://adoptium.net |
| Maven | 3.6+ | https://maven.apache.org |
| Git | Latest | https://git-scm.com |

---

## Setup

### 1. Clone or download this repository

```bash
git clone <your-repo-url>
cd se333-mcp-server
```

### 2. Set up the MCP server

```bash
# From inside se333-mcp-server/
uv init
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv add "mcp[cli]" httpx fastmcp
```

### 3. Start the MCP server

```bash
python main.py
```

You should see FastMCP start on `http://127.0.0.1:8000/sse`.

### 4. Connect the server to VS Code

1. Press `Ctrl+Shift+P` → search **MCP: Add Server**
2. Paste URL: `http://127.0.0.1:8000/sse`
3. Name it: `se333-mcp-server`
4. Open the resulting `mcp.json` — confirm the server shows **Running**

### 5. Enable Auto-Approve (YOLO mode)

`Ctrl+Shift+P` → **Chat: Settings** → enable **Auto-Approve**

### 6. Open the demo project

Open the `se333-demo/` folder in VS Code as a **separate window**.

### 7. Run the agent

In VS Code Chat (Agent mode), type:

```
#file:.github/prompts/tester.prompt.md
```

The agent will read your source files, create a Git branch, run Maven, parse JaCoCo, and iterate until coverage is maximised.

---

## MCP Tools API

### `add(a, b)`
Basic smoke-test tool. Returns `a + b`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `a` | int | First operand |
| `b` | int | Second operand |

**Returns:** int

---

### `parse_jacoco(jacoco_xml_path)`
Parses a JaCoCo XML report and identifies coverage gaps.

| Parameter | Type | Description |
|-----------|------|-------------|
| `jacoco_xml_path` | str | Path to `jacoco.xml`, e.g. `target/site/jacoco/jacoco.xml` |

**Returns:**
```json
{
  "overall": {
    "line": 72.5,
    "branch": 60.0,
    "method": 80.0,
    "instruction": 71.0
  },
  "uncovered_methods": [
    { "class": "com.se333.Calculator", "method": "divide", "missed_lines": 4 }
  ],
  "uncovered_classes": ["com.se333.StringUtils"],
  "summary": "Line coverage: 72.5% | Branch: 60%. Priority: Calculator.divide(), ..."
}
```

---

### `generate_bva_tests(class_name, method_name, param_name, param_type, min_value, max_value)`
Generates boundary value analysis test skeletons for numeric parameters.

| Parameter | Type | Description |
|-----------|------|-------------|
| `class_name` | str | Java class name, e.g. `Calculator` |
| `method_name` | str | Method under test, e.g. `divide` |
| `param_name` | str | Parameter name, e.g. `divisor` |
| `param_type` | str | Java type: `int` or `double` |
| `min_value` | str | Minimum valid value, e.g. `"1"` |
| `max_value` | str | Maximum valid value, e.g. `"100"` |

**Returns:**
```json
{
  "test_values": [
    { "value": 0, "category": "below min — invalid", "expected_valid": false },
    { "value": 1, "category": "min boundary — valid",  "expected_valid": true }
  ],
  "junit5_snippet": "// @ParameterizedTest skeleton..."
}
```

---

## Git Workflow

This project uses a **trunk-based** workflow:

```
main  (trunk — never commit directly)
 └── feature/tests-gen-iteration-1   ← agent works here
 └── feature/tests-gen-iteration-2
```

Each iteration the agent:
1. Creates a feature branch
2. Adds/improves test files
3. Commits with a meaningful message
4. Opens a pull request to `main`

---

## Troubleshooting

**Server won't start**
- Confirm you activated the virtual environment: `source .venv/bin/activate`
- Confirm fastmcp is installed: `uv pip list | grep fastmcp`

**VS Code can't connect to MCP server**
- Make sure `python main.py` is still running in a terminal
- Check the URL in `mcp.json` matches `http://127.0.0.1:8000/sse`
- Try restarting VS Code

**`mvn clean test` fails with "No tests found"**
- Confirm your test class name ends in `Test.java`
- Confirm the package in the test file matches `src/test/java/<package>/`

**JaCoCo XML not found**
- Run `mvn clean test` first (not just `mvn test`) — the `clean` ensures a fresh report
- Look for the file at `target/site/jacoco/jacoco.xml`

**Coverage stays stuck**
- Some methods (framework-generated, abstract) cannot be tested directly — document this in the PR
- Try calling `generate_bva_tests` for any method with numeric inputs

---

## FAQ

**Why two separate VS Code projects?**
The MCP server and the code-under-test live in separate projects to mirror real-world usage where tools are shared across repositories. The server is a service; the demo project is the client.

**Can I use this on my own Java project?**
Yes — copy `pom.xml` (or add the JaCoCo plugin to your existing POM), start the MCP server, open your project in VS Code, and run the prompt.

**Does the agent fix bugs automatically?**
Yes — if a generated test exposes a bug (e.g. the test asserts the correct result but the method returns something wrong), the agent diagnoses the failure, patches the application code, and commits the fix with a descriptive message before continuing.