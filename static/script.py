def main(self, app):
    def text_func(container):
        print("Button Hovered!")
        target_container = app.theme.root.bg.body
        target_container.style.color = [1.0, 1.0, 1.0, 1.0]
        target_container.mark_dirty()
        
    def text_func1(container):
        print("Button Hovered Out!")
        target_container = app.theme.root.bg.body
        target_container.style.color = [0.0, 0.0, 1.0, 1.0]
        target_container.mark_dirty()

    def text_func2(container):
        print("Button Clicked!")

    # app.theme.root.bg.body.buttons_test1.hover_test.hover.append(text_func)
    # app.theme.root.bg.body.buttons_test1.hover_test.hoverout.append(text_func1)
    app.theme.root.bg.body.buttons_test1.click_test.hover.append(text_func)
    app.theme.root.bg.body.buttons_test1.click_test.hoverout.append(text_func1)
    # app.theme.root.bg.body.buttons_test1.toggle_test.click.append(text_func2)
    return app