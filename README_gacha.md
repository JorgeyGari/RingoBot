# 🎲 Gacha System Documentation

## Overview

The Gacha system allows users to spend their PC (Points) to obtain random items from a prize pool. The system includes:

- **Single rolls** (10 PC each)
- **5-roll multipulls** with rare+ guarantee (50 PC)
- **10-roll multipulls** with legendary guarantee (100 PC)
- **Special character bonuses** for character-specific items
- **Inventory management** system
- **Roll history** tracking

## 📊 Rarity System

### Rarity Levels
- **⚪ Común (Rarity 1)**: ~70% drop rate
- **🟡 Raro (Rarity 2)**: ~25% drop rate  
- **🟣 Legendario (Rarity 3)**: ~5% drop rate

### Guarantee System
- **5-roll**: Guarantees at least 1 rare+ (rarity 2 or 3) item
- **10-roll**: Guarantees at least 1 legendary (rarity 3) item

### Special Character Bonus
Characters with special items have a 50% chance to receive their character-specific item when rolling a legendary (rarity 3) prize.

**Current Special Characters:**
- **Mark**: Coche teledirigido
- **Hikaru**: Colgante místico

## 🎮 Commands

### `/gacha roll`
- **Cost**: 10 PC
- **Description**: Make a single roll
- **Returns**: 1 random item

### `/gacha roll5`
- **Cost**: 50 PC  
- **Description**: Make 5 rolls with rare+ guarantee
- **Returns**: 5 items, guaranteed at least 1 rare+

### `/gacha roll10`
- **Cost**: 100 PC
- **Description**: Make 10 rolls with legendary guarantee  
- **Returns**: 10 items, guaranteed at least 1 legendary

### `/gacha inventario`
- **Description**: View your item inventory
- **Returns**: List of owned items grouped by rarity

### `/gacha objeto <nombre>`
- **Description**: View detailed information about a specific item
- **Returns**: Item details including description and rarity

### `/gacha premios [rareza]`
- **Description**: View available prizes (optionally filtered by rarity)
- **Returns**: List of all prizes or prizes of specific rarity

### `/gacha historial`
- **Description**: View your last 10 roll history
- **Returns**: Timeline of recent rolls and their results

## 💾 Database Schema

### `user_inventory`
- `id`: Primary key
- `discord_id`: User's Discord ID (Foreign Key)
- `item_name`: Name of the item
- `quantity`: Number owned
- `obtained_date`: When item was obtained

### `roll_history`
- `id`: Primary key
- `discord_id`: User's Discord ID (Foreign Key)
- `roll_type`: "single", "multi5", or "multi10"
- `cost`: PC spent
- `items_obtained`: Comma-separated list of items
- `timestamp`: When roll occurred

## 📋 Prize List (Current)

### ⚪ Común (Rarity 1)
- Sándwich de pollo - Lleva pechuga, lechuga, tomate y mayonesa. (VID +10)
- Refresco - Bebida refrescante con aroma a cola. (VID +5)
- Camiseta del Betis - Camiseta oficial del Real Betis Balompié.
- Pan tostado - Crujiente y sabroso. (VID +3)
- Chicle - Sabor menta. Horas de diversión.
- Llave inglesa - Herramienta básica de mecánico. (ATQ +1)

### 🟡 Raro (Rarity 2)
- Bate de béisbol - El arma idónea en un apocalipsis zombi. (ATQ +2)
- Bolsa de palomitas al microondas - Palomitas de maíz listas en 2 minutos. (VID +5 a cada compi)
- Galleta de la abuelita - ¡Come! ¡Que estás en los huesos! (Elimina estados alterados negativos)
- Armadura ligera - Protección básica contra ataques. (DEF +3)
- Poción de vida - Restaura completamente la vida. (VID completa)

### 🟣 Legendario (Rarity 3)
- Coche teledirigido - Enseña una nueva técnica a Mark: «Coche bomba». **(Especial de Mark)**
- Colgante místico - La mejor armadura para Hikaru. **(Especial de Hikaru)**
- Espada legendaria - Una espada de poder incalculable. (ATQ +10)
- Corona dorada - Símbolo de poder y riqueza.
- Grimorio ancestral - Libro de hechizos antiguos. (MAG +8)

## 🔧 Technical Implementation

### Files Modified/Created:
- `src/modules/gacha.py` - Main gacha module
- `data/prizes.csv` - Prize database (enhanced with Special_Character column)
- `src/bot/ringobot.py` - Added gacha commands and handlers

### Key Classes:
- `GachaModule` - Main gacha functionality
- `Prize` - Prize data structure  
- `RollResult` - Roll result data structure

### Integration Points:
- **Characters Module**: For user validation and point deduction
- **Database**: Shared SQLite database for inventory and history
- **CSV**: Prize data stored in `data/prizes.csv`

## 🚀 Future Enhancements

### Possible Additions:
1. **Limited-time banners** with rate-up items
2. **Pity system** tracking consecutive rolls without legendaries
3. **Item trading** between users
4. **Daily free rolls** or login bonuses
5. **Achievement system** for collecting items
6. **Seasonal/event items** with time-limited availability
7. **Item fusion/upgrade** system

### Adding New Items:
1. Edit `data/prizes.csv`
2. Add new row with: Name, Description, Rareness, Special_Character (optional)
3. Restart bot to reload prize data

### Adding Special Characters:
1. Add character name to Special_Character column for desired items
2. Items with same character will be grouped together
3. 50% chance for character to get their special item on legendary rolls

## 🐛 Error Handling

The system includes comprehensive error handling for:
- **Insufficient PC**: Users cannot roll without enough points
- **Database errors**: Automatic rollback and point refund on failures
- **Invalid items**: Graceful handling of missing item information
- **Connection issues**: Timeout and retry mechanisms

## 📈 Statistics

Test results show proper distribution:
- Special character bonuses activate correctly
- Guarantee systems work as intended
- Database operations are atomic and safe
- Roll distributions match expected probabilities

---

*Documentation last updated: July 20, 2025*
