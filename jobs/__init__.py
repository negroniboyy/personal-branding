# Importing the package registers every job handler exactly once, so any
# `from jobs import queue` / `import jobs.routes` elsewhere is enough to make
# job kinds available — callers never need to import handlers.py directly.
from . import handlers  # noqa: F401
