def info() -> list:
    """Devuelve una lista cuyo primer elemento son los puntos disponibles. El resto de elementos son los objetos que
    se pueden comprar junto a su precio."""
    with open('tienda.txt', 'r', encoding='utf-8') as f:
        item_list = f.read().splitlines()
    return item_list


def inventory() -> str:
    """Lee el archivo de texto con el inventario de la tienda y lo devuelve como mensaje."""

    item_list = info()
    money = item_list.pop(0)

    message = '**TIENDA**\n-----------------------------\n'

    for i in item_list:
        message += f"**{i.split(',')[0]}**: {i.split(',')[1]} PD\n"

    message += f"\n**Puntos restantes**: {money} PD"
    return message


def buy(item: str) -> str:
    """Comprueba si el usuario puede comprar el objeto indicado y lo devuelve como mensaje."""

    item_list = info()
    money = int(item_list.pop(0))

    for i in item_list:
        if i.split(',')[0] == item:
            price = int(i.split(',')[1])
            if money >= price:
                item_list.remove(i)
                item_list.insert(0, str(money - price))
                with open('tienda.txt', 'w', encoding='utf-8') as f:
                    f.seek(0, 0)
                    f.close()
                with open('tienda.txt', 'w', encoding='utf-8') as f:
                    for j in item_list:
                        f.write(f"{j}\n")

                return f"Habéis comprado **{i.split(',')[0]}** por **{price} PD**."
            else:
                return f"No tenéis suficientes puntos para comprar **{i.split(',')[0]}**."

    return "Ese objeto no está en la tienda."
