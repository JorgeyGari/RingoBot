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

    else:
        return None
