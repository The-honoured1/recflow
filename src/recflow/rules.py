class RulesEngine:
    def __init__(self):
        self.event_weights = {
            "view": 1.0,
            "click": 2.0,
            "add_to_cart": 5.0,
            "purchase": 10.0
        }
        self.recency_half_life_days = 30.0
        self.property_boosts = []
        self.active_algorithm = "sql_cooccurrence"
        
    def add_event_weight(self, event_type: str, weight: float):
        self.event_weights[event_type] = weight
        
    def set_recency_decay(self, half_life_days: float):
        if half_life_days <= 0:
            raise ValueError("Half life must be > 0 days")
        self.recency_half_life_days = half_life_days
        
    def add_metadata_boost(self, key: str, value: str, multiplier: float):
        self.property_boosts.append({"key": key, "value": value, "multiplier": multiplier})

    def set_algorithm(self, algo_name: str):
        self.active_algorithm = algo_name

    def to_dict(self):
        return {
            "active_algorithm": self.active_algorithm,
            "event_weights": self.event_weights,
            "recency_half_life_days": self.recency_half_life_days,
            "property_boosts": self.property_boosts
        }
        
    def from_dict(self, data: dict):
        if "active_algorithm" in data:
            self.active_algorithm = data["active_algorithm"]
        if "event_weights" in data:
            self.event_weights = data["event_weights"]
        if "recency_half_life_days" in data:
            self.set_recency_decay(float(data["recency_half_life_days"]))
        if "property_boosts" in data:
            self.property_boosts = data["property_boosts"]
