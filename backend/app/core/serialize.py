def pick(obj, *fields: str) -> dict:
    """Explicit field allow-list serialisation: nothing leaks unless named here."""
    return {f: getattr(obj, f) for f in fields}
