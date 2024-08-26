# Program for visualizing MicroMouse mazes
# USAGE: Set MAZE_SIZE to size of your maze; put maze file from the robot to the working directory of this script; launch this script

import tkinter

MAZE_SIZE = 6

canvas = tkinter.Canvas(width = 1000, height = 1000, bg = "white")
canvas.pack()

def DrawCell(positionX, positionY, cellSize, text: str, code = 0):
    if code & 1:
        canvas.create_line(positionX, positionY, positionX + cellSize + 2, positionY, width = 3)
    
    if code & 2:
        canvas.create_line(positionX + cellSize, positionY, positionX + cellSize, positionY + cellSize, width = 3)
    
    if code & 4:
        canvas.create_line(positionX, positionY + cellSize, positionX + cellSize + 2, positionY + cellSize, width = 3)
    
    if code & 8:
        canvas.create_line(positionX, positionY, positionX, positionY + cellSize, width = 3)

    canvas.create_text(positionX + cellSize / 2, positionY + cellSize / 2, text = text, font = "Ariel 30")

mazeFile = open("maze.txt")
maze = mazeFile.readlines()
mazeFile.close()

for i in range(MAZE_SIZE):
    splitMaze = maze[i].split()

    for j in range(MAZE_SIZE):
        DrawCell(200 + j * 100, 200 + i * 100, 100, str(splitMaze[j]), int(splitMaze[j]))

canvas.mainloop()
