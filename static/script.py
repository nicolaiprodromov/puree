from puree.utils import recursive_search

def main(self, app):
    def test_handler(container):
        print("Button Hovered!")
        target_container            = app.theme.root.bg.bottom_text_box.bottom_text_box_title
        target_container.text       = "Changed text on hover!"
        target_container.text_scale = 67
        target_container.mark_dirty()
        
    def test_handler1(container):
        print("Button Hovered Out!")
        target_container            = app.theme.root.bg.bottom_text_box.bottom_text_box_title
        target_container.text       = "PUREE UI Kit by xwz"
        target_container.text_scale = 75
        target_container.mark_dirty()

    def test_handler2(container):
        print("Button Clicked!")
        target_container            = app.theme.root.bg.bottom_text_box.bottom_text_box_title
        target_container.text       = "Changed text on click!"
        target_container.text_scale = 67
        target_container.mark_dirty()

    def test_handler3(container):
        target_container = app.theme.root.bg.bottom_text_box.bottom_text_box_title
        toggle_container = recursive_search(app.theme.root, container['id'])
        if toggle_container:
            if container['_toggle_value'] == True:
                print("Toggled On")
                target_container.text       = "Changed text on toggle!"
                target_container.text_scale = 67
                toggle_container.color      = [0.0, 1.0, 0.0, 1.0]
            else:
                print("Toggled Off")
                target_container.text       = "PUREE UI Kit by xwz"
                target_container.text_scale = 75
                toggle_container.color      = [1.0, 0.0, 0.0, 1.0]
            target_container.mark_dirty()
            toggle_container.mark_dirty()

    app.theme.root.bg.top_box.left_box.left_top_box.left_top_box_box.ht.hover.append(test_handler)
    app.theme.root.bg.top_box.left_box.left_top_box.left_top_box_box.ht.hoverout.append(test_handler1)
    app.theme.root.bg.top_box.left_box.left_top_box.middle_top_box.ct.click.append(test_handler2)
    app.theme.root.bg.top_box.left_box.left_bottom_box.tgt.toggle.append(test_handler3)
    return app