def main(self, app):

    # ─── State ───
    models = ['Claude 3.5 Sonnet', 'Ollama · llama3']
    state = {
        'model_idx': 0,
        'active_chat': 'chat_active',
    }

    chat_data = {
        'chat_active':    {'title': 'Scene Optimization',  'sub': 'Analyzing viewport performance'},
        'chat_materials': {'title': 'Material Generator',  'sub': 'PBR material creation'},
        'chat_uvs':       {'title': 'UV Unwrap Helper',    'sub': 'Automatic UV unwrapping'},
        'chat_shaders':   {'title': 'Shader Debug',        'sub': 'Node tree debugging'},
        'chat_assets':    {'title': 'Asset Organizer',     'sub': 'Scene organization'},
        'chat_lighting':  {'title': 'Lighting Setup',      'sub': 'Three-point lighting'},
    }

    # ─── Helpers ───
    def set_text(container_id, value):
        el = app.get_by_id(container_id)
        if el is None:
            return
        el.text = value
        el.mark_dirty()

    # ─── Model Toggle ───
    def toggle_model(container):
        state['model_idx'] = (state['model_idx'] + 1) % 2
        name = models[state['model_idx']]
        set_text('model_name', name)

        dot = app.get_by_id('model_dot')
        if dot:
            if state['model_idx'] == 0:
                dot.set_property('background-color', 'rgba(82, 200, 110, 0.92)')
                dot.set_property('box-shadow', '0px 0px 6px 2px rgba(82, 200, 110, 0.3)')
            else:
                dot.set_property('background-color', 'rgba(238, 178, 62, 0.92)')
                dot.set_property('box-shadow', '0px 0px 6px 2px rgba(238, 178, 62, 0.3)')

    selector = app.get_by_id('model_selector')
    if selector:
        selector.click.append(toggle_model)

    # ─── Chat Switching ───
    def make_chat_handler(chat_id):
        def handler(container):
            prev = app.get_by_id(state['active_chat'])
            if prev:
                prev.set_property('background-color', 'rgba(0, 0, 0, 0)')
                prev.set_property('border-color', 'rgba(0, 0, 0, 0)')

            state['active_chat'] = chat_id

            current = app.get_by_id(chat_id)
            if current:
                current.set_property('background-color', 'rgba(88, 155, 240, 0.06)')
                current.set_property('border-color', 'rgba(88, 155, 240, 0.12)')

            if chat_id in chat_data:
                set_text('header_title', chat_data[chat_id]['title'])
                set_text('header_subtitle', chat_data[chat_id]['sub'])

        return handler

    for chat_id in chat_data:
        el = app.get_by_id(chat_id)
        if el:
            el.click.append(make_chat_handler(chat_id))

    # ─── New Chat ───
    def new_chat(container):
        set_text('header_title', 'New Chat')
        set_text('header_subtitle', 'Start a conversation')

    new_btn = app.get_by_id('new_chat_btn')
    if new_btn:
        new_btn.click.append(new_chat)

    # ─── Suggestion Chips ───
    sug_prompts = {
        'sug_analyze':  'Analyze the current scene for issues',
        'sug_material': 'Generate a PBR material for metal',
        'sug_uv':       'Fix UV mapping on selected objects',
        'sug_script':   'Write a script to batch rename objects',
        'sug_render':   'Optimize render settings for speed',
    }

    def make_sug_handler(prompt):
        def handler(container):
            set_text('header_subtitle', prompt)
        return handler

    for sug_id, prompt in sug_prompts.items():
        el = app.get_by_id(sug_id)
        if el:
            el.click.append(make_sug_handler(prompt))

    return app
