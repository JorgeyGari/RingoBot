# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RingoBot is a Discord bot written in Python using py-cord, designed for a friend group (Ringos). It features dice rolling for RPG, music playback from YouTube, escape room simulations, automatic message replies, and a quest/mission system.

## Development Setup

### Environment Setup

```bash
# Create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create and configure .env file
cp .env.example .env
# Edit .env and add your DISCORD_TOKEN as TOKEN=<your_token_here>
```

### Key Dependencies

- **py-cord 2.6.1**: Discord API wrapper (not discord.py)
- **yt-dlp**: YouTube downloader for music module
- **PyNaCl**: Audio support for voice channels
- **openpyxl**: Excel file parsing for Discape module
- **python-dotenv**: Environment variable management

### Running Locally

```bash
# Direct execution
python src/main.py

# With Docker
docker-compose up -d
docker-compose logs -f ringobot
docker-compose down
```

## Architecture

### Module Pattern

RingoBot uses a **modular architecture** where each feature is an independent module:

1. **RingoBot** (`src/bot/ringobot.py`) - Main orchestrator class
   - Initializes all modules
   - Registers Discord event handlers (message, reactions)
   - Registers slash commands and groups
   - Manages command routing to appropriate modules

2. **Modules** (`src/modules/`) - Independent feature implementations
   - **DiceModule**: Dice rolling with various formats (XdY, fate dice)
   - **MusicModule**: YouTube audio playback in voice channels
   - **RepliesModule**: Automatic message responses (deterministic + probabilistic)
   - **DiscapeModule**: Escape room game simulation with inventory and investigations
   - **QuestsModule**: RPG mission system with database persistence

3. **Config** (`src/utils/config.py`) - Centralized configuration
   - Environment variables from .env
   - Discord IDs for channels and guilds
   - File paths and external service settings
   - Validation on startup

### Module Integration Pattern

Each module follows this pattern:

```python
class FeatureModule:
    async def handle_<command>_command(self, ctx, args):
        """Process slash command request."""
        # Implement command logic
        await ctx.respond(...)
```

Modules are **instantiated once** in RingoBot and referenced throughout. Slash command handlers call appropriate module methods, passing the Discord context.

### Data Persistence

- **Quests**: SQLite database (`data/quests.db`)
- **Discape**: Excel file (`data/file.xlsx`) with game state
- **Downloads**: Temporary music files (`downloads/`)
- **Logs**: Persistent logs (`logs/ringobot.log`)

Data directories are auto-created by config validation.

## Command Structure

### Slash Commands

All registered via `_register_commands()`:

- `/dado [dados] [modificador]` - Roll dice with optional modifier
- `/ytmusic [link]` - Play YouTube audio
- `/escape` - Command group with subcommands:
  - `iniciar [archivo]` - Start escape room from Excel file
  - `tirada [característica]` - Roll d20 with stat bonus
  - `investigar [objetivo]` - Investigate with autocomplete
  - `objetos` - Show inventory
  - `equipar [objeto]` - Equip item
  - `combinar [objeto1] [objeto2]` - Combine items
  - `unirse` - Join active escape room
- `/misión` - Quest command group:
  - `solicitar` - Request a quest
  - `crear [jugador] [descripción] [recompensa]` - Create quest
  - `completar [misión]` - Complete quest

### Message-Based Commands

- Private messages starting with `$` invoke `RepliesModule.handle_message()` with DM response
- Regular messages matching patterns trigger automatic replies or emoji reactions

## Key Patterns

### Configuration Validation

Config errors halt startup:

```python
config_errors = config.validate_config()
if config_errors:
    logger.error("Configuration errors:")
    for error in config_errors:
        logger.error(f"  - {error}")
    sys.exit(1)
```

### In-Memory Caching

Hall of fame uses a set to prevent duplicate posts on reaching star threshold:

```python
self.hall_of_fame_cache = set()  # Tracks message_id
```

### Emoji Reactions

Special "emoji_react:" prefix signals reaction response instead of text reply. Maps named identifiers to Unicode emojis:

```python
emoji_map = {"waving_hand": "👋"}
```

### Autocomplete Integration

Slash commands use `discord.utils.basic_autocomplete()` for dynamic option suggestions:

```python
@discord.option(
    "objetivo",
    autocomplete=discord.utils.basic_autocomplete(
        self._get_investigation_options
    ),
)
```

## Important Files

| File | Purpose |
|------|---------|
| `src/main.py` | Entry point, logging setup |
| `src/bot/ringobot.py` | Core orchestrator, event/command registration |
| `src/utils/config.py` | Configuration validation and constants |
| `src/modules/*.py` | Feature implementations |
| `Dockerfile` | Container image (Python 3.12, ffmpeg, system deps) |
| `docker-compose.yml` | Service orchestration with volume mounts |
| `requirements.txt` | Python dependencies |

## Debugging & Logging

- All modules use `logging.getLogger(__name__)`
- Logs written to both console and `logs/ringobot.log`
- Discord token validation happens at startup via `config.validate_config()`
- Module errors logged with context; individual module errors don't crash bot

## Testing Considerations

- No existing test suite
- Manual testing via Discord requires valid TOKEN in .env
- Modules can be tested in isolation by importing and calling methods directly
- Database operations in QuestsModule use SQLite (consider test database path)
- File operations in DiscapeModule depend on Excel file presence

## Development Notes

- The codebase uses Spanish for Discord messages and commands (game group preference)
- Each module can be modified independently without affecting others
- Discord intents set to `.all()` for access to all event types
- Non-root user in Docker for security
- Volume mounts preserve data/logs/downloads across container restarts
- FFmpeg required system dependency for music processing
