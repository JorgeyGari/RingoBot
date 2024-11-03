def solve_puzzle(puzzle_name: str) -> str:
    # call the function that matches the puzzle name
    return globals()[puzzle_name]()


def hola():
    return "¡Hola!"
