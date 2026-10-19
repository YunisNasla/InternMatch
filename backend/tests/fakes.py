from types import SimpleNamespace


class FakeClaude:
    """Answers like Claude would, from a function of (system, user, call number). Records every call."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        text = self.answer(kw["system"], kw["messages"][-1]["content"], len(self.calls))
        if isinstance(text, Exception):
            raise text
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)], usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )


def tag_as_software(system, user, n):
    """Tagger answers for pipeline tests: every posting is software, every company is space."""
    if "assign a company to one industry" in system:
        return '{"industry": "space", "confidence": "high"}'
    return '{"role_type": "software", "work_arrangement": "not_stated"}'
