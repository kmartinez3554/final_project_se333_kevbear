from fastmcp import FastMCP
import xml.etree.ElementTree as ET
import subprocess
import os

mcp = FastMCP("se333-mcp-server 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

@mcp.tool
def parse_jacoco(jacoco_xml_path: str) -> dict:
    """
    Parse a JaCoCo XML coverage report and return a structured summary.

    Args:
        jacoco_xml_path: Absolute or relative path to the jacoco.xml file,
                         typically at target/site/jacoco/jacoco.xml

    Returns:
        A dict with:
          - overall: {instruction, branch, line, complexity, method, class} coverage %
          - uncovered_methods: list of {class, method, missed_lines}
          - uncovered_classes: list of class names with 0% line coverage
          - summary: human-readable string describing what to test next
    """
    if not os.path.exists(jacoco_xml_path):
        return {"error": f"File not found: {jacoco_xml_path}"}

    try:
        tree = ET.parse(jacoco_xml_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return {"error": f"Failed to parse XML: {e}"}

    def pct(missed: int, covered: int) -> float:
        total = missed + covered
        return round(covered / total * 100, 1) if total > 0 else 100.0

    overall = {}
    for counter in root.findall("counter"):
        ctype = counter.get("type", "").lower()
        missed = int(counter.get("missed", 0))
        covered = int(counter.get("covered", 0))
        overall[ctype] = pct(missed, covered)

    uncovered_methods = []
    uncovered_classes = []

    for pkg in root.findall(".//package"):
        for cls in pkg.findall("class"):
            class_name = cls.get("name", "").replace("/", ".")

            line_counter = None
            for c in cls.findall("counter"):
                if c.get("type") == "LINE":
                    line_counter = c
                    break

            if line_counter is not None:
                missed = int(line_counter.get("missed", 0))
                covered = int(line_counter.get("covered", 0))
                if missed > 0 and covered == 0:
                    uncovered_classes.append(class_name)

            for method in cls.findall("method"):
                method_name = method.get("name", "")
                if method_name in ("<init>", "<clinit>"):
                    continue

                missed_lines = 0
                for c in method.findall("counter"):
                    if c.get("type") == "LINE":
                        missed_lines = int(c.get("missed", 0))
                        break

                if missed_lines > 0:
                    uncovered_methods.append({
                        "class": class_name,
                        "method": method_name,
                        "missed_lines": missed_lines,
                    })

    uncovered_methods.sort(key=lambda m: m["missed_lines"], reverse=True)

    line_pct = overall.get("line", 0.0)
    branch_pct = overall.get("branch", 0.0)

    if not uncovered_methods:
        summary = "All methods appear to be covered. Check branch coverage for remaining gaps."
    else:
        top = uncovered_methods[:3]
        names = ", ".join(f"{m['class']}.{m['method']}()" for m in top)
        summary = (
            f"Line coverage: {line_pct}% | Branch coverage: {branch_pct}%. "
            f"Priority methods to test next: {names}."
        )

    return {
        "overall": overall,
        "uncovered_methods": uncovered_methods,
        "uncovered_classes": uncovered_classes,
        "summary": summary,
    }

@mcp.tool
def generate_bva_tests(
    class_name: str,
    method_name: str,
    param_name: str,
    param_type: str,
    min_value: str,
    max_value: str,
) -> dict:
    """
    Generate boundary value analysis (BVA) test cases for a numeric method parameter.

    Applies the standard BVA partition:
      min-1, min, min+1, typical midpoint, max-1, max, max+1

    Args:
        class_name:  Simple Java class name, e.g. "Calculator"
        method_name: Method under test, e.g. "divide"
        param_name:  Parameter name, e.g. "divisor"
        param_type:  Java type: "int" or "double"
        min_value:   Minimum valid value as a string, e.g. "1"
        max_value:   Maximum valid value as a string, e.g. "100"

    Returns:
        A dict with:
          - test_values: list of {value, category, expected_valid}
          - junit5_snippet: ready-to-paste JUnit 5 @ParameterizedTest skeleton
    """
    is_int = param_type.strip().lower() in ("int", "integer", "long")

    try:
        lo = int(min_value) if is_int else float(min_value)
        hi = int(max_value) if is_int else float(max_value)
    except ValueError:
        return {"error": "min_value and max_value must be numeric strings."}

    mid = (lo + hi) // 2 if is_int else round((lo + hi) / 2, 4)
    delta = 1 if is_int else 1e-4

    candidates = [
        (lo - delta, "below min — invalid"),
        (lo,         "min boundary — valid"),
        (lo + delta, "just above min — valid"),
        (mid,        "midpoint — valid"),
        (hi - delta, "just below max — valid"),
        (hi,         "max boundary — valid"),
        (hi + delta, "above max — invalid"),
    ]

    test_values = [
        {
            "value": int(v) if is_int else v,
            "category": cat,
            "expected_valid": "invalid" not in cat,
        }
        for v, cat in candidates
    ]

    valid_vals = [t["value"] for t in test_values if t["expected_valid"]]
    invalid_vals = [t["value"] for t in test_values if not t["expected_valid"]]

    valid_args = ", ".join(str(v) for v in valid_vals)
    invalid_args = ", ".join(str(v) for v in invalid_vals)

    snippet = f"""// Auto-generated BVA tests for {class_name}.{method_name}({param_name})
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static org.junit.jupiter.api.Assertions.*;

class {class_name}BVATest {{

    {class_name} sut = new {class_name}();

    @ParameterizedTest(name = "{param_name} = {{0}} should be valid")
    @ValueSource({param_type}s = {{ {valid_args} }})
    void valid_{param_name}_values({param_type} {param_name}) {{
        assertDoesNotThrow(() -> sut.{method_name}({param_name}));
    }}

    @ParameterizedTest(name = "{param_name} = {{0}} should be invalid")
    @ValueSource({param_type}s = {{ {invalid_args} }})
    void invalid_{param_name}_values({param_type} {param_name}) {{
        assertThrows(IllegalArgumentException.class, () -> sut.{method_name}({param_name}));
    }}
}}
"""

    return {
        "test_values": test_values,
        "junit5_snippet": snippet,
    }

if __name__ == "__main__":
    mcp.run(transport="sse")