# emergent/agents/builder/models.py
# Modèle de base pour les agents IA Blaxing (usage côté Flask utilities)

class BlaxingAgent:
    def __init__(self, name, role, personality, mission, api_key=None, active=True, use_openai=False):
        self.name = name
        self.role = role
        self.personality = personality
        self.mission = mission
        self._api_key = api_key  # Stockage privé pour sécurité
        self.active = active
        self.use_openai = use_openai

    def to_dict(self, include_sensitive=False):
        """
        Retourne un dictionnaire de l'agent.
        Attention: include_sensitive=True ne doit être utilisé qu'en interne.
        """
        data = {
            "name": self.name,
            "role": self.role,
            "personality": self.personality,
            "mission": self.mission,
            "active": self.active,
            "use_openai": self.use_openai,
        }
        if include_sensitive:
            data["api_key"] = self._api_key
        return data

    @property
    def api_key(self):
        return self._api_key