# W70 application evidence

This directory contains the exact selected-hash plan, 300-cell readback, 12 catalog invariants, 140 carried-hold readbacks, prior-ID exclusion verification, preflight pin, and catalog commit record.

Run python3 application/verify_application.py from the repository root. It compares the pinned parent and catalog commit Git objects against every reviewed target, all selected updates, catalog structure, carried holds, and prior-ID exclusions.
