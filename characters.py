class Trainer:
    def __init__(self, name):
        self.name = name
        self.abilities = {}
        self.fate_points = 3

    def add_ability(self, ability: str, modifier: int):
        """Añade una habilidad al entrenador con el modificador indicado."""
        self.abilities[ability] = modifier

