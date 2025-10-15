def main(self, app):
    counter = [0]
    
    def hover_handler(container):
        title = app.theme.root.header.text_box.text
        title.text = "Hovering!"
        title.mark_dirty()
        
    def hover_out_handler(container):
        title = app.theme.root.header.text_box.text
        title.text = "Puree UI Showcase"
        title.mark_dirty()
    
    def click_handler(container):
        title = app.theme.root.header.text_box.text
        title.text = "Clicked!"
        title.mark_dirty()
    
    def toggle_handler(container):
        title = app.theme.root.header.text_box.text
        if container._toggle_value:
            title.text = "Toggled ON"
        else:
            title.text = "Toggled OFF"
        title.mark_dirty()
    
    return app
