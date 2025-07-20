"""
Dice rolling module for RPG dice functionality.
"""

import random
import logging
import discord
from discord.ext import commands
from typing import Optional

logger = logging.getLogger(__name__)


class DiceModule:
    """Handles dice rolling functionality."""

    def validate_dice(self, dice: str) -> Optional[str]:
        """
        Validate dice input format.

        Args:
            dice: Dice string (e.g., "2d6", "1d20", "4df")

        Returns:
            Error message if invalid, None if valid
        """
        if "d" not in dice:
            return "Necesito que me des los dados en un formato válido. Por ejemplo, `2d6`, `1d20` o `4df`."

        try:
            number_of_dice, dice_type = dice.split("d")

            # Validate dice type
            if dice_type != "f":
                if not dice_type.isnumeric():
                    return "Necesito que me des los dados en un formato válido. Por ejemplo, `2d6`, `1d20` o `4df`."
                if int(dice_type) < 2 or int(dice_type) > 9999:
                    return "¿De dónde quieres que saque un dado así?"

            # Validate number of dice
            if not number_of_dice.isnumeric():
                return "Necesito que me des los dados en un formato válido. Por ejemplo, `2d6`, `1d20` o `4df`."
            if int(number_of_dice) < 1:
                return "¿Entonces... no tiro ningún dado?"
            if int(number_of_dice) > 100:
                return "Oye, no tengo tantos dados."

        except ValueError:
            return "Necesito que me des los dados en un formato válido. Por ejemplo, `2d6`, `1d20` o `4df`."

        return None

    def human_readable_dice(self, dice: str) -> str:
        """
        Convert dice notation to human-readable format.

        Args:
            dice: Dice string (e.g., "2d6")

        Returns:
            Human-readable string
        """
        number_of_dice, dice_type = dice.split("d")
        number = int(number_of_dice)

        number_text = "un" if number == 1 else str(number)
        dice_type_text = "fate" if dice_type == "f" else f"{dice_type} caras"
        plural = "" if number == 1 else "s"

        if dice_type == "f":
            return f"{number_text} dado{plural} de Fate"
        return f"{number_text} dado{plural} de {dice_type_text}"

    def roll_dice(self, dice: str) -> list:
        """
        Roll dice and return results.

        Args:
            dice: Dice string (e.g., "2d6")

        Returns:
            List of dice results
        """
        number_of_dice, dice_type = dice.split("d")
        number = int(number_of_dice)

        if dice_type == "f":
            # Fate dice: -, ·, +
            fate_dice = ["-", "·", "+"]
            return [random.choice(fate_dice) for _ in range(number)]

        sides = int(dice_type)
        return [random.randint(1, sides) for _ in range(number)]

    def calculate_total(self, roll: list) -> int:
        """
        Calculate total from dice roll results.

        Args:
            roll: List of dice results

        Returns:
            Total sum
        """
        fate_values = {"-": -1, "·": 0, "+": 1}
        return sum(fate_values.get(die, die) for die in roll)

    async def handle_roll_command(self, ctx, dados: str, modificador: int):
        """
        Handle the dice roll slash command.

        Args:
            ctx: Discord application context
            dados: Dice notation string
            modificador: Modifier to add to the roll
        """
        # Validate dice input
        error = self.validate_dice(dados)
        if error:
            await ctx.respond(error, ephemeral=True)
            return

        try:
            # Roll the dice
            roll = self.roll_dice(dados)
            total_roll = self.calculate_total(roll) + modificador

            # Format response
            response = (
                f"¡Has tirado {self.human_readable_dice(dados)}!\n"
                f"`{roll}`\n"
                f"**Total:** {total_roll}"
            )

            await ctx.respond(response)
            logger.info(f"Dice roll: {dados} -> {roll} (total: {total_roll})")

        except Exception as e:
            logger.error(f"Error in dice roll: {e}")
            await ctx.respond(
                "Error al tirar los dados. Inténtalo de nuevo.", ephemeral=True
            )
