def main(self, app):
    import bpy
    import json
    import os
    import threading

    # ─── Text input access ───
    try:
        from puree.text_input_op import _text_input_instances
    except ImportError:
        _text_input_instances = []

    # ─── Constants ───
    MAX_SLOTS = 15  # 15 pairs (30 slots total: 0-29)
    MODELS = [
        {"name": "Claude Sonnet", "api": "claude", "model": "claude-sonnet-4-20250514"},
        {"name": "Ollama llama3", "api": "ollama", "model": "llama3"},
    ]

    # ─── Conversation state ───
    conversations = {
        "chat_active": {
            "title": "Scene Optimization",
            "messages": [
                {"role": "user", "text": "Analyze my scene and suggest performance optimizations for viewport rendering."},
                {"role": "assistant", "text": "Found 8 high-poly meshes over 200k faces, 3 materials with 4+ texture layers, and a particle system generating 1.2M instances. Recommend starting with subdivision reduction."},
                {"role": "user", "text": "Apply subdivision reduction to all meshes over 100k faces. Keep the Cube at its current level."},
                {"role": "assistant", "text": "Done. Reduced subdivision on 8 meshes while preserving Cube. Scene is now at 890k vertices — viewport should feel significantly faster."},
            ],
        },
        "chat_materials": {
            "title": "Material Generator",
            "messages": [
                {"role": "user", "text": "Create a PBR metal material with scratches and wear."},
                {"role": "assistant", "text": "Setting up Principled BSDF: metallic=1.0, roughness map from procedural noise, scratch normal overlay via bump node. Want me to apply it to the selected object?"},
            ],
        },
        "chat_uvs": {"title": "UV Unwrap Helper", "messages": []},
        "chat_shaders": {"title": "Shader Debug", "messages": []},
        "chat_assets": {"title": "Asset Organizer", "messages": []},
        "chat_lighting": {"title": "Lighting Setup", "messages": []},
    }

    state = {
        "active_chat": "chat_active",
        "model_idx": 0,
        "waiting": False,
        "input_had_focus": False,
        "next_chat_num": 1,
    }

    # ─── Helpers ───
    def set_text(cid, value):
        el = app.get_by_id(cid)
        if el is None:
            return
        el.text = str(value)
        el.mark_dirty()

    def get_input_instance():
        for inst in _text_input_instances:
            if inst.container_id.endswith("input_field"):
                return inst
        return None

    def get_input_text():
        inst = get_input_instance()
        return inst.text.strip() if inst else ""

    def clear_input():
        inst = get_input_instance()
        if inst:
            inst.text = ""
            inst.cursor_pos = 0

    def calc_slot_height(text):
        chars_per_line = 30
        newlines = text.count("\n") + 1
        text_lines = max(1, len(text) / max(chars_per_line, 1))
        total_lines = max(newlines, text_lines)
        # 16px padding (8+8), 19px role (16h + 3mb), text at ~18px/line
        text_h = max(22, int(total_lines * 18))
        return text_h + 39  # 16 padding + 19 role area + 4 safety

    # ─── Slot management ───
    def show_slot(idx, text):
        slot_id = f"slot_{idx}"
        slot = app.get_by_id(slot_id)
        if slot is None:
            return
        h = calc_slot_height(text)
        slot.set_property("height", f"{h}px")
        slot.set_property("margin-bottom", "4px")
        text_el = slot.get_by_id("msg_slot_text")
        if text_el:
            # text height = total - padding(16) - role(16) - margin(3) - extra(4)
            text_h = max(22, h - 39)
            text_el.set_property("height", f"{text_h}px")
            text_el.text = text
            text_el.mark_dirty()

    def hide_slot(idx):
        slot_id = f"slot_{idx}"
        slot = app.get_by_id(slot_id)
        if slot is None:
            return
        slot.set_property("height", "0px")
        slot.set_property("margin-bottom", "0px")

    def hide_all_slots():
        for i in range(MAX_SLOTS * 2):
            hide_slot(i)

    def render_conversation(chat_id):
        hide_all_slots()
        if chat_id not in conversations:
            return
        msgs = conversations[chat_id]["messages"]
        for i, msg in enumerate(msgs):
            if i >= MAX_SLOTS * 2:
                break
            show_slot(i, msg["text"])
        set_text("header_title", conversations[chat_id]["title"])

    # ─── Send message ───
    def send_message(text):
        if not text or state["waiting"]:
            return
        chat_id = state["active_chat"]
        if chat_id not in conversations:
            conversations[chat_id] = {"title": "New Chat", "messages": []}
        conv = conversations[chat_id]
        msg_idx = len(conv["messages"])
        if msg_idx >= MAX_SLOTS * 2 - 1:
            return
        conv["messages"].append({"role": "user", "text": text})
        show_slot(msg_idx, text)
        clear_input()
        # Show thinking indicator in next slot
        asst_idx = msg_idx + 1
        if asst_idx < MAX_SLOTS * 2:
            conv["messages"].append({"role": "assistant", "text": "Thinking..."})
            show_slot(asst_idx, "Thinking...")
            state["waiting"] = True
            call_llm(chat_id, asst_idx)

    # ─── LLM API calls ───
    def call_llm(chat_id, response_idx):
        conv = conversations.get(chat_id, {})
        msgs = conv.get("messages", [])[:-1]  # Exclude the "Thinking..." placeholder
        api_messages = [{"role": m["role"], "content": m["text"]} for m in msgs]
        model_info = MODELS[state["model_idx"]]

        def on_response(text):
            def _update():
                if chat_id in conversations:
                    msgs_list = conversations[chat_id]["messages"]
                    if response_idx < len(msgs_list):
                        msgs_list[response_idx]["text"] = text
                if state["active_chat"] == chat_id:
                    show_slot(response_idx, text)
                state["waiting"] = False
                return None
            bpy.app.timers.register(_update)

        if model_info["api"] == "claude":
            _call_claude(api_messages, model_info["model"], on_response)
        else:
            _call_ollama(api_messages, model_info["model"], on_response)

    def _call_claude(messages, model, callback):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            callback("Set ANTHROPIC_API_KEY environment variable to use Claude.")
            return

        def _do():
            try:
                import urllib.request
                url = "https://api.anthropic.com/v1/messages"
                body = json.dumps({
                    "model": model,
                    "max_tokens": 1024,
                    "messages": messages,
                }).encode()
                req = urllib.request.Request(url, data=body, headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                })
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                    text = data["content"][0]["text"]
                    callback(text)
            except Exception as e:
                callback(f"Claude error: {e}")

        threading.Thread(target=_do, daemon=True).start()

    def _call_ollama(messages, model, callback):
        def _do():
            try:
                import urllib.request
                url = "http://localhost:11434/api/chat"
                body = json.dumps({
                    "model": model,
                    "messages": messages,
                    "stream": False,
                }).encode()
                req = urllib.request.Request(url, data=body, headers={
                    "Content-Type": "application/json",
                })
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                    text = data["message"]["content"]
                    callback(text)
            except Exception as e:
                callback(f"Ollama error: {e}")

        threading.Thread(target=_do, daemon=True).start()

    # ─── Send button handler ───
    def on_send_click(container):
        text = get_input_text()
        if text:
            send_message(text)

    send_btn = app.get_by_id("send_btn")
    if send_btn:
        send_btn.click.append(on_send_click)

    # ─── Enter-to-send via blur detection ───
    def check_blur_send():
        inst = get_input_instance()
        if inst is None:
            return 0.15
        currently_focused = inst.is_focused
        had_focus = state["input_had_focus"]
        state["input_had_focus"] = currently_focused
        if had_focus and not currently_focused:
            text = inst.text.strip()
            if text:
                def _do_send():
                    send_message(text)
                    return None
                bpy.app.timers.register(_do_send)
        return 0.15

    bpy.app.timers.register(check_blur_send)

    # ─── Model toggle ───
    def toggle_model(container):
        state["model_idx"] = (state["model_idx"] + 1) % len(MODELS)
        m = MODELS[state["model_idx"]]
        set_text("model_name", m["name"])
        dot = app.get_by_id("model_dot")
        if dot:
            if m["api"] == "claude":
                dot.set_property("background-color", "rgba(82, 200, 110, 0.92)")
                dot.set_property("box-shadow", "0px 0px 6px 2px rgba(82, 200, 110, 0.25)")
            else:
                dot.set_property("background-color", "rgba(238, 178, 62, 0.92)")
                dot.set_property("box-shadow", "0px 0px 6px 2px rgba(238, 178, 62, 0.25)")

    selector = app.get_by_id("model_selector")
    if selector:
        selector.click.append(toggle_model)

    # ─── Chat switching ───
    def make_chat_handler(chat_id):
        def handler(container):
            prev = app.get_by_id(state["active_chat"])
            if prev:
                prev.set_property("background-color", "rgba(0, 0, 0, 0)")
                prev.set_property("border-color", "rgba(0, 0, 0, 0)")
            state["active_chat"] = chat_id
            current = app.get_by_id(chat_id)
            if current:
                current.set_property("background-color", "rgba(88, 155, 240, 0.06)")
                current.set_property("border-color", "rgba(88, 155, 240, 0.12)")
            render_conversation(chat_id)
        return handler

    for cid in conversations:
        el = app.get_by_id(cid)
        if el:
            el.click.append(make_chat_handler(cid))

    # ─── New chat ───
    def new_chat(container):
        num = state["next_chat_num"]
        state["next_chat_num"] = num + 1
        new_id = f"_new_chat_{num}"
        conversations[new_id] = {"title": f"Chat {num}", "messages": []}
        # Deselect previous
        prev = app.get_by_id(state["active_chat"])
        if prev:
            prev.set_property("background-color", "rgba(0, 0, 0, 0)")
            prev.set_property("border-color", "rgba(0, 0, 0, 0)")
        state["active_chat"] = new_id
        render_conversation(new_id)

    new_btn = app.get_by_id("new_chat_btn")
    if new_btn:
        new_btn.click.append(new_chat)

    # ─── Attach buttons (placeholder: insert @reference in input) ───
    def attach_object(container):
        inst = get_input_instance()
        if inst:
            selected = [obj.name for obj in bpy.context.selected_objects]
            if selected:
                ref = ", ".join(f"@{name}" for name in selected)
                inst.insert_text(ref + " ")
            else:
                inst.insert_text("@")

    def attach_file(container):
        inst = get_input_instance()
        if inst:
            inst.insert_text("#file:")

    obj_btn = app.get_by_id("attach_obj_btn")
    if obj_btn:
        obj_btn.click.append(attach_object)

    file_btn = app.get_by_id("attach_file_btn")
    if file_btn:
        file_btn.click.append(attach_file)

    # ─── Initialize ───
    render_conversation("chat_active")

    return app
