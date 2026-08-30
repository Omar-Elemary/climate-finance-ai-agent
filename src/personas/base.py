from dataclasses import dataclass, field


@dataclass
class Persona:
    name: str
    description: str = ""
    system_prompt: str = ""
    tone: str = ""
    focus_areas: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        parts = []
        if self.name:
            parts.append(f"You are: {self.name}")
        if self.description:
            parts.append(f"Background: {self.description}")
        if self.system_prompt:
            parts.append(f"Instructions: {self.system_prompt}")
        if self.tone:
            parts.append(f"Communication style: {self.tone}")
        if self.focus_areas:
            parts.append(f"Focus areas: {', '.join(self.focus_areas)}")
        return "\n".join(parts)

    def __repr__(self) -> str:
        return f"Persona(name='{self.name}')"
