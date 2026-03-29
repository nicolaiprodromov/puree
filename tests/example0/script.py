def main(self, app):
    root = app.theme.root
    sw = root.scroll_wrap

    click_count = [0]

    def on_click(container):
        click_count[0] += 1
        counter = sw.click_counter
        counter.text = f"Clicks: {click_count[0]}"
        counter.mark_dirty()

    sw.click_btn.click.append(on_click)

    def on_hover_in(container):
        status = sw.hover_status
        status.text = "Status: HOVERED"
        status.mark_dirty()

    def on_hover_out(container):
        status = sw.hover_status
        status.text = "Status: idle"
        status.mark_dirty()

    sw.hover_target.hover.append(on_hover_in)
    sw.hover_target.hoverout.append(on_hover_out)

    toggle_state = [False]

    def on_toggle(container):
        toggle_state[0] = not toggle_state[0]
        btn = sw.toggle_btn
        indicator = sw.toggle_indicator

        if toggle_state[0]:
            btn.text = "ON"
            btn.set_property("background-color", "rgba(46,204,113,0.2)")
            btn.set_property("border-color", "rgba(46,204,113,0.4)")
            btn.set_property("color", "rgba(46,204,113,1)")
            btn.mark_dirty()

            indicator.text = "Toggle state: ON"
            indicator.set_property("background-color", "rgba(46,204,113,0.1)")
            indicator.set_property("border-color", "rgba(46,204,113,0.3)")
            indicator.set_property("color", "rgba(46,204,113,1)")
            indicator.mark_dirty()
        else:
            btn.text = "OFF"
            btn.set_property("background-color", "rgba(155,89,182,0.2)")
            btn.set_property("border-color", "rgba(155,89,182,0.4)")
            btn.set_property("color", "rgba(155,89,182,1)")
            btn.mark_dirty()

            indicator.text = "Toggle state: OFF"
            indicator.set_property("background-color", "rgba(0,0,0,0)")
            indicator.set_property("border-color", "rgba(231,76,60,0.3)")
            indicator.set_property("color", "rgba(231,76,60,1)")
            indicator.mark_dirty()

    sw.toggle_btn.click.append(on_toggle)

    text_variants = [
        "Changed text #1",
        "Dynamic update!",
        "Runtime text swap",
        "mark_dirty() works!",
        "Another value",
    ]
    text_idx = [0]

    def on_change_text(container):
        target = sw.dyn_text_target
        target.text = text_variants[text_idx[0] % len(text_variants)]
        target.mark_dirty()
        text_idx[0] += 1

    sw.dyn_text_btn.click.append(on_change_text)

    style_toggled = [False]
    colors = [
        "rgba(52,152,219,0.25)",
        "rgba(46,204,113,0.25)",
        "rgba(231,76,60,0.25)",
        "rgba(155,89,182,0.25)",
    ]
    color_idx = [0]

    def on_toggle_style(container):
        target = sw.dyn_style_target
        target.set_property("background-color", colors[color_idx[0] % len(colors)])
        target.mark_dirty()
        color_idx[0] += 1

    sw.dyn_style_btn.click.append(on_toggle_style)

    visible = [True]

    def on_toggle_visibility(container):
        target = sw.dyn_showhide_target
        visible[0] = not visible[0]
        if visible[0]:
            target.style.display = "FLEX"
            target.text = "Now you see me"
        else:
            target.style.display = "NONE"
        target.mark_dirty()

    sw.dyn_showhide_btn.click.append(on_toggle_visibility)

    child_counter = [0]

    def on_add_child(container):
        child_counter[0] += 1
        parent = sw.dyn_children_container
        new_child = parent.add_child(
            "[test_card]",
            id=f"dyn_card_{child_counter[0]}",
            params={
                "card_title": f"Dynamic #{child_counter[0]}",
                "badge_text": "NEW",
                "badge_style": "tc_badge_pass",
                "card_content": f"Added at runtime (child {child_counter[0]})",
            },
        )
        new_child.mark_dirty()

    def on_clear_children(container):
        parent = sw.dyn_children_container
        parent.clear_children()
        parent.mark_dirty()

    sw.dyn_add_btn.click.append(on_add_child)
    sw.dyn_remove_btn.click.append(on_clear_children)

    behind_clicks = [0]

    def on_behind_click(container):
        behind_clicks[0] += 1
        label = sw.pointer_result
        label.text = f"Behind clicks: {behind_clicks[0]}"
        label.mark_dirty()

    sw.pointer_behind.click.append(on_behind_click)

    def on_scroll(container):
        offset = container._scroll_value
        label = sw.scroll_offset_label
        label.text = f"Scroll offset: {int(offset)}"
        label.mark_dirty()

    sw.scroll_area.scroll.append(on_scroll)

    return app
