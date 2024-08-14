# Discape

## Acerca de

Discape es una biblioteca que añade nuevos comandos al RingoBot para dar una interfaz (inspirada en el sistema de Zero Escape) que simula juegos de salas de huida para múltiples jugadores simultáneos mediante comandos de barra diagonal en Discord.

## Objetivos

* Aligerar la carga de trabajo de un director de juego en una campaña de rol con temática de misterio
* Ser fácil de utilizar para una persona que no tenga ninguna experiencia con la programación
* Proporcionar al usuario una experiencia lo más cercana posible a un videojuego mediante comandos de Discord

## Funcionamiento

El programa toma como única entrada un archivo `.xlsx` con los datos que requiere y manipulará durante su funcionamiento. Esta (peculiar) elección se debe a tres razones:

* Un libro de Excel es la manera más conocida de visualizar datos en un formato similar a una base de datos
* Excel solo requiere un nivel básico de conocimientos informáticos
* Una base de datos requiere un proveedor, pero un archivo `.xlsx` solo requiere de una herramienta de ofimática que la mayoría de usuarios ya tiene descargada en su equipo

El archivo puede ser cargado mediante un comando solo accesible a un administrador.

Una vez cargado el archivo, el bot guardará los cambios en una copia local cada vez que tenga que escribir. Esto servirá como resguardo por si la ejecución se detuviera de manera inesperada. En ese caso, todo lo que se debe hacer es cargar la copia local y la sala de huida continuará desde donde los jugadores la dejaron.

### Abstracción de una sala de huida

Para nosotros, una sala de huida es un conjunto de **atracciones** que pueden ser investigadas. Investigar una atracción puede hacerse con las manos vacías o con un **objeto equipado**. Los usuarios que investigan en una sala de huida son **jugadores** que interpretan a un **personaje**. Cuando un usuario investiga una atracción, esta puede no devolverle nada, desbloquear un **objeto** o **permitir la salida**. Si a un usuario se le permite la salida, ha logrado escapar y se considera una victoria.

> **Ejemplo:** Kai investiga una cajonera y trata de abrir un cajón. El cajón está bloqueado por un cerrojo. Kai utiliza una llave para abrir el cerrojo y dentro encuentra un diario.
>
> Esto son dos acciones interpretadas por el `personaje` Kai sobre la `atracción` cajón. En su primera acción, al `investigar`, Kai no tiene ningún objeto equipado. La atracción no devuelve nada. En la segunda acción, Kai `investiga` con un `objeto equipado`: la llave. Ahora, la `atracción` cajón devuelve un nuevo `objeto`: el diario.

### Estructura del `.xlsx`

#### Personajes

La primera hoja será la hoja de **Personajes**.
Está compuesta de las siguientes columnas:

| Nombre | Jugador | Sala | Camino | Equipado | *Fuerza* | *Resistencia* | *Agilidad* | *Inteligencia* | *Suerte* |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nombre del personaje | Alias (@) en Discord | Nombre del canal que representa la sala en la que se encuentra el personaje | Sucesión de decisiones que ha tomado el jugador | Objeto que el personaje lleva en la mano | Número | Número | Número | Número | Número |

Las características numéricas son personalizables y ayudan a la hora de hacer tiradas de salvación. Las que aparecen en la tabla son meros ejemplos.

#### Inventario

La segunda hoja será la hoja de **Inventario**. Esta representa los objetos que ha recogido el equipo que está investigando. Los objetos descubiertos se comparten entre todos los participantes de una misma sala de huida.
Está compuesta de las siguientes columnas:

| Objeto | Descripción | Sala |
| --- | --- | --- |
| Nombre del objeto | Descripción del objeto | Sala (canal) a la que pertenece este objeto

#### Combinaciones

La tercera hoja será la hoja de **Combinaciones**. Dos objetos del inventario pueden ser combinados para producir un nuevo objeto. En la práctica, esto elimina dos objetos en la hoja de inventario y crea uno nuevo que los sustituye.

> **Ejemplo:** Kai ha encontrado un destornillador y un mando de televisión y los ha guardado. Si utiliza el destornillador con el mando de televisión, puede desatornillar el mando y recoger las pilas que tiene dentro.
>
> Kai ha `combinado` dos `objetos` que tenía en el inventario: el destornillador y el mando de televisión. Estos dos `objetos` se han eliminado de su inventario y se ha añadido uno nuevo: las pilas.

Está compuesta de las siguientes columnas:

| Objeto 1 | Objeto 2 | Resultado | Descripción | Sala |
| --- | --- | --- | --- | --- |
| Objeto para combinar | Objeto para combinar | Objeto nuevo | Descripción del objeto nuevo | Sala a la que pertenecen los objetos |

#### Sala de huida

La cuarta hoja en adelante son las hojas de la **Sala de huida**. Describen la estructura de la sala.

Una sala de huida se asocia con un canal del servidor. Por eso, el título de la hoja debe coincidir exactamente con el título del canal que servirá para este canal. Por ejemplo, si nuestra sala se llama "Sala de prueba" y los jugadores resalizarán la investigación en el canal *#sala-de-prueba*, el título de la hoja deberá ser "sala-de-prueba".

Una hoja de sala de huida está compuesta de las siguientes columnas:

| Atracción | Descripción | Profundidad | Camino | Llave | Acción |
| --- | --- | --- | --- | --- | --- |
| Nombre de una de las atracciones que componen la sala de huida | Descripción de la atracción | Camino previo necesario para que el jugador pueda ver esta atracción | Nuevo paso en el camino al investigar esta atracción | Llave necesaria para que el jugador pueda acceder a esta atracción | Descripción de la acción que revela esta atracción al usar la llave |

El **camino** representa las decisiones de investigación que ha tomado el jugador. Cuando inicia una sala de huida, el camino está vacío. Al elegir investigar una atracción, está tomando una decisión que se representa escribiendo una nueva letra en el camino. En esencia, es un árbol.

> **Ejemplo:** Kai entra en la sala de huida. Su `camino` está vacío.
>
> Tiene dos opciones para avanzar: puede ir por el pasillo izquierdo (A) o puede ir por el pasillo derecho (B). Kai elige el pasillo izquierdo. Su `camino` ahora es: `A`.
>
> Al entrar en el pasillo izquierdo, se encuentra con tres habitaciones: un baño (A), una cocina (B) o un estudio (C). Kai ha decidido entrar en la cocina. Su `camino` ahora es: `AB`.
>
> Kai solo encuentra un frigorífico en la cocina, así que decide volver. Su última decisión se borra del camino, porque ha vuelto sobre sus pasos. Su camino ahora es: `A`.

Algunas palabras clave sirven para determinar el comportamiento especial de algunas atracciones:

* Si la columna "Camino" contiene la palabra "Objeto", la atracción es un objeto recogible. Desaparecerá de la sala en cuanto alguien la investigue y generará un objeto nuevo en el inventario.

* Si la columna "Camino" contiene la palabra `Final`, la atracción es la salida de la sala. Al investigarla, todos los jugadores que estaban en ella serán liberados (su columna "Sala" pasa a estar vacía).

La **profundidad** de una atracción representa el lugar donde está localizada. Para que una atracción sea visible para un jugador, deben cumplirse dos condiciones:

1. La profundidad de la atracción es igual al camino que ha tomado el jugador.
2. La atracción no tiene llave.

> **Ejemplo:** En el caso de arriba, estas son las profundidades de cada una de las atracciones mencionadas:
>
> Pasillo izquierdo: `` (profundidad nula)  
> Pasillo derecho: `` (profundidad nula)  
> Baño: `A`  
> Cocina: `A`  
> Estudio: `A`  
> Frigorífico: `AB`  

La **llave** es el objeto con el que es necesario investigar el camino previo para revelar la atracción a la que está asociada. Cuando el usuario investiga la atracción correcta con el objeto equipado correcto, esta columna se vacía con el mensaje especificado en la columna "Acción".

### Iniciar y terminar una partida

Para que el juego comience, el jugador debe unirse a la sala de huida con un comando. Al hacerlo, su columna "Sala" en la hoja "Personajes" se rellenará con el nombre del canal en el que haya sido ejecutado el comando.
