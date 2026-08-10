# Gomoku (Renju) - Pygame Board Game

A Python-based implementation of the classic Gomoku board game, built using the Pygame library. This project features both local PvP and a PvE mode against a custom-built AI.

**Developer Note:** This project was primarily an exercise in algorithmic thinking and working with graphical loops in Python. It lacks a strict Object-Oriented Programming (OOP) architecture, which I acknowledge as technical debt. It serves as a great learning milestone before transitioning to strictly typed, OOP-focused languages like C#.

## Technologies Used
* **Language:** Python
* **Libraries:** Pygame

## Features
* **Player vs Player (PvP):** Play locally with a friend, including a SWAP2 opening rule implementation[cite: 1].
* **Player vs Environment (PvE):** Play against the computer with 3 distinct difficulty levels[cite: 1].
* **Custom AI Logic:** The AI does not rely on external game engines. It uses a greedy algorithm and a custom heatmap-based scoring system to evaluate the board, rank potential moves, and block threats[cite: 1].
* **AI-Assisted Development:** Leveraged LLMs during the development process to brainstorm and optimize the mathematical evaluation logic for the AI.

## Future Updates
* No major updates planned. My current focus has shifted toward C# and .NET development.
