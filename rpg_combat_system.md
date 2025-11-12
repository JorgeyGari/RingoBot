# RPG Combat System Description

## Description from creative document
Sistema de combate
	En algunas ocasiones, una bestia atacará Teséia y algunos de los participantes (los que hayan perdido en el juego del glifo) le harán frente en una batalla por turnos.

	El turno de los jugadores se determinará mediante una tirada de Agilidad al inicio del combate. Después de eso, los turnos se sucederán y los jugadores podrán elegir entre dos opciones:

Atacar: El atacante tira un dado de 6 caras al que le suma su Fuerza. El defensor tira un dado de 6 caras al que le suma su Aguante.
Si la tirada del atacante supera a la del defensor, le hace un daño equivalente a la diferencia entre las tiradas.
Si la tirada del atacante es igual o inferior a la del defensor, el ataque no conecta.
Técnica: Diversas posibilidades que alterarán el combate según el tipo de técnica. Cada técnica tendrá asociada una característica del jugador.

	El combate terminará cuando el enemigo tenga la vida a 0. Los participantes comienzan con una vida fija. Si la vida de un participante llega a 0, quedará fuera de combate y en estado crítico para el rol. Tendrá que recuperarse. Existe el riesgo de morir en combate o en consecuencia de daños graves.

	Los participantes pueden equiparse con diversos objetos (armas, armaduras…) que pueden potenciar sus características a la hora de combatir. Estos objetos se pueden obtener en el gachapón.

	Algunos ataques añadirán estados negativos al defensor. Estos estados pueden ser:

Terror. En cada turno, hay una probabilidad de ⅕ de que no puedas atacar.
Náuseas. Cada dos turnos, perderás un punto de vida.
Nostalgia. Impide el uso de técnicas.

## Character stats
These are modifiers that go from +0 to +4.

- **Fuerza**: Influye en el daño infligido al atacar.
- **Aguante**: Influye en la defensa al recibir ataques.
- **Agilidad**: Determina el orden de los turnos en combate y la probabilidad de esquivar ataques.
- **Conocimiento**
- **Encanto**

Additionally, all characters have a **Vida** stat that determines how much damage they can take before being incapacitated.

## Armor and Weapons
Characters can equip an armor and a weapon, which can add modifiers to their stats. These items can be obtained through the gacha.

## Techniques
Techniques are special abilities that can be used during combat. Some techniques are common to all characters, while others are unique to specific characters. There should be a database of techniques that includes:
- **Technique Name**: The name of the technique.
- **Description**: A brief description of what the technique does.
- **Associated Stat**: The character stat that the technique is based on (e.g., Fuerza, Agilidad).
- **Effect on Combat**: How the technique affects the combat (e.g., damage, status effects).
- **Cost**: Techniques have a turn cost, which is the number of turns a character must wait before using the technique again. It can be 0 (instant use) or a positive integer (e.g., 1, 2, etc.).

## Enemy Combat and Stats
Enemies will have their own stats similar to characters, including:
- **Fuerza**: Damage dealt when attacking.
- **Aguante**: Defense against attacks.
- **Agilidad**: Determines the order of turns and evasion.
- **Vida**: Total health points.
- **Special Abilities**: Unique abilities that enemies can use during combat, akin to character techniques.

Admins must have a way to register enemies with their stats and abilities, similar to how characters are registered.
