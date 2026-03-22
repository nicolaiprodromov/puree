def main(self, app):
    modes = {
        'overview': {
            'eyebrow': 'Declarative GPU UI',
            'heading': 'Interfaces with shader-grade polish.',
            'body': 'Puree brings layout, scoped styles, components, and runtime behavior into one clean authoring flow.',
            'status': 'Overview',
            'note': 'Switch modes to change the story and see live state updates.',
            'spotlight_title': 'Calm by default, dramatic on demand.',
            'spotlight_body': 'Use the spotlight toggle to intensify the atmosphere while keeping the layout intact.',
            'progress': '34%',
            'step': '01',
            'mode_tile': 'Base',
            'input_tile': 'Live',
        },
        'components': {
            'eyebrow': 'Reusable building blocks',
            'heading': 'Scoped components, tuned per instance.',
            'body': 'Each card, chip, tile, and field in this demo comes from reusable YAML and SCSS with local overrides.',
            'status': 'Components',
            'note': 'Component params let the same structure feel custom without duplicating the template.',
            'spotlight_title': 'Namespaced pieces stay elegant at scale.',
            'spotlight_body': 'The visual language shifts per instance while selectors remain contained and collision-free.',
            'progress': '67%',
            'step': '02',
            'mode_tile': 'Scoped',
            'input_tile': 'Param',
        },
        'runtime': {
            'eyebrow': 'Python in the loop',
            'heading': 'Runtime changes feel native to the layout.',
            'body': 'Interaction handlers can rewrite copy, widths, and presentation state without rebuilding the entire surface.',
            'status': 'Runtime',
            'note': 'This mode is driven from script.py, including text swaps and the live progress indicator.',
            'spotlight_title': 'State changes stay local and responsive.',
            'spotlight_body': 'Puree lets the script update targeted nodes instead of forcing a heavy redraw path everywhere.',
            'progress': '100%',
            'step': '03',
            'mode_tile': 'Live',
            'input_tile': 'State',
        },
    }

    state = {
        'mode_order': ['overview', 'components', 'runtime'],
        'mode': 'overview',
        'spotlight_on': False,
    }

    def set_text(container_id, value):
        target = app.get_by_id(container_id)
        if target is None:
            return
        target.text = value
        target.mark_dirty()

    def get_toggle_value(container):
        if isinstance(container, dict):
            return container.get('_toggle_value', False) is True
        return getattr(container, '_toggle_value', False) is True

    def update_spotlight_text():
        if state['spotlight_on']:
            set_text('spotlight_toggle_action_chip_label', 'Spotlight on')
            set_text('theme_tile_stat_tile_value', 'Glow')
        else:
            set_text('spotlight_toggle_action_chip_label', 'Spotlight off')
            set_text('theme_tile_stat_tile_value', 'Quiet')

    def apply_mode(mode_name):
        state['mode'] = mode_name
        mode = modes[mode_name]

        set_text('hero_eyebrow', mode['eyebrow'])
        set_text('hero_heading', mode['heading'])
        set_text('hero_body', mode['body'])
        set_text('status_value', mode['status'])
        set_text('composer_note', mode['note'])
        set_text('spotlight_title', mode['spotlight_title'])
        set_text('spotlight_body', mode['spotlight_body'])
        set_text('speed_tile_stat_tile_value', mode['step'])
        set_text('mode_tile_stat_tile_value', mode['mode_tile'])
        set_text('input_tile_stat_tile_value', mode['input_tile'])

        progress_fill = app.get_by_id('progress_fill')
        if progress_fill is not None:
            progress_fill.set_property('width', mode['progress'])

        footer = app.get_by_id('notes_input_input_shell_footer')
        if footer is not None:
            footer.text = f"Mode: {mode['status']} | Spotlight: {'on' if state['spotlight_on'] else 'off'}"
            footer.mark_dirty()

        update_spotlight_text()

    def cycle_story(container):
        current_index = state['mode_order'].index(state['mode'])
        next_index = (current_index + 1) % len(state['mode_order'])
        apply_mode(state['mode_order'][next_index])

    def enable_overview(container):
        apply_mode('overview')

    def enable_components(container):
        apply_mode('components')

    def enable_runtime(container):
        apply_mode('runtime')

    def toggle_spotlight(container):
        state['spotlight_on'] = get_toggle_value(container)

        if state['spotlight_on']:
            set_text('spotlight_title', 'The spotlight layer pushes the interface into showcase mode.')
            set_text('spotlight_body', 'Accent language becomes brighter and the story panel reads like a launch surface.')

            # Change atmosphere — intensify accent colors
            spotlight = app.get_by_id('spotlight_panel')
            if spotlight:
                spotlight.set_property('background-color', 'rgba(28, 16, 58, 0.98)')
                spotlight.set_property('--background-color-2', 'rgba(72, 32, 130, 0.96)')

            hero = app.get_by_id('hero_panel')
            if hero:
                hero.set_property('background-color', 'rgba(14, 20, 38, 0.98)')
                hero.set_property('--background-color-2', 'rgba(24, 52, 82, 0.96)')

            shell = app.get_by_id('shell')
            if shell:
                shell.set_property('background-color', 'rgba(10, 14, 28, 0.98)')
                shell.set_property('--background-color-2', 'rgba(16, 32, 52, 0.98)')
        else:
            # Restore calm atmosphere
            spotlight = app.get_by_id('spotlight_panel')
            if spotlight:
                spotlight.set_property('background-color', 'rgba(16, 16, 30, 0.94)')
                spotlight.set_property('--background-color-2', 'rgba(46, 25, 82, 0.92)')

            hero = app.get_by_id('hero_panel')
            if hero:
                hero.set_property('background-color', 'rgba(13, 18, 29, 0.96)')
                hero.set_property('--background-color-2', 'rgba(17, 39, 60, 0.9)')

            shell = app.get_by_id('shell')
            if shell:
                shell.set_property('background-color', 'rgba(8, 12, 22, 0.95)')
                shell.set_property('--background-color-2', 'rgba(11, 26, 41, 0.98)')

            apply_mode(state['mode'])
            return

        footer = app.get_by_id('notes_input_input_shell_footer')
        if footer is not None:
            footer.text = f"Mode: {modes[state['mode']]['status']} | Spotlight: on"
            footer.mark_dirty()

        update_spotlight_text()

    app.get_by_id('cycle_story').click.append(cycle_story)
    app.get_by_id('nav_overview').click.append(enable_overview)
    app.get_by_id('nav_components').click.append(enable_components)
    app.get_by_id('nav_runtime').click.append(enable_runtime)
    app.get_by_id('spotlight_toggle').toggle.append(toggle_spotlight)

    apply_mode(state['mode'])
    return app