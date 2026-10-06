"""Black-box health evals for the running StyleIQ API.

Unlike tests/ (pass/fail on code behaviour), these produce scores for a live
deployment: is it up, is it fast, and are its search results still relevant.
Run with: python -m evals.run
"""
