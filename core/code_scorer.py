"""Combines language-level static scores with AST-based code-level modifiers.

Calculates a modifier (0.7x to 1.1x) based on object-oriented programming density,
encapsulation usage, and inheritance usage in the actual repository files.
"""

from typing import Any


def calculate_code_modifier(language: str, file_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate the code-level modifier score for a language based on aggregated file metrics.

    Args:
        language: The normalized language name.
        file_metrics: List of metrics dictionaries for files of this language.

    Returns:
        Dictionary containing:
            - modifier: float (between 0.7 and 1.1)
            - reason: str (short explanation of the modifier adjustment)
            - metrics: dict (aggregated metrics summary)
    """
    if not file_metrics:
        return {
            "modifier": 1.0,
            "reason": "No source code files analyzed (using language base score)",
            "metrics": _empty_aggregate(),
        }

    # Aggregate metrics
    agg = _empty_aggregate()
    for m in file_metrics:
        agg["class_count"] += m.get("class_count", 0)
        agg["interface_count"] += m.get("interface_count", 0)
        agg["abstract_count"] += m.get("abstract_count", 0)
        agg["private_members"] += m.get("private_members", 0)
        agg["protected_members"] += m.get("protected_members", 0)
        agg["public_members"] += m.get("public_members", 0)
        agg["inheritance_count"] += m.get("inheritance_count", 0)
        agg["polymorphism_count"] += m.get("polymorphism_count", 0)
        agg["total_lines"] += m.get("total_lines", 0)
        agg["total_functions"] += m.get("total_functions", 0)

    total_files = len(file_metrics)
    lang_lower = language.lower()

    # Base values
    modifier = 1.0
    penalties = []
    boosts = []

    # CRITICAL CHECK 1: Class existence
    # If a supported OOP language is used, but there are zero classes in the analyzed files,
    # it is a strong indication of procedural/functional usage of a multi-paradigm language.
    if agg["class_count"] == 0:
        if lang_lower in ("python", "javascript", "ruby"):
            modifier = 0.70
            return {
                "modifier": modifier,
                "reason": "No class definitions found; procedural or functional paradigm is dominant (-30%)",
                "metrics": agg,
            }
        elif lang_lower in ("java", "c#", "csharp"):
            # Java/C# require classes for entry points, but if zero, something is strange (maybe only interfaces)
            if agg["interface_count"] > 0:
                modifier = 0.85
                penalties.append("Only interfaces defined, no concrete class implementations (-15%)")
            else:
                modifier = 0.70
                return {
                    "modifier": modifier,
                    "reason": "No class definitions or interfaces found (-30%)",
                    "metrics": agg,
                }

    # CHECK 2: Encapsulation usage
    # Look at private/protected member density compared to public members
    total_hidden = agg["private_members"] + agg["protected_members"]
    total_members = total_hidden + agg["public_members"]

    if total_members > 0:
        ratio = total_hidden / total_members
        if ratio > 0.4:
            # High encapsulation
            boosts.append("Strong encapsulation: high ratio of private/protected members (+5%)")
            modifier += 0.05
        elif ratio < 0.1 and lang_lower in ("java", "c#", "csharp", "c++"):
            # Low encapsulation in strict languages
            penalties.append("Weak encapsulation: low use of private/protected members (-5%)")
            modifier -= 0.05
    else:
        # Strict OOP languages should have access modifiers
        if lang_lower in ("java", "c#", "c++") and agg["class_count"] > 0:
            penalties.append("No encapsulation markers found in classes (-5%)")
            modifier -= 0.05

    # CHECK 3: Paradigm dilution (Python / JS / Ruby)
    # Compare classes vs procedural module-level functions
    if lang_lower in ("python", "javascript"):
        if agg["class_count"] > 0 and agg["total_functions"] > 0:
            oop_ratio = agg["class_count"] / (agg["class_count"] + agg["total_functions"])
            if oop_ratio < 0.15:
                penalties.append("Paradigm dilution: loose function definitions dominant (-10%)")
                modifier -= 0.10
            elif oop_ratio > 0.6:
                boosts.append("High class-to-function density; class-based design is dominant (+5%)")
                modifier += 0.05

    # CHECK 4: Advanced OOP features usage (Inheritance, Polymorphism, Abstraction)
    # If they use interface implementation, superclass extension, generics, or abstract classes
    has_inheritance = agg["inheritance_count"] > 0
    has_abstraction = (agg["interface_count"] > 0) or (agg["abstract_count"] > 0)
    has_polymorphism = agg["polymorphism_count"] > 0

    if has_inheritance and has_abstraction and has_polymorphism:
        boosts.append("Comprehensive OOP: uses interfaces, inheritance, and polymorphism (+5%)")
        modifier += 0.05
    elif not has_inheritance and agg["class_count"] > 2:
        penalties.append("Flat hierarchy: multiple classes without inheritance (-5%)")
        modifier -= 0.05

    # Clamp modifier to 0.70 - 1.10
    modifier = max(0.70, min(1.10, modifier))
    modifier = round(modifier, 2)

    # Build justification string
    if modifier > 1.0:
        reason = ", ".join(boosts)
    elif modifier < 1.0:
        reason = ", ".join(penalties) if penalties else "Procedural design detected"
    else:
        reason = "Standard OOP design patterns matched base language score"

    return {
        "modifier": modifier,
        "reason": reason,
        "metrics": agg,
    }


def _empty_aggregate() -> dict[str, int]:
    """Helper to return an empty metrics dict."""
    return {
        "class_count": 0,
        "interface_count": 0,
        "abstract_count": 0,
        "private_members": 0,
        "protected_members": 0,
        "public_members": 0,
        "inheritance_count": 0,
        "polymorphism_count": 0,
        "total_lines": 0,
        "total_functions": 0,
    }
