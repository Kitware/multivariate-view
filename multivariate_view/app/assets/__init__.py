from trame.assets.local import LocalFileManager

ASSETS = LocalFileManager(__file__)
ASSETS.url("favicon", "./favicon.png")
