def produce(params: dict) -> str:
    state = params['globals']

    count = state.get('count', 0) + 1
    state.set('count', count)

    return f'{state.get("prefix", "event")} {count}'
