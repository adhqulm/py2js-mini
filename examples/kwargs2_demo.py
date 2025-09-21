def paint(color, width=1, height=1, **meta):
    print("paint", color, width, height, meta)


opts = {"height": 5}
paint("red")
paint("blue", 3, **opts)
paint(color="green", width=2, **{"tag": "ui", "alpha": 0.5})
