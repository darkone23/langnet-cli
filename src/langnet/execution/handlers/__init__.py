"""Execution handler package.

Handlers are imported by the registry or by callers that need a specific tool.
Keep this package import cheap; some handler modules initialize heavy optional
dependencies.
"""
