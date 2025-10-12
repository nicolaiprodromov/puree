def recursive_search(container, target_id):
    if container.id == target_id:
        return container
    for child in container.children:
        result = recursive_search(child, target_id)
        if result:
            return result
    return None