import random


def handle_response(message) -> str or None:
    p_message = message.lower()

    if p_message.startswith('hola'):
        return '¡Hola!'

    if p_message.startswith('!ayuda'):
        return '¡Hola! Soy RingoBot. Encantade de conocerte.\n\n' \
               'Conozco los siguientes comandos:\n' \
               '**!insulta** - ¡Insulta a alguien!\n' \
               '**!ayuda** - ¡Muestra esta ayuda!\n' \
               'Si te da vergüenza, también puedo escribirte al privado si añades `$` antes de `!`' \
               '(por ejemplo: `$!ayuda`).\n' \
               '\nAdemás, tengo otros comandos más avanzados que puedes consultar con `/`.'

    if p_message.endswith('5') or p_message.endswith('cinco'):
        if random.randint(1, 6) == 5:
            return 'Por el culo te la hinco.'

    if p_message.startswith('!insulta'):
        user = message.split(" ")[1:]
        if user:
            if user == "<@527911869550428168>":
                return 'Te quiero, <@527911869550428168> <3'
            else:
                ans = ' '
                for i in user:
                    ans = ans + ' ' + i
                return ans + ", gilipollas de mierda."

    if p_message.endswith('tu puta madre'):
        return 'La tuya, que es más capulla.'

    if p_message.startswith('buenas noches'):
        return '¡Buenas noches!'

    if 'ringobot' in p_message:
        return '¿Qué? ¿Me has llamado?'

    if 'me mato' in p_message \
        or 'me suicido' in p_message \
        or 'quiero morir' in p_message \
        or 'quiero matarme' in p_message \
        or 'me voy a matar' in p_message \
        or 'me voy a suicidar' in p_message \
        or 'suicidarme' in p_message \
        or 'me mataré' in p_message \
        or 'me quiero matar' in p_message:
        return '**Teléfono de prevención del suicidio: 024**'

    else:
        return None
