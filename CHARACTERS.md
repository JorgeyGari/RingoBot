# Character Tracking System

This document describes the character tracking system implementation for RingoBot.

## Overview

The character tracking system allows users to register characters and track their PC (points) through a Discord bot interface. The system includes both user commands and admin commands for managing characters and points.

## Database Schema

The system uses SQLite with two main tables:

### Characters Table
- `id`: Primary key
- `discord_id`: Unique Discord user ID
- `character_name`: Name of the character
- `points`: Current PC count (default: 0)
- `guild_id`: Discord guild/server ID
- `created_at`: Registration timestamp
- `updated_at`: Last modification timestamp

### Point History Table
- `id`: Primary key
- `character_id`: Foreign key to characters table
- `points_change`: Points added/removed (positive/negative)
- `reason`: Optional reason for the change
- `admin_id`: Discord ID of admin who made the change
- `timestamp`: When the change occurred

## User Commands

### `/personaje registrar <nombre>`
Register a new character with the given name. Each Discord user can only have one character.

### `/personaje ver`
View your character information including name, current PC, and registration date.

### `/personaje ranking [límite]`
View the leaderboard of characters sorted by PC (highest first). Default limit is 10.

### `/personaje historial`
View your character's point history showing all PC changes with reasons and timestamps.

## Admin Commands

### `/admin dar-pc <usuario> <cantidad> [razón]`
Give PC to a specific user's character. Only administrators can use this command.

### `/admin quitar-pc <usuario> <cantidad> [razón]`
Remove PC from a specific user's character. Only administrators can use this command.

### `/admin borrar-personaje <usuario>`
Delete a user's character and all associated history. Only administrators can use this command.

## Features

- **Unique Characters**: Each Discord user can only register one character
- **Point Tracking**: All point changes are logged with reasons and timestamps
- **Audit Trail**: Complete history of who made changes and when
- **Guild Support**: Characters are associated with specific Discord servers
- **Negative Point Prevention**: Points cannot go below 0
- **Admin Controls**: Full administrative control over character management

## File Structure

- `src/modules/characters.py`: Main character management module
- `src/utils/config.py`: Configuration including database path
- `data/characters.db`: SQLite database file (created automatically)

## Configuration

Add the following to your config file:
```python
CHARACTER_DB_PATH = "data/characters.db"
```

## Usage Examples

```
# User commands
/personaje registrar Aragorn
/personaje ver
/personaje ranking 5
/personaje historial

# Admin commands
/admin dar-pc @usuario 10 "Quest completion reward"
/admin quitar-pc @usuario 2 "Minor rule violation"
/admin borrar-personaje @usuario
```

## Error Handling

The system includes comprehensive error handling for:
- Database connection issues
- Duplicate character registrations
- Missing characters
- Invalid point amounts
- Permission checks for admin commands

## Logging

All character operations are logged including:
- Character registrations
- Point changes
- Errors and warnings
- Database operations
