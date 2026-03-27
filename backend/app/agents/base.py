from abc import ABC, abstractmethod


class BaseAgent(ABC):
    name: str
    description: str
    parameters: dict

    @abstractmethod
    async def run(self, **kwargs) -> str:
        pass

    def to_tool_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
