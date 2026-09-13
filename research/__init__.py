"""Offline research utilities for V3.5 runner reverse engineering.

Nothing under this package is imported by the live scanner. Research code must
remain replay-safe: features at timestamp T may only use data available at or
before T.
"""
