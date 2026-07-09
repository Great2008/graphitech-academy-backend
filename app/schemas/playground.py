"""
app/schemas/playground.py
"""

from typing import Optional

from pydantic import BaseModel, Field


class PlaygroundRunRequest(BaseModel):
    language: str = Field(..., description="e.g. 'python', 'javascript', 'java', 'c', 'cpp'")
    source_code: str
    stdin: Optional[str] = None


class PlaygroundRunResponse(BaseModel):
    status: str  # e.g. "Accepted", "Wrong Answer", "Compilation Error", "Runtime Error", "Time Limit Exceeded"
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    time_seconds: Optional[float] = None
    memory_kb: Optional[int] = None
