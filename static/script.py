def main(self, app):
    def text_func(container):
        print("Button Hovered!")
    app.theme.root.children[0].children[1].children[0].hover.append(text_func)
    return app