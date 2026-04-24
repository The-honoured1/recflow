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
        self.popularity_boost_weight = 2.0
        self.repetition_penalty_decay = 0.8  # Deduct 20% score for every past interaction
        
    def add_event_weight(self, event_type: str, weight: float):
        self.event_weights[event_type] = weight
        
    def set_recency_decay(self, half_life_days: float):
        if half_life_days <= 0:
            raise ValueError("Half life must be > 0 days")
        self.recency_half_life_days = half_life_days
        
    def add_metadata_boost(self, key: str, value: str, multiplier: float):
        self.property_boosts.append({"key": key, "value": value, "multiplier": multiplier})

    def set_popularity_weight(self, weight: float):
        self.popularity_boost_weight = weight
        
    def set_repetition_penalty(self, decay_factor: float):
        self.repetition_penalty_decay = decay_factor

    def to_dict(self):
        return {
            "event_weights": self.event_weights,
            "recency_half_life_days": self.recency_half_life_days,
            "property_boosts": self.property_boosts,
            "popularity_boost_weight": self.popularity_boost_weight,
            "repetition_penalty_decay": self.repetition_penalty_decay
        }
        
    def from_dict(self, data: dict):
        if "event_weights" in data:
            self.event_weights = data["event_weights"]
        if "recency_half_life_days" in data:
            self.set_recency_decay(float(data["recency_half_life_days"]))
        if "property_boosts" in data:
            self.property_boosts = data["property_boosts"]
        if "popularity_boost_weight" in data:
             self.popularity_boost_weight = float(data["popularity_boost_weight"])
        if "repetition_penalty_decay" in data:
             self.repetition_penalty_decay = float(data["repetition_penalty_decay"])
