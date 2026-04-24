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
        
    def add_event_weight(self, event_type: str, weight: float):
        """Map generic event types to exact scores dynamically."""
        self.event_weights[event_type] = weight
        
    def set_recency_decay(self, half_life_days: float):
        """Determine how quickly old user interests decay."""
        if half_life_days <= 0:
            raise ValueError("Half life must be > 0 days")
        self.recency_half_life_days = half_life_days
        
    def add_metadata_boost(self, key: str, value: str, multiplier: float):
        self.property_boosts.append({"key": key, "value": value, "multiplier": multiplier})

    def to_dict(self):
        return {
            "event_weights": self.event_weights,
            "recency_half_life_days": self.recency_half_life_days,
            "property_boosts": self.property_boosts
        }
        
    def from_dict(self, data: dict):
        if "event_weights" in data:
            self.event_weights = data["event_weights"]
        if "recency_half_life_days" in data:
            self.set_recency_decay(float(data["recency_half_life_days"]))
        if "property_boosts" in data:
            self.property_boosts = data["property_boosts"]
