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
    button_2 = app.theme.root.button_2
    button_3 = app.theme.root.button_3

    def on_click(container):
        global _color_index
        _color_index = (_color_index + 1) % len(colors)
        base, hover = colors[_color_index]
        button.set_property("background-color", base)
        button.mark_dirty()
        console.log("Color changed to", base)

    def on_click_2(container):
        console.warn("Warning from button_2")

    def on_click_3(container):
        console.error("Error from button_3")

    button.click.append(on_click)
    button_2.click.append(on_click_2)
    button_3.click.append(on_click_3)
    return app
