import sys

from core import loader

if __name__ == "__main__":
    regenerate = "--regenerate" in sys.argv
    loader.build_database(progress=print, regenerate=regenerate)
