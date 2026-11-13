#!/usr/bin/env python
"""Ninjavenge - a lane-defense ninja game. Run: python main.py"""
from ninjavenge.app import App
from ninjavenge.scenes import MenuScene


def main():
    app = App()
    app.run(MenuScene(app))


if __name__ == "__main__":
    main()
