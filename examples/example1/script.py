from puree.utils import recursive_search
def main(self, app):

    def hover_button_in(container):
        this_container = recursive_search(app.theme.root, container['id'])
        radial = this_container.children[1]
        radial.style.box_shadow_color = [.2, .8, .032, .165]
        radial.style.box_shadow_blur  = 20
        radial.mark_dirty() 

    def hover_button_out(container):
        this_container = recursive_search(app.theme.root, container['id'])
        radial = this_container.children[1]
        radial.style.box_shadow_color = [0, 0, 0, 0]
        radial.style.box_shadow_blur  = 0
        radial.mark_dirty()

    def click_button(container):
        this_container = recursive_search(app.theme.root, container['id'])
        radial = this_container.children[1]
        radial.style.box_shadow_color = [.2, .8, .032, .165]
        radial.style.box_shadow_blur  = 20
        radial.mark_dirty() 

    def toggle_button(container):
        this_container = recursive_search(app.theme.root, container['id'])
        radial = this_container.children[1]
        print(f"Toggle - Container: {container['id']}, Toggle: {container['_toggle_value']}, Radial: {radial.id}, Style Obj: {id(radial.style)}")

        if container['_toggle_value'] == True:
            radial.style.box_shadow_color = [.2, .8, .032, .165]
            radial.style.box_shadow_blur  = 20
            radial.mark_dirty() 
        else:
            radial.style.box_shadow_color = [0, 0, 0, 0]
            radial.style.box_shadow_blur  = 0
            radial.mark_dirty() 

    print(f"DEBUG: app.theme.root.id = {app.theme.root.id}")
    print(f"DEBUG: app.theme.root.children = {len(app.theme.root.children)}")
    if app.theme.root.children:
        for child in app.theme.root.children:
            print(f"  Child: {child.id}, has {len(child.children)} children")
    
    result = app.get_by_id("hover_test_button")
    print(f"DEBUG: get_by_id('hover_test_button') returned: {result}")
    if result:
        result.hover.append(hover_button_in)
    else:
        print("ERROR: Could not find hover_test_button!")
        app.theme.root.bg.hover_test_button.hover.append(hover_button_in)
    app.get_by_id("hover_test_button").hoverout.append(hover_button_out)
    app.get_by_id("click_test_button").click.append(click_button)
    app.get_by_id("toggle_test_button").toggle.append(toggle_button)

    return app
