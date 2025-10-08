def main(self, app):
    def text_func(container):
        print("Button Hovered!")
        # Get the target container using property-based access
        target_container = app.theme.root.bg.body
        # Modify its color
        target_container.style.color = [1.0, 1.0, 1.0, 1.0]  # White in linear space
        # Mark it as dirty so the GPU buffer gets updated
        target_container.mark_dirty()
        
    def text_func1(container):
        print("Button Hovered Out!")
        # Get the target container using property-based access
        target_container = app.theme.root.bg.body
        # Modify its color
        target_container.style.color = [0.0, 0.0, 1.0, 1.0]  # Blue in linear space
        # Mark it as dirty so the GPU buffer gets updated
        target_container.mark_dirty()

    # Use property-based access instead of index-based access
    # Old way: app.theme.root.children[0].children[2].children[0].children[0]
    # New way: app.theme.root.bg.body.buttons_test1.hover_test.ht_text
    app.theme.root.bg.body.buttons_test1.hover_test.hover.append(text_func)
    app.theme.root.bg.body.buttons_test1.hover_test.hoverout.append(text_func1)
    app.theme.root.bg.body.buttons_test1.click_test.hover.append(text_func)
    app.theme.root.bg.body.buttons_test1.click_test.hoverout.append(text_func1)
    return app