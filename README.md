# RingoBot: Bot de Discord para RINGOS 2.0

RingoBot es un bot desarrollado con `py-cord` y diseñado específicamente para asistir a mi grupo de amigos: Ringos.

## Funciones principales

* **Responde a tus mensajes.** RingoBot es tu amigue y responderá a ciertos mensajes de forma automática.
* **Tira dados.** Ya que a los ringos nos encantan los juegos de rol, RingoBot puede ayudarte a tirar dados de distintas formas.
* **Simula *escape rooms*.** Diseñado para emular videojuegos basados en la resolución de acertijos y salas de huida, la extensión [*Discape*](README_discape.md) trae la emoción de estos juegos a Discord.

## Ejecutar con Docker

### Requisitos previos

- Docker y Docker Compose instalados
- Archivo `.env` configurado con el token de Discord

### Configuración inicial

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/JorgeyGari/RingoBot.git
   cd RingoBot
   ```

2. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   # Editar .env y añadir tu DISCORD_TOKEN
   ```

### Comandos de ejecución

- **Iniciar RingoBot:**
  ```bash
  docker-compose up -d
  ```

### Estructura del proyecto

```
RingoBot/
├── src/
│   ├── bot/ringobot.py           # Clase principal del bot
│   ├── modules/                  # Módulos de funcionalidad
│   │   ├── dice.py               # 🎲 Dados de RPG
│   │   ├── music.py              # 🎵 Reproducción de música
│   │   ├── discape.py            # 🔍 Escape rooms
│   │   ├── quests.py             # ⚔️ Sistema de misiones
│   │   └── replies.py            # 💬 Respuestas automáticas
│   └── utils/config.py           # ⚙️ Configuración centralizada
├── data/                         # Datos y bases de datos
├── Dockerfile                    # Imagen Docker
└── docker-compose.yml            # Orquestación de contenedores
```
