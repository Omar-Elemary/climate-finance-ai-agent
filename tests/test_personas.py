from src.personas.base import Persona
from src.personas.loader import load_persona, list_personas


def test_persona_creation():
    p = Persona(name="Test", description="A test persona")
    assert p.name == "Test"
    assert p.focus_areas == []


def test_persona_to_prompt_context():
    p = Persona(
        name="Investor",
        description="Climate finance investor",
        system_prompt="Focus on ROI",
        tone="analytical",
        focus_areas=["ROI", "risk"],
    )
    ctx = p.to_prompt_context()
    assert "Investor" in ctx
    assert "Climate finance investor" in ctx
    assert "Focus on ROI" in ctx
    assert "analytical" in ctx
    assert "ROI" in ctx
    assert "risk" in ctx


def test_list_personas():
    personas = list_personas()
    assert isinstance(personas, list)
    assert "investor" in personas
    assert "policy_expert" in personas
    assert "scientist" in personas


def test_load_persona():
    p = load_persona("investor")
    assert p.name == "Climate Investor"
    assert len(p.focus_areas) > 0


def test_load_persona_not_found():
    try:
        load_persona("nonexistent_persona_xyz")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_load_all_personas():
    from src.personas.loader import load_personas
    personas = load_personas()
    assert len(personas) >= 3
    names = [p.name for p in personas]
    assert "Climate Investor" in names
    assert "Policy Expert" in names
    assert "Environmental Scientist" in names
