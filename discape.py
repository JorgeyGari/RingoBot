from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient import errors

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
KEY = 'key.json'
SPREADSHEET_ID = '1GL-QM22vXwWWMUL3Cgn-DTIfLrOelFkvF7rsw_qDRJA'

creds = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES)

service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Get the list of sheets within the spreadsheet
spreadsheet = sheet.get(spreadsheetId=SPREADSHEET_ID).execute()
sheet_properties = spreadsheet.get('sheets', [])


def get_column_values(sheet_name, column_letter):
    """Returns a list with the values of the specified column. Includes empty cells."""
    range_to_get = f"{sheet_name}!{column_letter}:{column_letter}"
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=range_to_get).execute()
    values = result.get('values', [])

    col_values = []
    for value in values:
        if value:  # Check if the list is not empty before accessing its elements
            col_values.append(value[0])
        else:
            col_values.append('')

    return col_values


def remove_row(sheet_num: int, row_num: int):
    """Removes the specified row of the specified sheet."""
    sheet_id = sheet_properties[sheet_num - 1]['properties']['sheetId']

    # Delete the entire row
    delete_request = {
        "requests": [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_num - 1,  # Index of the row you want to delete, 0-based
                        "endIndex": row_num  # Index + 1 of the next row, making it a single-row range
                    }
                }
            }
        ]
    }

    try:
        sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=delete_request).execute()
        print(f"Row {row_num} deleted successfully from Sheet {sheet_num}.")
    except errors.HttpError as error:
        print(f"An error occurred: {error}")


def add_row(sheet_num: int, row_values: list):
    """Adds a new row at the end of the specified sheet."""
    sheet_id = sheet_properties[sheet_num - 1]['properties']['sheetId']

    # Add the new row
    append_request = {
        "requests": [
            {
                "appendCells": {
                    "sheetId": sheet_id,
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {
                                        "stringValue": value
                                    }
                                } for value in row_values
                            ]
                        }
                    ],
                    "fields": "userEnteredValue"
                }
            }
        ]
    }

    try:
        sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=append_request).execute()
        print(f"Row {row_values} added successfully to Sheet {sheet_num}.")
    except errors.HttpError as error:
        print(f"An error occurred: {error}")


def get_stat(player: str, stat: str) -> int:
    """Returns the value of the specified stat for the specified player."""
    sheet_name = 'Personajes'
    player_column = 'B'
    stat_col = {
        'Fuerza': 'C',
        'Resistencia': 'D',
        'Agilidad': 'E',
        'Inteligencia': 'F',
        'Suerte': 'G'
    }
    player_row = get_column_values(sheet_name, player_column).index(player)
    stat_value = get_column_values(sheet_name, stat_col[stat])[player_row]

    return stat_value

def get_player_location(player: str) -> list[str]:
    """Returns the room and path of the specified player."""
    sheet_name = 'Personajes'
    player_column = 'B'
    room_column = 'H'
    path_column = 'I'
    player_row = get_column_values(sheet_name, player_column).index(player)
    room = get_column_values(sheet_name, room_column)[player_row]
    try:
        path = get_column_values(sheet_name, path_column)[player_row]
    except IndexError:
        path = ''

    return [room, path]

def update_player_location(player: str, room: str, path: str):
    """Updates the room and path of the specified player."""
    sheet_name = 'Personajes'
    player_column = 'B'
    room_column = 'H'
    path_column = 'I'
    player_row = get_column_values(sheet_name, player_column).index(player)
    room_range = f"{sheet_name}!{room_column}{player_row + 1}"
    path_range = f"{sheet_name}!{path_column}{player_row + 1}"
    room_body = {
        "values": [
            [
                room
            ]
        ]
    }
    path_body = {
        "values": [
            [
                path
            ]
        ]
    }

    try:
        sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=room_range, body=room_body, valueInputOption='USER_ENTERED').execute()
        sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=path_range, body=path_body, valueInputOption='USER_ENTERED').execute()
        print(f"Player {player} location updated successfully.")
    except errors.HttpError as error:
        print(f"An error occurred: {error}")

def get_zones(player: str) -> list[str]:
    """Returns a list with the names of the zones."""
    [room, path] = get_player_location(player)
    sheet_name = room
    last_column = 'F'
    zone_range = f"{sheet_name}!A2:{last_column}"
    depth_col = 2
    data = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=zone_range).execute()
    values = data.get('values', [])
    zones = []
    if not values:
        print('No data found.')
    else:
        for row in values:
            if row[depth_col] == path and (len(row) < 5 or row[4] == ''):
                zones.append(row[0])

    return zones


def unlock_zone(player: str, item: str):
    [room, path] = get_player_location(player)
    sheet_name = room
    last_column = 'F'
    zone_range = f"{sheet_name}!A2:{last_column}"
    depth_col = 2
    data = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=zone_range).execute()
    values = data.get('values', [])
    zones = []
    clear_values = [['']]
    if not values:
        print('No data found.')
    else:
        i = 1
        for row in values:
            i += 1
            if len(row) >= 5:
                if row[depth_col] == path and row[4] == item:
                    clear_request = sheet.values().update(spreadsheetId=SPREADSHEET_ID, range=f"{sheet_name}!E{i}", body={'values': clear_values}, valueInputOption='RAW')
                    clear_request.execute()
                    print(row[5])

    return zones


def add_item(new_data: list[str]):
    """Adds a new item to the inventory. The new item must be a list with the following format: [name, description]."""
    append_range = f"Inventario!A:B"  # Specify the columns you want to append to

    # Append the data to the end of the sheet
    request = sheet.values().append(spreadsheetId=SPREADSHEET_ID, range=append_range, valueInputOption="RAW", body={"values": new_data})
    request.execute()

    print("Data appended successfully.")


def get_inventory() -> list[str]:
    sheet_name = 'Inventario'
    last_column = 'B'
    inventory_range = f"{sheet_name}!A2:{last_column}"
    data = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=inventory_range).execute()
    values = data.get('values', [])
    inventory = []
    if not values:
        print('No data found.')
    else:
        for row in values:
            inventory.append(row[0])

    return inventory

def combine(obj1: str, obj2: str):
    sheet_name = 'Combinaciones'
    last_column = 'D'
    combinations_range = f"{sheet_name}!A2:{last_column}"
    data = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=combinations_range).execute()
    combinations = data.get('values', [])
    if not combinations:
        print('No data found.')
    else:
        for row in combinations:
            if (row[0] == obj1 and row[1] == obj2) or (row[0] == obj2 and row[1] == obj1):
                inventory_range = "Inventario!A:B"
                inventory_data = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=inventory_range).execute()
                inventory = inventory_data.get('values', [])
                if not inventory:
                    print('No data found.')
                else:
                    i = 1
                    for item in inventory:
                        if item[0] == obj1 or item[0] == obj2:
                            remove_row(3, i)
                        else:
                            i += 1

                add_item([row[2:4]])

def unlock_item(room: str, item: str):
    sheet_name = room
    last_column = 'F'
    zone_range = f"{sheet_name}!A2:{last_column}"
    data = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=zone_range).execute()
    values = data.get('values', [])

    for row in values:
        if item in row:
            add_item([row[0:2]])
            remove_row(2, values.index(row) + 2)

def take_path(player: str, choice: str):
    """Moves the player to the specified path or adds the item to the inventory.
    Returns the description of the new room or the description of the item."""
    [room, current_path] = get_player_location(player)
    sheet_name = room
    last_column = 'F'
    zone_range = f"{sheet_name}!A2:{last_column}"
    depth_col = 2
    data = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=zone_range).execute()
    values = data.get('values', [])
    if choice == '↩️ Volver':
        update_player_location(player, room, current_path[:-1])
        return f'Volviste al lugar anterior.'
    if not values:
        print('No data found.')
    else:
        for row in values:
            if row[depth_col] == current_path and row[0] == choice:
                if row[3] != 'Objeto':
                    update_player_location(player, room, current_path + row[3])
                else:
                    unlock_item(room, choice)
                return row[1]