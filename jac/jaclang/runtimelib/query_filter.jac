"""Query filter types for predicate pushdown.

These types represent structured predicates extracted from FilterCompr AST nodes
at runtime. They are database-agnostic — each storage backend (SQLite, MongoDB)
translates them to native query syntax.
"""

import from typing { Any }

"""Comparison operators for filter predicates."""
enum CompareOp {
    EQ = "eq",
    NE = "ne",
    LT = "lt",
    LE = "le",
    GT = "gt",
    GE = "ge",
    IN = "in",
    NOT_IN = "not_in"
}

"""A single field-level predicate extracted from a filter comprehension."""
obj Predicate {
    has field_name: str,
        op: CompareOp,
        value: Any;
}

"""A set of predicates that can be pushed down to the storage layer."""
obj QueryFilter {
    has type_name: (str | None) = None,
        predicates: list[Predicate] = [];
}
