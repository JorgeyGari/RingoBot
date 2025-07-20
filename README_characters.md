# Character Tracking System

This document describes the character tracking system implementation for RingoBot.

## Overview

The character tracking system allows users to register characters and track their PC (points) through a Discord bot interface. The system includes both user commands and admin commands for managing characters and points.

## Quest Completion Workflow

The quest system now includes an approval workflow:

1. **Quest Assignment**: Admins create quests for users
2. **Quest Completion**: Users complete quests using `/misión completar`
3. **Quest Abandonment**: Users can abandon quests using `/misión abandonar`
4. **Admin Review**: Completion notifications are sent to a dedicated channel with reaction buttons
5. **Approval/Rejection**: Admins can react with ✅ (approve) or ❌ (reject)
   - **✅ Approval**: User receives congratulatory message with reward details
   - **❌ Rejection**: Quest is reset to active status, user can attempt again

### User Commands

- **`/personaje ver-balance`**: Check your current PC balance
- **`/personaje cambiar-imagen <imagen_url>`**: Update your character's picture with a custom image URL
- **`/misión solicitar`**: Request a new mission from admins
- **`/misión completar <misión>`**: Report completion of an assigned mission
- **`/misión abandonar <misión>`**: Give up on an assigned mission and unassign it

### Admin Commands

- **`/admin registrar-personaje <usuario> <nombre_personaje> [imagen_url]`**: Register a character for a user (optionally with custom picture)
- **`/admin cambiar-nombre <usuario> <nuevo_nombre>`**: Update a character's name
- **`/admin cambiar-imagen <usuario> <imagen_url>`**: Update a character's picture
- **`/admin modificar-personaje <usuario> [nuevo_nombre] [imagen_url]`**: Modify multiple character attributes at once
- **`/misión crear <jugador> <descripción> <recompensa>`**: Create a mission for a player

## Database Schema

The system uses SQLite with two main tables:

### Characters Table
- `id`: Primary key
- `discord_id`: Unique Discord user ID
- `character_name`: Name of the character
- `points`: Current PC count (default: 0)
- `picture_url`: Character picture URL (optional)
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

### `/personaje ver`
View your character information including name, current PC, registration date, and character picture.

### `/personaje ver-balance`
Check your current PC balance quickly.

### `/personaje cambiar-imagen <imagen_url>`
Update your character's picture by providing an image URL. The URL must start with http:// or https://.

### `/personaje ranking [límite]`
View the leaderboard of characters sorted by PC (highest first). Default limit is 10.

### `/personaje historial`
View your character's point history showing all PC changes with reasons and timestamps.

## Admin Commands

### `/admin registrar-personaje <usuario> <nombre> [imagen]`
Register a new character for a specific user. Optionally include a custom image URL. If no image is provided, the user's Discord avatar will be used. Only administrators can use this command.

### `/admin cambiar-nombre <usuario> <nuevo_nombre>`
Update the name of an existing character without affecting other attributes. Only administrators can use this command.

### `/admin cambiar-imagen <usuario> <imagen_url>`
Update the picture of an existing character. The URL must be valid and start with http:// or https://. Only administrators can use this command.

### `/admin modificar-personaje <usuario> [nuevo_nombre] [imagen_url]`
Modify multiple attributes of an existing character at once. You can provide just a name, just an image URL, or both. This is a convenient way to update characters without using multiple commands. Only administrators can use this command.

### `/admin dar-pc <usuario> <cantidad> [razón]`
Give PC to a specific user's character. Only administrators can use this command.

### `/admin quitar-pc <usuario> <cantidad> [razón]`
Remove PC from a specific user's character. Only administrators can use this command.

### `/admin borrar-personaje <usuario>`
Delete a user's character and all associated history. Only administrators can use this command.

## Features

- **Admin-Only Registration**: Only administrators can register characters for users
- **Character Modification**: Administrators can modify existing characters without re-registration
- **Flexible Updates**: Individual attribute updates (name/picture) or combined modifications
- **Unique Characters**: Each Discord user can only have one character
- **Custom Character Pictures**: Support for custom character images with fallback to Discord avatars
- **User Picture Updates**: Users can update their character pictures themselves
- **Point Tracking**: All point changes are logged with reasons and timestamps
- **Audit Trail**: Complete history of who made changes and when
- **Guild Support**: Characters are associated with specific Discord servers
- **Negative Point Prevention**: Points cannot go below 0
- **Admin Controls**: Full administrative control over character management
- **URL Validation**: Automatic validation of image URLs for character pictures

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
/personaje ver
/personaje actualizar-imagen https://example.com/character.jpg
/personaje ranking 5
/personaje historial

# Admin commands
/admin registrar-personaje @usuario Aragorn
/admin registrar-personaje @usuario Legolas https://example.com/elf.jpg
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
