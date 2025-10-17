from puree.utils import recursive_search
def main(self, app):

    radial_focus        = [.2, .8, .032, .165]
    radial_neutral      = [0, 0, 0, 0]
    radial_blur_focus   = 13
    radial_blur_neutral = 0

    def hover_button_in(container):
        this_container = recursive_search(app.theme.root, container['id'])
        radial = this_container.children[2]
        radial.style.box_shadow_color = radial_focus
        radial.style.box_shadow_blur  = radial_blur_focus
        radial.mark_dirty() 

    def hover_button_out(container):
        this_container = recursive_search(app.theme.root, container['id'])
        radial = this_container.children[2]
        radial.style.box_shadow_color = radial_neutral
        radial.style.box_shadow_blur  = radial_blur_neutral
        radial.mark_dirty()

    def click_button(container):
        this_container = recursive_search(app.theme.root, container['id'])
        radial = this_container.children[2]
        radial.style.box_shadow_color = radial_focus
        radial.style.box_shadow_blur  = radial_blur_focus
        radial.mark_dirty() 

    def toggle_button(container):
        this_container = recursive_search(app.theme.root, container['id'])
        radial = this_container.children[2]
        print(f"Toggle - Container: {container['id']}, Toggle: {container['_toggle_value']}, Radial: {radial.id}, Style Obj: {id(radial.style)}")

        if container['_toggle_value'] == True:
            radial.style.box_shadow_color = radial_focus
            radial.style.box_shadow_blur  = radial_blur_focus
            radial.mark_dirty() 
        else:
            radial.style.box_shadow_color = radial_neutral
            radial.style.box_shadow_blur  = radial_blur_neutral
            radial.mark_dirty() 

    app.get_by_id("hover_test_button").hover.append(hover_button_in)
    app.get_by_id("hover_test_button").hoverout.append(hover_button_out)
    app.get_by_id("click_test_button").click.append(click_button)
    app.get_by_id("toggle_test_button").toggle.append(toggle_button)

    return app
