def main(self, app):
    import bpy
    import json
    import math
    import os
    import threading

    # ─── Text input access ───
    try:
        from puree.text_input_op import _text_input_instances
    except ImportError:
        _text_input_instances = []

    # ─── Constants ───
    MAX_SLOTS = 15
    MODELS = [
        {"name": "Claude Sonnet", "api": "claude", "model": "claude-sonnet-4-20250514"},
        {"name": "Ollama llama3", "api": "ollama", "model": "llama3"},
    ]
    ACTIVE_CHAT_BG = "rgba(214, 163, 91, 0.12)"
    ACTIVE_CHAT_BORDER = "rgba(214, 163, 91, 0.24)"
    ROLE_STYLES = {
        "user": {
            "label": "You",
            "icon": "user",
            "slot_bg": "rgba(255, 255, 255, 0.025)",
            "slot_border": "rgba(255, 255, 255, 0.06)",
            "role_color": "rgba(205, 210, 220, 0.88)",
            "text_color": "rgba(240, 235, 227, 0.92)",
            "avatar_bg": "rgba(205, 210, 220, 0.08)",
            "avatar_border": "rgba(205, 210, 220, 0.16)",
            "avatar_opacity": 0.84,
        },
        "assistant": {
            "label": "Assistant",
            "icon": "star_on",
            "slot_bg": "rgba(214, 163, 91, 0.09)",
            "slot_border": "rgba(214, 163, 91, 0.18)",
            "role_color": "rgba(214, 163, 91, 0.96)",
            "text_color": "rgba(245, 237, 223, 0.96)",
            "avatar_bg": "rgba(214, 163, 91, 0.12)",
            "avatar_border": "rgba(214, 163, 91, 0.26)",
            "avatar_opacity": 0.96,
        },
    }

    # ─── Conversation state ───
    conversations = {}

    state = {
        "active_chat": None,
        "model_idx": 0,
        "waiting": False,
        "input_had_focus": False,
        "next_chat_num": 0,
    }

    # ─── Helpers ───
    def set_text(cid, value):
        el = app.get_by_id(cid)
        if el is None:
            return
        el.text = str(value)
        el.mark_dirty()

    def set_chat_selected(chat_id, selected):
        el = app.get_by_id(chat_id)
        if el is None:
            return
        if selected:
            el.set_property("background-color", ACTIVE_CHAT_BG)
            el.set_property("border-color", ACTIVE_CHAT_BORDER)
        else:
            el.set_property("background-color", "rgba(0, 0, 0, 0)")
            el.set_property("border-color", "rgba(0, 0, 0, 0)")

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
            inst._request_refresh()

    def calc_slot_height(text):
        chars_per_line = 36
        newlines = text.count("\n") + 1
        text_lines = max(1, math.ceil(len(text) / max(chars_per_line, 1)))
        total_lines = max(newlines, text_lines)
        text_h = max(28, int(total_lines * 20))
        return text_h + 52

    def apply_slot_role(slot, message):
        style = ROLE_STYLES.get(message.get("role", "user"), ROLE_STYLES["user"])
        slot.set_property("background-color", style["slot_bg"])
        slot.set_property("border-color", style["slot_border"])
        slot.set_property("border-width", "1px")
        slot.set_property("padding", "16px 16px 16px 16px")
        slot.set_property("opacity", 1.0)

        avatar = slot.get_by_id("msg_slot_avatar")
        if avatar is not None:
            avatar.img = style["icon"]
            avatar.set_property("background-color", style["avatar_bg"])
            avatar.set_property("border-color", style["avatar_border"])
            avatar.set_property("opacity", style["avatar_opacity"])
            avatar.mark_dirty()

        role_el = slot.get_by_id("msg_slot_role")
        if role_el is not None:
            role_el.text = style["label"]
            role_el.set_property("color", style["role_color"])
            role_el.mark_dirty()

        text_el = slot.get_by_id("msg_slot_text")
        if text_el is not None:
            text_el.set_property("color", style["text_color"])

    # ─── Slot management ───
    def show_slot(idx, message):
        slot_id = f"message_{idx}"
        slot = app.get_by_id(slot_id)
        if slot is None:
            return
        text = message.get("text", "")
        h = calc_slot_height(text)
        apply_slot_role(slot, message)
        slot.set_property("height", f"{h}px")
        slot.set_property("margin-bottom", "10px")
        slot.mark_dirty()
        avatar_el = slot.get_by_id("msg_slot_avatar")
        if avatar_el is not None:
            avatar_el.set_property("width", "24px")
            avatar_el.set_property("height", "24px")
            avatar_el.mark_dirty()
        role_el = slot.get_by_id("msg_slot_role")
        if role_el is not None:
            role_el.set_property("height", "18px")
            role_el.mark_dirty()
        text_el = slot.get_by_id("msg_slot_text")
        if text_el:
            text_h = max(28, h - 52)
            text_el.set_property("height", f"{text_h}px")
            text_el.text = text
            text_el.mark_dirty()

    def hide_slot(idx):
        slot_id = f"message_{idx}"
        slot = app.get_by_id(slot_id)
        if slot is None:
            return
        slot.set_property("height", "0px")
        slot.set_property("padding", "0px")
        slot.set_property("margin-bottom", "0px")
        slot.set_property("border-width", "0px")
        slot.set_property("opacity", 0.0)
        slot.mark_dirty()
        text_el = slot.get_by_id("msg_slot_text")
        if text_el is not None:
            text_el.text = " "
            text_el.set_property("height", "0px")
            text_el.mark_dirty()
        role_el = slot.get_by_id("msg_slot_role")
        if role_el is not None:
            role_el.text = " "
            role_el.set_property("height", "0px")
            role_el.mark_dirty()
        avatar_el = slot.get_by_id("msg_slot_avatar")
        if avatar_el is not None:
            avatar_el.set_property("width", "0px")
            avatar_el.set_property("height", "0px")
            avatar_el.set_property("opacity", 0.0)
            avatar_el.mark_dirty()

    def hide_all_slots():
        for i in range(MAX_SLOTS + 1):
            hide_slot(i)

    def render_conversation(chat_id):
        hide_all_slots()
        if chat_id not in conversations:
            return
        msgs = conversations[chat_id]["messages"]
        for i, msg in enumerate(msgs):
            if i > MAX_SLOTS:
                break
            show_slot(i, msg)
        set_text("header_title", conversations[chat_id]["title"])

    # ─── Home / Chat view toggle ───
    def show_home():
        home = app.get_by_id("home_page")
        if home:
            home.set_property("display", "FLEX")
            home.mark_dirty()
        for cid in ["main_header", "messages_scroll", "input_area"]:
            el = app.get_by_id(cid)
            if el:
                el.set_property("display", "NONE")
                el.mark_dirty()

    def show_chat():
        home = app.get_by_id("home_page")
        if home:
            home.set_property("display", "NONE")
            home.mark_dirty()
        for cid in ["main_header", "messages_scroll", "input_area"]:
            el = app.get_by_id(cid)
            if el:
                el.set_property("display", "FLEX")
                el.mark_dirty()

    # ─── Send message ───
    def send_message(text):
        if not text or state["waiting"]:
            return
        chat_id = state["active_chat"]
        if chat_id not in conversations:
            conversations[chat_id] = {"title": "New Chat", "messages": []}
        conv = conversations[chat_id]
        msg_idx = len(conv["messages"])
        if msg_idx > MAX_SLOTS:
            return
        conv["messages"].append({"role": "user", "text": text})
        show_slot(msg_idx, conv["messages"][msg_idx])
        clear_input()
        asst_idx = msg_idx + 1
        if asst_idx <= MAX_SLOTS:
            conv["messages"].append({"role": "assistant", "text": "Thinking..."})
            show_slot(asst_idx, conv["messages"][asst_idx])
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
                    show_slot(response_idx, conversations[chat_id]["messages"][response_idx])
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
            prev = state["active_chat"]
            if prev:
                set_chat_selected(prev, False)
            state["active_chat"] = chat_id
            set_chat_selected(chat_id, True)
            show_chat()
            render_conversation(chat_id)
        return handler

    for cid in conversations:
        el = app.get_by_id(cid)
        if el:
            el.click.append(make_chat_handler(cid))

    # ─── Sidebar slot management ───
    MAX_SIDEBAR_SLOTS = 6

    def hide_sidebar_slot(slot_id):
        el = app.get_by_id(slot_id)
        if el is None:
            return
        el.set_property("height", "0px")
        el.set_property("padding", "0px")
        el.set_property("border-width", "0px")
        el.set_property("opacity", 0.0)
        el.mark_dirty()
        icon = el.get_by_id("chat_item_icon")
        if icon:
            icon.set_property("width", "0px")
            icon.set_property("height", "0px")
            icon.set_property("opacity", 0.0)
            icon.img = ""
            icon.mark_dirty()
        title_el = el.get_by_id("chat_item_title")
        if title_el:
            title_el.text = " "
            title_el.set_property("height", "0px")
            title_el.mark_dirty()
        date_el = el.get_by_id("chat_item_date")
        if date_el:
            date_el.text = " "
            date_el.set_property("height", "0px")
            date_el.mark_dirty()

    def show_sidebar_slot(slot_id, title):
        el = app.get_by_id(slot_id)
        if el is None:
            return
        el.set_property("height", "60px")
        el.set_property("padding", "0px 12px")
        el.set_property("border-width", "1px")
        el.set_property("opacity", 1.0)
        el.mark_dirty()
        icon = el.get_by_id("chat_item_icon")
        if icon:
            icon.set_property("width", "34px")
            icon.set_property("height", "34px")
            icon.set_property("opacity", 0.74)
            icon.img = "star_on"
            icon.mark_dirty()
        title_el = el.get_by_id("chat_item_title")
        if title_el:
            title_el.text = title
            title_el.set_property("height", "20px")
            title_el.mark_dirty()
        date_el = el.get_by_id("chat_item_date")
        if date_el:
            date_el.text = "Now"
            date_el.set_property("height", "16px")
            date_el.mark_dirty()
        el.click.append(make_chat_handler(slot_id))

    def init_sidebar_slots():
        for i in range(0, MAX_SIDEBAR_SLOTS):
            hide_sidebar_slot(f"chat_slot_{i}")

    # ─── New chat ───
    def new_chat(container):
        num = state["next_chat_num"]
        if num >= MAX_SIDEBAR_SLOTS:
            return
        state["next_chat_num"] = num + 1
        slot_id = f"chat_slot_{num}"
        conversations[slot_id] = {"title": f"Chat {num + 1}", "messages": []}
        prev = state["active_chat"]
        if prev:
            set_chat_selected(prev, False)
        state["active_chat"] = slot_id
        show_sidebar_slot(slot_id, f"Chat {num + 1}")
        set_chat_selected(slot_id, True)
        show_chat()
        render_conversation(slot_id)

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
    init_sidebar_slots()
    hide_all_slots()
    show_home()

    # Wire home page start button
    home_btn = app.get_by_id("home_start_btn")
    if home_btn:
        home_btn.click.append(new_chat)

    return app
