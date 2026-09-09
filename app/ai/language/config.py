"""
Centralized Language Feature Flag & Configuration Subsystem for GoRush.

Controls launch vs Phase 2 vs unsupported regional languages centrally.
"""

from typing import Any, Dict
from app.common.enums.chat import Language

# Central Language Configuration map as required by BRD
_DEFAULT_LANGUAGE_CONFIG: Dict[str, Dict[str, Any]] = {
    "en": {
        "enabled": True,
        "status": "launch",
        "name": "English",
    },
    "hi": {
        "enabled": True,
        "status": "launch",
        "name": "Hindi",
    },
    "hi-en": {
        "enabled": True,
        "status": "launch",
        "name": "Hinglish",
    },
    "mixed": {
        "enabled": True,
        "status": "launch",
        "name": "Mixed",
    },
    "mr": {
        "enabled": True,
        "status": "phase2",
        "name": "Marathi",
    },
    "gu": {
        "enabled": True,
        "status": "phase2",
        "name": "Gujarati",
    },
    "bn": {
        "enabled": True,
        "status": "phase2",
        "name": "Bengali",
    },
    "ta": {
        "enabled": True,
        "status": "phase2",
        "name": "Tamil",
    },
    "te": {
        "enabled": True,
        "status": "phase2",
        "name": "Telugu",
    },
    "kn": {
        "enabled": True,
        "status": "phase2",
        "name": "Kannada",
    },
    "ml": {
        "enabled": True,
        "status": "phase2",
        "name": "Malayalam",
    },
    "pa": {
        "enabled": True,
        "status": "phase2",
        "name": "Punjabi",
    },
    "or": {
        "enabled": True,
        "status": "phase2",
        "name": "Odia",
    },
    "as": {
        "enabled": True,
        "status": "phase2",
        "name": "Assamese",
    },
    "ur": {
        "enabled": True,
        "status": "phase2",
        "name": "Urdu",
    },
    "raj": {
        "enabled": True,
        "status": "launch",
        "name": "Rajasthani",
    },
    "unknown": {
        "enabled": False,
        "status": "unsupported",
        "name": "Unknown",
    },
}

# Mutable configuration at runtime
LANGUAGE_CONFIG: Dict[str, Dict[str, Any]] = {
    code: dict(cfg) for code, cfg in _DEFAULT_LANGUAGE_CONFIG.items()
}


def get_language_config(lang: str | Language) -> Dict[str, Any]:
    """Retrieve central configuration dict for a language."""
    enum_val = Language.normalize(lang)
    code = enum_val.value
    if code in LANGUAGE_CONFIG:
        return LANGUAGE_CONFIG[code]
    return {
        "enabled": False,
        "status": "unsupported",
        "name": str(lang),
    }


def is_language_enabled(lang: str | Language) -> bool:
    """Return whether the specified language is currently enabled."""
    cfg = get_language_config(lang)
    return bool(cfg.get("enabled", False))


def is_phase2_language(lang: str | Language) -> bool:
    """Return True if language belongs to Phase 2 roadmap."""
    cfg = get_language_config(lang)
    return cfg.get("status") == "phase2"


def set_language_enabled(lang: str | Language, enabled: bool) -> None:
    """Toggle language feature flag dynamically."""
    enum_val = Language.normalize(lang)
    code = enum_val.value
    if code in LANGUAGE_CONFIG:
        LANGUAGE_CONFIG[code]["enabled"] = enabled
    else:
        LANGUAGE_CONFIG[code] = {
            "enabled": enabled,
            "status": "phase2" if enabled else "unsupported",
            "name": code.upper(),
        }


def reset_language_config() -> None:
    """Reset configuration to default launch settings."""
    global LANGUAGE_CONFIG
    LANGUAGE_CONFIG = {
        code: dict(cfg) for code, cfg in _DEFAULT_LANGUAGE_CONFIG.items()
    }
