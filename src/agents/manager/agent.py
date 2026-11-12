from typing import List, Optional, Callable
from src.a2a.client import A2ACardResolver
from src.a2a.types import (
    AgentCard
)
from src.agents.agent import BaseAgent
from src.aci.factory import ACI
from src.utils.log import get_logger
from .prompt import SYSTEM_PROMPT
from typing import override
from typing import List
import logging
import importlib
from src.tools.api import API_TOOL_CALLS
from src.utils.config import CONFIG

BuilderAgent = importlib.import_module("src.agents.builder.agent").BuilderAgent
HarnessAgent = importlib.import_module("src.agents.harness-generator.agent").HarnessAgent
FuzzerAgent = importlib.import_module("src.agents.fuzzer.agent").FuzzerAgent
CrashAnalyzerAgent = importlib.import_module("src.agents.crash-analyzer.agent").CrashAnalyzerAgent
DictionaryGeneratorAgent = importlib.import_module("src.agents.dict-generator.agent").DictionaryGeneratorAgent
SeedGeneratorAgent = importlib.import_module("src.agents.seed-generator.agent").SeedGeneratorAgent
CoverageAnalyzerAgent = importlib.import_module("src.agents.cov-analyzer.agent").CoverageAnalyzerAgent

class ManagerAgent(BaseAgent):
    logger = get_logger("Manager Agent")
    tools: List[dict] = API_TOOL_CALLS.get_tool_calls(
        [
            "open",
            "goto",
            "scroll_up",
            "scroll_down",
            "check_status",
            "bash",
            "send_agent_task"
        ]
    )
    MAX_TOOL_CALL_TIMES = 10
    MAX_EPOCH = 100

    @staticmethod
    def _normalize_name(name: str) -> str:
        return name.lower().replace(" ", "").replace("_", "").replace("-", "")

    def __init__(self, agent_addresses: List[str]):
        super().__init__()
        self.logger.log(level=logging.INFO, msg="Manager Agent Initialized.")
        self.cards: dict[str, AgentCard] = self.resolve_agent_cards(agent_addresses)
        self.agents = self.list_agents()
        builder = BuilderAgent()
        harness = HarnessAgent()
        fuzzer = FuzzerAgent()
        crash_analyzer = CrashAnalyzerAgent()
        dict_gen = DictionaryGeneratorAgent()
        seed_gen = SeedGeneratorAgent()
        cov_analyzer = CoverageAnalyzerAgent()

        self.class_map = {
            "Builder Agent": builder,
            "Harness Generator Agent": harness,
            "Fuzzer Agent": fuzzer,
            "Crash Analyzer Agent": crash_analyzer,
            "Dictionary Generator Agent": dict_gen,
            "Seed Generator Agent": seed_gen,
            "Coverage Analyzer Agent": cov_analyzer,
        }
            
        self.prompt_factory = ACI(
             agents=self.agents,
        )

    def resolve_agent_cards(self, agent_addresses: List[str]) -> dict[str, AgentCard]:
        """Resolve agent cards from the given addresses."""
        cards = {}
        for address in agent_addresses:
            card_resolver = A2ACardResolver(address)
            card = card_resolver.get_agent_card()
            cards[card.name] = card
        return cards

    def list_agent_names(self) -> List[str]:
        """List the names of the available agents."""
        return list(self.cards.keys())

    def list_agents(self) -> List[AgentCard]:
        """List the names of the available agents."""
        return list(self.cards.values())

    @override
    def format_system_prompt(self) -> str:
        return SYSTEM_PROMPT + self.prompt_factory.create_available_agents_prompt()

    @override
    def register_agent_pre_call(self):
        command = "check_status"
        observation = self.aci.run_command_with_timeout(command, timeout=120, max_output_lines=200)
        message = f"This is the current states of the fuzzing tasks:\n{observation}"
        self.history_processor.extend_user_msg(content=message)

    @override
    def handle_agent_action(self, tool_args: dict) -> str:
        agent_name = tool_args.get("agent_name")
        if not agent_name:
            raise ValueError("You must specify the agent name to send the task to.")
        task_description = tool_args.get("task_description")
        if not task_description:
            raise ValueError("You must specify the task description to send to the agent.")
        
        agent = self.class_map.get(agent_name)
        if not agent:
            norm_target = self._normalize_name(agent_name)
            for k, v in self.class_map.items():
                if self._normalize_name(k) == norm_target:
                    agent = v
                    break
        if not agent:
            raise ValueError("The agent name: {} is not valid. The available agents are {}".format(agent_name, self.list_agent_names()))
        
        self.logger.info(msg=f"Sending agent task: {agent_name}\nTask description: {task_description}")
        observation = agent.run(task_description)
        command = "check_status"
        new_observation = self.aci.run_command_with_timeout(command, timeout=120, max_output_lines=200)
        message = f"This is the current states of the fuzzing tasks after the agent {agent_name} has completed its task:\n{new_observation}"
        return observation + "\n" + message