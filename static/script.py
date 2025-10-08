def main(self, app):
    def text_func(container):
        print("Button Hovered!")
        # Get the target container (first child of root)
        target_container = app.theme.root.children[0].children[2]
        # Modify its color
        target_container.style.color = [1.0, 1.0, 1.0, 1.0]  # White in linear space
        # Mark it as dirty so the GPU buffer gets updated
        target_container.mark_dirty()
        
    def text_func1(container):
        print("Button Hovered Out!")
        # Get the target container (first child of root)
        target_container = app.theme.root.children[0].children[2]
        # Modify its color
        target_container.style.color = [0.0, 0.0, 1.0, 1.0]  # Blue in linear space
        # Mark it as dirty so the GPU buffer gets updated
        target_container.mark_dirty()


    app.theme.root.children[0].children[2].children[0].children[0].hover.append(text_func)
    app.theme.root.children[0].children[2].children[0].children[0].hoverout.append(text_func1)
    app.theme.root.children[0].children[2].children[0].children[1].hover.append(text_func)
    app.theme.root.children[0].children[2].children[0].children[1].hoverout.append(text_func1)
    return app