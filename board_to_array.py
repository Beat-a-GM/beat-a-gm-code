import numpy as np
import chess
import chess.svg
#from chess import Move

def is_square_attacked_by_pawns(square, board, color):
    for attacker in board.attackers(color, square):
        if board.piece_type_at(attacker)==chess.PAWN: 
            return True
    return False
def board_to_array(board: chess.Board):
    # Define a dictionary to map pieces to integers
    piece_to_int = {
        'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6,
        'p': -1, 'n': -2, 'b': -3, 'r': -4, 'q': -5, 'k': -6,
        'None': 0
    }

    # Create an 8x8 array of zeros
    board_array = np.zeros((8, 8), dtype=int)

    # Iterate over the board and fill the array
    for i in range(64):
        piece = board.piece_at(i)
        if piece != None:
            board_array[i // 8, i % 8] = board.piece_type_at(i)* (1 if board.color_at(i)==chess.WHITE else -1)#piece_to_int[str(piece)]

    return board_array


def structural_piece_mobility(board: chess.Board, color: chess.Color):
    #maps the piece mobility of black's piece, where they can move without being attacked by a black pawn
    # Create an 8x8 array of zeros
    board_array = np.zeros((8, 8), dtype=int)
    if (board.turn != color): 
        raise Exception("wrong color parameter")
    
    for move in list(board.legal_moves):
        if board.piece_type_at(move.from_square) != chess.PAWN \
            and not is_square_attacked_by_pawns(move.to_square, board, not color):
            board_array[move.to_square // 8, move.to_square % 8]+=1
        
    return board_array
        