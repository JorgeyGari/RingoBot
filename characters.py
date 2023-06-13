class Trainer:
    def __init__(self, name):
        self.name = name
        self.abilities = {}
        self.fate_points = 3

    def add_ability(self, ability: str, modifier: int):
        """Añade una habilidad al entrenador con el modificador indicado."""
        self.abilities[ability] = modifier


class Pokemon:
    def __init__(self, name):
        self.name = name
        self.moves = {}
        self.physical_stress = 0
        self.mental_stress = 0
        self.max_mental_stress = 2
        self.max_physical_stress = 2
        self.consequences = {}

    def add_move(self, move: str, modifier: int):
        """Añade un movimiento al Pokémon con el modificador indicado."""
        self.moves[move] = modifier

    def add_consequence(self, consequence: str, modifier: int):
        """Añade una consecuencia al Pokémon con el modificador indicado."""
        self.consequences[consequence] = modifier
