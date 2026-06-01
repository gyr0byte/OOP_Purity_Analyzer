"""Regex/Pattern-based AST heuristic analyzer for supported OOP languages.

Extracts object-oriented structure metrics from source code files to adjust
the static language-level purity scores based on actual code design.
"""

import re
from typing import Any


class ASTMetrics:
    """Dataclass or dict wrapper to hold extracted code-level metrics."""

    def __init__(self):
        self.class_count = 0
        self.interface_count = 0
        self.abstract_count = 0
        self.private_members = 0
        self.protected_members = 0
        self.public_members = 0
        self.inheritance_count = 0
        self.polymorphism_count = 0
        self.total_lines = 0
        self.empty_or_comment_lines = 0
        self.total_functions = 0  # To compare procedural vs class-based

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "class_count": self.class_count,
            "interface_count": self.interface_count,
            "abstract_count": self.abstract_count,
            "private_members": self.private_members,
            "protected_members": self.protected_members,
            "public_members": self.public_members,
            "inheritance_count": self.inheritance_count,
            "polymorphism_count": self.polymorphism_count,
            "total_lines": self.total_lines,
            "total_functions": self.total_functions,
        }


def analyze_code_content(language: str, content: str) -> dict[str, Any]:
    """Analyze a single source code file using regex heuristics.

    Args:
        language: The normalized language name (e.g. 'Java', 'Python').
        content: The code file content as string.

    Returns:
        Dictionary of extracted metrics.
    """
    metrics = ASTMetrics()
    if not content:
        return metrics.to_dict()

    lines = content.splitlines()
    metrics.total_lines = len(lines)

    # Pre-clean comments to avoid false-positives in regex matching
    # Strip block comments and line comments where appropriate
    content_no_comments = _strip_comments(language, content)

    # Perform analysis based on language rules
    lang_lower = language.lower()
    if lang_lower == "python":
        _analyze_python(content_no_comments, metrics)
    elif lang_lower in ("java", "c#", "csharp", "kotlin"):
        _analyze_jvm_dotnet(content_no_comments, metrics)
    elif lang_lower in ("javascript", "typescript"):
        _analyze_javascript(content_no_comments, metrics)
    elif lang_lower in ("c++", "cpp"):
        _analyze_cpp(content_no_comments, metrics)
    elif lang_lower == "ruby":
        _analyze_ruby(content_no_comments, metrics)
    else:
        _analyze_generic(content_no_comments, metrics)

    return metrics.to_dict()


def _strip_comments(language: str, content: str) -> str:
    """Strip comment blocks and lines to make parsing cleaner."""
    lang_lower = language.lower()
    if lang_lower == "python" or lang_lower == "ruby":
        # Strip # comment lines
        return re.sub(r"#.*", "", content)
    elif lang_lower in ("java", "c#", "csharp", "kotlin", "javascript", "typescript", "c++", "cpp"):
        # Strip block comments /* ... */ and line comments // ...
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        return re.sub(r"//.*", "", content)
    return content


def _analyze_python(content: str, metrics: ASTMetrics):
    """Extract metrics from Python source code."""
    # Find classes: class Foo or class Foo(Bar):
    classes = re.findall(r"\bclass\s+([a-zA-Z0-9_]+)(?:\s*\((.*?)\))?\s*:", content)
    metrics.class_count = len(classes)
    for _, bases in classes:
        if bases and "object" not in bases.lower():
            metrics.inheritance_count += 1

    # Find functions/methods
    funcs = re.findall(r"\bdef\s+([a-zA-Z0-9_]+)\s*\(", content)
    metrics.total_functions = len(funcs)

    # Python encapsulation heuristics: double/single underscore fields and methods
    # e.g., self.__private_var, self._protected_var
    # excluding magic methods like __init__
    privates = re.findall(r"\bself\.__[a-zA-Z0-9_]+(?<!__)\b", content)
    protecteds = re.findall(r"\bself\._[a-zA-Z0-9_]+\b", content)

    metrics.private_members = len(privates)
    metrics.protected_members = len(protecteds)

    # Check for abstract base class imports or definitions
    if "abc" in content.lower() or "abstractmethod" in content.lower():
        metrics.abstract_count = len(re.findall(r"@abstractmethod", content))


def _analyze_jvm_dotnet(content: str, metrics: ASTMetrics):
    """Extract metrics from Java, C#, or Kotlin source code."""
    # Class declaration
    classes = re.findall(r"\b(?:class|record)\s+([a-zA-Z0-9_]+)", content)
    metrics.class_count = len(classes)

    # Interface declaration
    interfaces = re.findall(r"\binterface\s+([a-zA-Z0-9_]+)", content)
    metrics.interface_count = len(interfaces)

    # Abstract declarations
    abstracts = re.findall(r"\babstract\s+(?:class)?\s*([a-zA-Z0-9_]+)", content)
    metrics.abstract_count = len(abstracts)

    # Inheritance indicators
    # Java/C#: class Foo extends Bar, class Foo implements Bar, class Foo : Bar
    extends = len(re.findall(r"\bextends\s+([a-zA-Z0-9_]+)", content))
    implements = len(re.findall(r"\bimplements\s+([a-zA-Z0-9_]+)", content))
    colon_inheritance = len(re.findall(r"\bclass\s+[a-zA-Z0-9_]+\s*:\s*[a-zA-Z0-9_]+", content))
    metrics.inheritance_count = extends + implements + colon_inheritance

    # Access modifiers
    metrics.private_members = len(re.findall(r"\bprivate\b", content))
    metrics.protected_members = len(re.findall(r"\bprotected\b", content))
    metrics.public_members = len(re.findall(r"\bpublic\b", content))

    # Polymorphism: Generics <T>, method overrides
    overrides = len(re.findall(r"\b@Override\b|\boverride\b", content))
    generics = len(re.findall(r"<[A-Z][a-zA-Z0-9_]*>", content))
    metrics.polymorphism_count = overrides + generics


def _analyze_javascript(content: str, metrics: ASTMetrics):
    """Extract metrics from JavaScript / TypeScript source code."""
    classes = re.findall(r"\bclass\s+([a-zA-Z0-9_]+)", content)
    metrics.class_count = len(classes)

    # In JS: class Foo extends Bar
    metrics.inheritance_count = len(re.findall(r"\bextends\s+([a-zA-Z0-9_]+)", content))

    # ES6 private fields (#field)
    metrics.private_members = len(re.findall(r"\b#[a-zA-Z0-9_]+\b", content))

    # Functions
    funcs = re.findall(r"\bfunction\s+[a-zA-Z0-9_]+|\bconst\s+[a-zA-Z0-9_]+\s*=\s*\([^)]*\)\s*=>", content)
    metrics.total_functions = len(funcs)


def _analyze_cpp(content: str, metrics: ASTMetrics):
    """Extract metrics from C++ source code."""
    classes = re.findall(r"\b(?:class|struct)\s+([a-zA-Z0-9_]+)", content)
    metrics.class_count = len(classes)

    # Class inheritance (e.g. class Foo : public Bar)
    metrics.inheritance_count = len(re.findall(r"\b(?:class|struct)\s+[a-zA-Z0-9_]+\s*:\s*(?:public|protected|private)\s+[a-zA-Z0-9_]+", content))

    # Access modifiers (C++ uses label sections like public:, private:)
    metrics.private_members = len(re.findall(r"\bprivate\s*:", content))
    metrics.protected_members = len(re.findall(r"\bprotected\s*:", content))
    metrics.public_members = len(re.findall(r"\bpublic\s*:", content))

    # Polymorphism: virtual functions, templates
    virtuals = len(re.findall(r"\bvirtual\b", content))
    templates = len(re.findall(r"\btemplate\s*<", content))
    metrics.polymorphism_count = virtuals + templates


def _analyze_ruby(content: str, metrics: ASTMetrics):
    """Extract metrics from Ruby source code."""
    classes = re.findall(r"\bclass\s+([A-Z][a-zA-Z0-9_]*)", content)
    metrics.class_count = len(classes)

    # In Ruby: class Foo < Bar
    metrics.inheritance_count = len(re.findall(r"\bclass\s+[A-Z][a-zA-Z0-9_]*\s*<\s*[A-Z][a-zA-Z0-9_]*", content))

    # Access levels
    metrics.private_members = len(re.findall(r"\bprivate\b", content))
    metrics.protected_members = len(re.findall(r"\bprotected\b", content))


def _analyze_generic(content: str, metrics: ASTMetrics):
    """Generic fallback analyzer if specific rules don't match."""
    metrics.class_count = len(re.findall(r"\bclass\b", content))
    metrics.private_members = len(re.findall(r"\bprivate\b", content))
    metrics.protected_members = len(re.findall(r"\bprotected\b", content))
