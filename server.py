from flask import Flask, request, jsonify, make_response
from stockfish import Stockfish
import chess
import chess.pgn
import requests
import re
import chess
from testpos import testpos
from gpttest import gpt_call
import io
from flip_color import flip_color
app = Flask(__name__)

app.config['curr_month'] = 2
app.config['split_result'] = []
app.config['game_index']=0
# Initialize Stockfish
stockfish = Stockfish('/opt/homebrew/bin/stockfish', depth=20)

@app.route('/get-pawn-moves', methods=["GET"]) #get positions to fill up the training data for the pawn move enemy restriction model
def get_pawn_moves():
    if app.config['game_index']>=len(app.config['split_result']):#fill up the data
        string = f"https://api.chess.com/pub/player/hikaru/games/2023/{app.config['curr_month']}/pgn"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
        data = requests.get(string, headers=headers)
        if (data.status_code != 200):
            print("Request was a failure")
            return jsonify("Request was a failure")
        app.config['split_result'] = data.text.split("Event \"Live Chess\"]")[1:]
        app.config['game_index']=0
        app.config['curr_month']+=1
        if (app.config['curr_month']>12):
            return jsonify("already used all of the games in the year")
        
    #go through a game and accumulate all of the right pawn pushes in a list
    board = chess.Board()
    result = []
    game = app.config['split_result'][app.config['game_index']]
    app.config['game_index']+=1
    game_pgn = chess.pgn.read_game(io.StringIO(game))
    for move in game_pgn.mainline_moves():
        if len(result)>3: break
        if (board.fullmove_number>40): break #we are looking at middlegame positions only
        
        #print(board.fen() + " " + board.uci(move) + " " + board.san(move) + " " + str(board.piece_at(move.from_square)))
        is_mg_pawn_push = board.fullmove_number>=15 and board.piece_type_at(move.from_square)==chess.PAWN and \
            not board.is_capture(move) and not move.promotion
        board.push(move)
        if (not is_mg_pawn_push): continue
        board.pop()
        fen = board.fen()
        result.append({"fen": fen, "uci": move.uci(), "san": board.san(move)})
        board.push(move)
    return result
                
                
            
            
        

@app.route('/get-positions', methods=["GET"]) #get positions to fill in the database
def get_positions():
    number = int(request.args.get('number'))
    year = int(request.args.get('year'))
    month = int(request.args.get('month'))
    username = str(request.args.get('username'))
    string = f"https://api.chess.com/pub/player/{username}/games/{year}/{month}/pgn"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    data = requests.get(string, headers=headers)
    #print("data " + data)
    if (data.status_code != 200):
        print("Request was a failure")
        return jsonify("Request was a failure")


    #pgn processing in order to extract date, white username, black username, link, and moves
    split_result = data.text.split("Event \"Live Chess\"]")[1:]
    result = []
    for game in split_result:
        #print("looking at new game")
        #remove ] character and {} move time stamps from the game string
        last_pos = 0 #for keeping the positions gathered apart
        game = game.replace(']', '')
        while ("{" in game):
            game = game[0:game.find("{")] + game[game.find("}")+1:]

        game_split = game.split("[")[2:]
        date_string = game_split[0]
        white_string = game_split[2].replace("White", "").replace("\"", "").strip()
        black_string = game_split[3].replace("Black", "").replace("\"", "").strip()
        moves_and_link_split = game_split[18].split(" ")
            #use regular expressions to extract the link out of the moves and link
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, moves_and_link_split[1])
        link = urls[0].replace('\"', '') if urls else None

        #print(link)
        #print(moves_and_link_split)
            #move strings start at index 2 and occur in each third move (5, 8, etc.
        board = chess.Board()
        for i in range(2, min(2+6*40,len(moves_and_link_split)), 3):
            
            #print(moves_and_link_split[i])
            #print("i " + str(i))
            if len(board.piece_map().values())<15: break
                
            move = board.parse_san(moves_and_link_split[i])
            move_uci = move.uci()
            move_san = moves_and_link_split[i]
            
            if (i>2+6*15 and i>last_pos+20):
                stockfish.set_fen_position(board.fen())
                top3_moves = stockfish.get_top_moves(3)
                best_move = stockfish.get_best_move()
                best_move_obj = board.parse_uci(best_move)
                san_best_move = board.san(best_move_obj)
                #check to see if we want to use the position
                #print(top3_moves) #for debugging
                stockfish.make_moves_from_current_position([move_uci])
                eval = abs(stockfish.get_evaluation()['value'])
                eval_type = (stockfish.get_evaluation()['type'])
                if testpos(i, top3_moves, board, best_move, move_uci) and abs(top3_moves[0]['Centipawn'])>=eval+50 and eval_type=='cp':
                    last_pos=i
                    print("hey we got one")
                    #calculate the top 5 following stockfish moves
                    
                    board.push_uci(best_move)
                    stockfish.set_fen_position(board.fen())
                    stockfish_line = [{"uci": best_move, "san": san_best_move, "position": board.fen()}]
                    for _ in range(0,5):
                        best_move_now = stockfish.get_best_move()
                        best_move_now_obj = board.parse_uci(best_move_now)
                        best_move_now_san = board.san(best_move_now_obj)
                        board.push(best_move_now_obj)
                        stockfish.set_fen_position(board.fen())
                        stockfish_line.append({"uci": best_move_now, "san": best_move_now_san, "position": board.fen()})
                        
                    for _ in range(0,6):
                        board.pop()
                        
                    board.push_uci(move_uci)
                    stockfish.set_fen_position(board.fen())
                    gm_line = [{"uci": move_uci, "san": move_san, "position": board.fen()}]
                    for j in range(1,6):
                        gm_next_move_obj = None
                        gm_next_move_san = ""
                        if (i+j*3>=len(moves_and_link_split)):
                            gm_next_move_obj = board.parse_uci(stockfish.get_best_move())
                            gm_next_move_san = board.san(gm_next_move_obj)
                        else:
                            gm_next_move_obj = board.parse_san(moves_and_link_split[i+j*3])
                            gm_next_move_san = moves_and_link_split[i+j*3]
                        gm_move_uci = gm_next_move_obj.uci()
                        gm_move_san = gm_next_move_san
                        board.push_uci(gm_move_uci)
                        stockfish.set_fen_position(board.fen())
                        gm_line.append({"uci": gm_move_uci, "san": gm_move_san, "position": board.fen()})
                    for _ in range(0,6):
                        board.pop()
                        
                    pos_response={
                        "white_username": white_string,
                        "black_username": black_string,
                        "game_date": date_string,
                        "game_link": link,
                        "position": board.fen(),
                        "stockfish_move": {"uci": best_move, "san": san_best_move, "line": stockfish_line},
                        "gm_move": {"uci": move_uci, "san": move_san, "line": gm_line},
                        "hints": [],
                        "analysis": ""
                    }
                    gpt_result = gpt_call({"position": board.fen(), "stockfish_line": stockfish_line, "gm_line": gm_line}).split(":")
                    gpt_analysis = []
                    for i in range(1, len(gpt_result)):
                        gpt_analysis.append(gpt_result[i].strip())
                    gpt_analysis[5] = gpt_analysis[5].replace("Stockfish Line", "").strip()
                    for i in range(0,6):
                        pos_response["gm_move"]["line"][i]["analysis"]=gpt_analysis[i]
                    for i in range(0,6):
                        pos_response["stockfish_move"]["line"][i]["analysis"]=gpt_analysis[i+6]
                    pos_response["hints"] = gpt_analysis[12:15]
                    pos_response["analysis"] = gpt_analysis[15]
                    print(pos_response)
                    result.append(pos_response)
                    if (len(result)>=number): break
            
            #make the move
            board.push_uci(move_uci)
        if (len(result)>=number): return result
            
                
    return result
    
if __name__ == '__main__':
    app.run(debug=True)