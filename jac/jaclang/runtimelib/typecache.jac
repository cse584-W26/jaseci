def get_field_types(cls: type) -> dict[str, object];

def field_names(cls: type) -> tuple;

def emit_plan(cls: type) -> tuple;

def emit_plan_map(cls: type) -> dict;

def warm(cls: type) -> None;

def invalidate(cls: type) -> None;

def clear -> None;
