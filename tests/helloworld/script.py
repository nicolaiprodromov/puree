colors = [
    ("#3498db", "#2980b9"),  # blue, darker blue
    ("#e74c3c", "#c0392b"),  # red, darker red
    ("#2ecc71", "#27ae60"),  # green, darker green
    ("#f39c12", "#e67e22"),  # orange, darker orange
    ("#9b59b6", "#8e44ad"),  # purple, darker purple
]

_color_index = 0


def main(self, app):
    button = app.theme.root.button

    def on_click(container):
        global _color_index
        _color_index = (_color_index + 1) % len(colors)
        base, hover = colors[_color_index]
        button.set_property("background-color", base)
        button.mark_dirty()

    button.click.append(on_click)
    return app
