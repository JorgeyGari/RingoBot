"""
Replies module for handling automatic message responses.
"""

import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RepliesModule:
    """Handles automatic replies to user messages."""

    LUC_USER_ID = "<@527911869550428168>"

    def handle_message(self, message: str) -> Optional[str]:
        """
        Process a message and return an appropriate reply if applicable.

        Args:
            message: The message content to process

        Returns:
            Reply string if applicable, None otherwise
        """
        p_message = message.lower()

        # Greeting
        if p_message.startswith("hola"):
            return "¡Hola!"

        # Help command
        if p_message.startswith("!ayuda"):
            return (
                "¡Hola! Soy RingoBot. Encantade de conocerte.\n\n"
                "Conozco los siguientes comandos:\n"
                "**!insulta** - ¡Insulta a alguien!\n"
                "**!ayuda** - ¡Muestra esta ayuda!\n"
                "Si te da vergüenza, también puedo escribirte al privado si añades `$` antes de `!`"
                "(por ejemplo: `$!ayuda`).\n"
                "\nAdemás, tengo otros comandos más avanzados que puedes consultar con `/`."
            )

        # Fun response to numbers ending in 5
        if p_message.endswith("5") or p_message.endswith("cinco"):
            if random.randint(1, 6) == 5:
                return "Por el culo te la hinco."

        # Insult command
        if p_message.startswith("!insulta"):
            user_parts = message.split(" ")[1:]
            if user_parts:
                if user_parts[0] == self.LUC_USER_ID:
                    return f"Te quiero, {self.LUC_USER_ID} <3"
                else:
                    users = " ".join(user_parts)
                    return f"{users}, gilipollas de mierda."

        # Response to insults
        if p_message.endswith("tu puta madre"):
            return "La tuya, que es más capulla."

        # Good night
        if p_message.startswith("buenas noches"):
            return "¡Buenas noches!"

        # Bot mention
        if "ringobot" in p_message:
            return "¿Qué? ¿Me has llamado?"

        # Suicide prevention
        suicide_phrases = [
            "me mato",
            "me suicido",
            "quiero morir",
            "quiero matarme",
            "me voy a matar",
            "me voy a suicidar",
            "suicidarme",
            "me mataré",
            "me quiero matar",
            "me quiero suicidar",
            "me suicidaré",
        ]

        if any(phrase in p_message for phrase in suicide_phrases):
            return "**Teléfono de prevención del suicidio: 024**"

        return None
