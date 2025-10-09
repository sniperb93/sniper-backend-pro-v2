# emergent/agents/builder/models.py
# Modèle de base pour les agents IA Blaxing (usage côté Flask utilities)

class BlaxingAgent:
    def __init__(self, name, role, personality, mission, api_key=None, active=True, use_openai=False):
        self.name = name
        self.role = role
        self.personality = personality
        self.mission = mission
        self.api_key = api_key
        self.active = active
        self.use_openai = use_openai

    def to_dict(self):
        return {
            "name": self.name,
            "role": self.role,
            "personality": self.personality,
            "mission": self.mission,
            "api_key": self.api_key,
            "active": self.active,
            "use_openai": self.use_openai,
        }