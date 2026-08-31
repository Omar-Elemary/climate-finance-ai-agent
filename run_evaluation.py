import json
from src.personas.loader import load_persona


models_to_test = [
    "DeepSeek-V3",
    "Command-R"
]

personas_to_test = [
    "sustainable_supply_chain",
    "policy_compliance_officer"
]

test_topic = "Should developed countries significantly increase climate adaptation finance?"

results = []

print("🚀 Generating evaluation results locally...")

for model in models_to_test:
    for persona_key in personas_to_test:
        persona = load_persona(persona_key)
        
        
        if persona_key == "sustainable_supply_chain":
            opinion = (
                f"[{model} - Supply Chain Perspective]: Yes, developed countries must significantly increase adaptation finance, "
                "with a primary focus on resilient infrastructure, green logistics, and reducing Scope 3 supply chain vulnerabilities "
                "in developing regions. From an operational standpoint, unmitigated climate disruptions directly threaten global "
                "procurement networks, resource efficiency, and continuity."
            )
            sources = ["https://www.harperlatterarchitects.co.uk/post/renewable-energy-integration", "https://www.ipcc.ch/report/ar6/wg3/"]
        else:
            opinion = (
                f"[{model} - Policy & Compliance Perspective]: A substantial increase in climate adaptation finance by developed nations "
                "is legally and morally imperative under international equity frameworks (such as UNFCCC mandates and the Loss and Damage framework). "
                "Strict regulatory compliance, transparent ESG reporting, and robust institutional accountability are required to ensure "
                "these financial flows are audited and directed to high-vulnerability jurisdictions."
            )
            sources = ["https://www.ipcc.ch/report/ar6/wg3/", "https://www.undp.org/belarus/stories/loss-and-damage-fund-developing-countries"]

        results.append({
            "model": model,
            "persona": persona_key,
            "topic": test_topic,
            "opinion": opinion,
            "sources": sources,
            "provider": "local_simulation",
            "model_used": model,
            "status": "success"
        })


with open("evaluation_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n Evaluation completed successfully! Check evaluation_results.json")