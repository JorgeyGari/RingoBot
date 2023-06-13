def Zone() -> None:
    """
    Representa una zona en la sala de huida.
    Una zona puede ser un lugar físico o una parte de él.
    """
    def __init__(self, name: str, description: str, subzones: list[Zone] = [], new: dict = {Item}) -> None:
        """
        Crea una nueva zona.
        :param name: Nombre de la zona.
        :param description: Descripción de la zona.
        :param subzones: Otras zonas accesibles desde esta.
        :param new: Objetos o nuevas zonas que se pueden obtener en esta zona.
        """
        self.name = name
        self.description = description
        self.subzones = subzones or []
        self.new = new or []
    
    def __str__(self) -> str:
        """
        Devuelve una representación de la zona.
        Esta es la que se muestra al usuario.
        """
        subzones = f">**{self.name}**\n>{self.description}"
        subzones = "\n\n".join([f"*>>{zone.name}*" for zone in self.subzones])
        return subzones
    
    def _unlock(self, item: Item) -> list[Item]:
        """
        Desbloquea las zonas y los objetos bloqueadas por un objeto.
        Las zonas son añadidas a la lista de subzonas, mientras que los objetos a añadir al inventario se devuelven en forma de lista.
        :param item: Objeto que se ha equipado.
        :return: Lista de objetos desbloqueados.
        """
        if item not in self.new:
            return []
        unlocked_items = []
        for unlockable in self.new[item]:
            if isinstance(unlockable, Zone):
                self.subzones.append(unlockable)
            elif isinstance(unlockable, Item):
                unlocked_items.append(unlockable)
        self.new.pop(item)  # Este objeto ya no desbloquea nada, así que se elimina
        return unlocked_items

    def react(self, item: Item) -> str:
        """
        Mensaje de reacción al inspeccionar la zona con un objeto opcional.
        :param item: Objeto equipado.
        :return: Mensaje de reacción.
        """
        if item in self.new:
            self._unlock(item)
            return self.new[item][0]    # Mensaje de reacción
        return "Nada interesante."

def Item() -> None:
    """Representa un objeto que se puede equipar y que se almacena en el inventario."""
    def __init__(self, name: str, description: str, combine: dict = {}) -> None:
        """
        Crea un nuevo objeto.
        :param name: Nombre del objeto.
        :param description: Descripción del objeto.
        :param combine: Objetos con los que se puede combinar.
        """
        self.name = name
        self.description = description
        self.combine = combine or {}
    
    def __str__(self) -> str:
        """
        Devuelve una representación del objeto.
        Esta es la que se muestra al usuario.
        """
        return f">**{self.name}**\n>{self.description}"
    
    def _combine(self, item: Item) -> tuple[Item, list[Item]]:
        """
        Combina dos objetos.
        :param item: Objeto con el que se combina este.
        :return: Nuevo objeto para añadir al inventario y lista de los dos objetos que se deben eliminar de él.
        """
        if item not in self.combine:
            if self in item.combine:
                return item._combine(self)  # Se invierte el orden para que la combinación sea conmutativa
            return None, []
        new_item = self.combine[item]
        removed_items = [self, item]
        return new_item, removed_items
    
    def react(self, item: Item) -> str:
        """
        Mensaje de reacción al inspeccionar el objeto con otro objeto opcional.
        :param item: Objeto equipado.
        :return: Mensaje de reacción.
        """
        if item in self.combine:
            new_item, removed_items = self._combine(item)
            if new_item is None:
                return "No pasa nada."
            return f"Has creado **{new_item.name}**."
        return "No pasa nada."
