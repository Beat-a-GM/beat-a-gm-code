import numpy as np
def array_reverse(arr: np.array):
    arr_copy = np.zeros((8, 8))
    for i in range(0, 64):
        row = i // 8
        #0,7  1,6  2,5  3,4
        new_row = 7-row
        arr_copy[new_row, i % 8] = arr[row, i % 8]
    return arr_copy
def board_array_reverse(arr: np.array): #array represents the board
    arr_copy = array_reverse(arr)
    for i in range(0, 64):
        arr_copy[i // 8, i % 8] = arr_copy[i // 8, i % 8] * -1
    return arr_copy
    