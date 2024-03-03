import chess
def flip_color(board: chess.Board):
    starting_fen = board.fen()
    parts = starting_fen.split()
    
    # Toggle between 'w' and 'b'
    if parts[1] == 'w':
        parts[1] = 'b'
    else:
        parts[1] = 'w'
    
    # Rejoin the parts into a full FEN string
    return chess.Board(' '.join(parts))