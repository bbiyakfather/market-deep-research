"""Stable Vega-Lite spec emitter.

The TypeScript reference serializes specs with ``JSON.stringify(spec, null, 2)``;
that means dict iteration order corresponds to JS object insertion order. Python's
``dict`` is insertion-ordered too, so as long as Python code adds keys in the same
order the TS does, the output will match. The pytest harness uses a structural
diff so key *order* in the actual spec is irrelevant — only the key set and values
matter.
"""
