def main(ui):
    def text_func(container):
        print("Button Clicked!")
    ui.theme.root.children[0].click.append(text_func)
    return ui