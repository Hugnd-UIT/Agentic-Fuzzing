from pydantic import BaseModel, Field, field_validator
from typing import Tuple, Any
import os, sys
from pathlib import Path
import yaml

_REQUIRED_ENV_VARS = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"]
_MISSING = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
if _MISSING:
    print(f"Required environment variables not set: {', '.join(_MISSING)}", file=sys.stderr)
    sys.exit(-1)

_script_path = os.path.realpath(__file__)

_script_dir = os.path.dirname(_script_path)

def _optional_llm_timeout() -> int | None:
    raw = os.environ.get("LLM_TIMEOUT", "600").strip().lower()
    return None if raw in {"none", "unlimited"} else int(raw)

def _normalize_llm_base(url: str) -> str:
    if os.path.exists("/.dockerenv") or os.environ.get("CONTAINER_NAME"):
        return url.replace("://localhost:", "://host.docker.internal:").replace("://127.0.0.1:", "://host.docker.internal:")
    return url

class ACIVariables(BaseModel):
    CURRENT_FILE: str = ""
    CURRENT_LINE: int = 0
    OVERLAP: int = 2
    WINDOW: int = 100
    CMD_OUTPUT_LINES: int = 100
    MAX_OUTPUT_CHARACTERS: int = 100000 # 10k tokens * 10 characters per token
    WHITELIST_CMD_TIMEOUT: int = 5400

    def __getitem__(self, key):
        return getattr(self, key)

class LLMArgs(BaseModel):
    OPENAI_API_BASE: str = _normalize_llm_base(os.environ["OPENAI_BASE_URL"])
    OPENAI_MODEL: str = os.environ["OPENAI_MODEL"]
    LLM_TIMEOUT: int | None = _optional_llm_timeout()
    LLM_TEMPERATURE: float = float(os.environ.get("LLM_TEMPERATURE", 0.6))
    MAX_EPOCH: int = int(os.environ.get("MAX_EPOCH", 100))
    LLM_TOP_P: float = float(os.environ.get("LLM_TOP_P", 0.9))
    LLM_TOP_K: int = int(os.environ.get("LLM_TOP_K", 20))
    REMINDER_TOKEN_RATIO: float = float(os.environ.get("REMINDER_TOKEN_RATIO", 0.8))
    MAX_TOKEN_LEN: int = int(os.environ.get("MAX_TOKEN_LEN", 128000))
    def __getitem__(self, key):
        return getattr(self, key)

class Config(BaseModel):
    docker: bool = Field(..., alias="docker")

    @field_validator("docker", mode="before")
    def convert_docker_flag(cls, v):
        return bool(int(v))

    ACIARGs: ACIVariables = Field(..., alias="aci_variables")
    LLMARGs: LLMArgs = Field(default_factory=LLMArgs, alias="llm_args")

    def get_aci_variables(self) -> dict[str, Any]:
        return self.ACIARGs.model_dump()

if os.environ.get("CONFIG_FILE"):
    CONFIG_FILE = os.environ["CONFIG_FILE"]
else:
    CONFIG_FILE = os.path.join(Path(_script_dir).parent.parent, "config.yaml")

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as file:
        yaml_data = yaml.safe_load(file)
    CONFIG = Config(**yaml_data)
else:
    print(f"Configuration file not found: {CONFIG_FILE}", file=sys.stderr)
    sys.exit(-1)

CMD_TIMEOUT_WHITELIST = ["build_target", "run_fuzzer"]
WHITELIST_CMD_TIMEOUT = CONFIG.ACIARGs.WHITELIST_CMD_TIMEOUT

def get_agent_addresses():
    addresses = []
    agents_map = [
        ("Builder Agent", ["builder"]),
        ("Dictionary Generator Agent", ["dict-generator"]),
        ("Seed Generator Agent", ["seed-generator"]),
        ("Harness Generator Agent", ["harness-generator"]),
        ("Fuzzer Agent", ["fuzzer"]),
        ("Crash Analyzer Agent", ["crash-analyzer"]),
        ("Coverage Analyzer Agent", ["cov-analyzer"]),
    ]
    spec_location = ".well-know/agent.json"
    SRC_AGENT_PATH = os.path.join(Path(_script_dir).parent, "agents")
    for canonical_name, candidates in agents_map:
        found = False
        for agent in candidates:
            address = os.path.join(SRC_AGENT_PATH, agent, spec_location)
            if os.path.exists(address):
                addresses.append(address)
                found = True
                break
        if not found:
            raise Exception(f"agent.json not found for {canonical_name} in {candidates}!")
    return addresses