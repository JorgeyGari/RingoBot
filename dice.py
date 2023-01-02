import random


def invalid(dice) -> str or None:
    """Devuelve un mensaje de error si el dado es inválido, o None si es válido."""

    if 'd' not in dice:
        return "Necesito que me des un comando de dados válido. Por ejemplo, `2d6`, `1d20` o `4df`."

    number_of_dice = dice.split('d')[0]
    dice_type = dice.split('d')[1]

    if dice_type != 'f':
        if dice_type.isnumeric() is False:
            return "Necesito que me des un comando de dados válido. Por ejemplo, `2d6`, `1d20` o `4df`."
        if int(dice_type) < 2 or int(dice_type) > 9999:
            return "¿De dónde quieres que saque un dado así?"

    if number_of_dice.isnumeric() is False:
        return "Necesito que me des un comando de dados válido. Por ejemplo, `2d6`, `1d20` o `4df`."
    if int(number_of_dice) < 1:
        return "¿Entonces... no tiro ningún dado?"
    if int(number_of_dice) > 100:
        return "Oye, no tengo tantos dados."

    return None


def human_read(dice) -> str:
    """Devuelve una cadena de texto con el comando de dados en formato de lenguaje natural."""

    number_of_dice = 'un' if int(dice.split('d')[0]) == 1 else int(int(dice.split('d')[0]))
    dice_type = 'fate' if dice.split('d')[1] == 'f' else dice.split('d')[1] + ' caras'
    plural = '' if number_of_dice == 'un' else 's'
    if dice_type == 'fate':
        return f'{number_of_dice} dado{plural} de Fate'
    return f'{number_of_dice} dado{plural} de {dice_type}'


def roll_dice(dice) -> list:
    """Tira los dados y devuelve una lista con los resultados."""

    number_of_dice = int(dice.split('d')[0])
    if dice[-1] == 'f':
        fate_dice = ['-', '·', '+']
        return [random.choice(fate_dice) for _ in range(number_of_dice)]

    dice_type = int(dice.split('d')[1])
    return [random.randint(1, dice_type) for _ in range(number_of_dice)]


def total_roll(roll) -> int:
    """Devuelve la suma de los dados tirados."""

    fate_values = {'-': -1, '·': 0, '+': 1}
    return sum([fate_values[dice] if dice in fate_values else dice for dice in roll])
