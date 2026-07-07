"""Compiler error types."""


class CompileError(RuntimeError):
    """Raised when wiz-checker reports errors > 0 against the compiler's output.

    This indicates a bug in the compiler itself (the produced speech*.json failed
    structural/logical validation). Distinct from plain RuntimeError, which is
    reserved for unexpected internal failures (e.g. checker crash, malformed JSON).
    """
