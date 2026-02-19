# type: ignore
from datetime import datetime

import pytest

from eventum.plugins.event.plugins.template.context import (
    EventContext,
    EventStateContext,
    EventTagsContext,
    EventTimestampContext,
)
from eventum.plugins.event.plugins.template.fsm.fields import (
    After,
    Always,
    And,
    Before,
    Contains,
    Defined,
    Eq,
    Ge,
    Gt,
    HasTags,
    In,
    Le,
    LenEq,
    LenGe,
    LenGt,
    LenLe,
    LenLt,
    Lt,
    Matches,
    Never,
    Not,
    Or,
    TimestampComponents,
)
from eventum.plugins.event.plugins.template.state import (
    SingleThreadState as State,
)


def test_eq():
    context = EventStateContext(
        locals=State({'field': 10}),
        shared=...,
        globals=...,
    )
    assert Eq(eq={'locals.field': 10}).check(context)
    assert not Eq(eq={'locals.field': 5}).check(context)
    assert not Eq(eq={'locals.other_field': 10}).check(context)


def test_gt():
    context = EventStateContext(
        locals=State({'field': 10}),
        shared=...,
        globals=...,
    )
    assert Gt(gt={'locals.field': 5}).check(context)
    assert not Gt(gt={'locals.field': 10}).check(context)
    assert not Gt(gt={'locals.field': 15}).check(context)


def test_ge():
    context = EventStateContext(
        locals=State({'field': 10}),
        shared=...,
        globals=...,
    )
    assert Ge(ge={'locals.field': 5}).check(context)
    assert Ge(ge={'locals.field': 10}).check(context)
    assert not Ge(ge={'locals.field': 15}).check(context)


def test_lt():
    context = EventStateContext(
        locals=State({'field': 10}),
        shared=...,
        globals=...,
    )
    assert Lt(lt={'locals.field': 15}).check(context)
    assert not Lt(lt={'locals.field': 10}).check(context)
    assert not Lt(lt={'locals.field': 5}).check(context)


def test_le():
    context = EventStateContext(
        locals=State({'field': 10}),
        shared=...,
        globals=...,
    )
    assert Le(le={'locals.field': 15}).check(context)
    assert Le(le={'locals.field': 10}).check(context)
    assert not Le(le={'locals.field': 5}).check(context)


def test_len_eq():
    context = EventStateContext(
        locals=State({'field': [1, 2, 3]}),
        shared=...,
        globals=...,
    )
    assert LenEq(len_eq={'locals.field': 3}).check(context)
    assert not LenEq(len_eq={'locals.field': 2}).check(context)


def test_len_gt():
    context = EventStateContext(
        locals=State({'field': [1, 2, 3]}),
        shared=...,
        globals=...,
    )
    assert LenGt(len_gt={'locals.field': 2}).check(context)
    assert not LenGt(len_gt={'locals.field': 3}).check(context)


def test_len_ge():
    context = EventStateContext(
        locals=State({'field': [1, 2, 3]}),
        shared=...,
        globals=...,
    )
    assert LenGe(len_ge={'locals.field': 2}).check(context)
    assert LenGe(len_ge={'locals.field': 3}).check(context)
    assert not LenGe(len_ge={'locals.field': 4}).check(context)


def test_len_lt():
    context = EventStateContext(
        locals=State({'field': [1, 2, 3]}),
        shared=...,
        globals=...,
    )
    assert LenLt(len_lt={'locals.field': 4}).check(context)
    assert not LenLt(len_lt={'locals.field': 3}).check(context)


def test_len_le():
    context = EventStateContext(
        locals=State({'field': [1, 2, 3]}),
        shared=...,
        globals=...,
    )
    assert LenLe(len_le={'locals.field': 4}).check(context)
    assert LenLe(len_le={'locals.field': 3}).check(context)
    assert not LenLe(len_le={'locals.field': 2}).check(context)


def test_contains():
    context = EventStateContext(
        locals=State({'field': [5, 10, 15]}),
        shared=...,
        globals=...,
    )
    assert Contains(contains={'locals.field': 10}).check(context)
    assert not Contains(contains={'locals.field': 2}).check(context)


def test_in():
    context = EventStateContext(
        locals=State({'field': 5}),
        shared=...,
        globals=...,
    )
    assert In(
        in_={'locals.field': [5, 10, 15]},
    ).check(context)
    assert not In(
        in_={'locals.field': [2, 4, 6]},
    ).check(context)


def test_has_tags():
    assert HasTags(has_tags='tag1').check(
        EventTagsContext(tags=('tag1', 'tag2')),
    )
    assert HasTags(has_tags=['tag1', 'tag2']).check(
        EventTagsContext(tags=('tag1', 'tag2', 'tag3')),
    )
    assert not HasTags(has_tags='tag3').check(
        EventTagsContext(tags=('tag1', 'tag2')),
    )


def test_before():
    context = EventTimestampContext(
        timestamp=datetime.fromisoformat('2023-10-27T10:30:20.500000Z'),
    )

    assert Before(
        before=TimestampComponents(year=2024),
    ).check(context)

    assert Before(
        before=TimestampComponents(month=11),
    ).check(context)

    assert Before(
        before=TimestampComponents(day=28),
    ).check(context)

    assert Before(
        before=TimestampComponents(hour=11),
    ).check(context)

    assert Before(
        before=TimestampComponents(minute=31),
    ).check(context)

    assert Before(
        before=TimestampComponents(second=21),
    ).check(context)

    assert Before(
        before=TimestampComponents(microsecond=600_000),
    ).check(context)

    assert Before(
        before=TimestampComponents(year=2023, month=11),
    ).check(context)

    assert Before(
        before=TimestampComponents(year=2023, month=10, day=28),
    ).check(context)

    assert Before(
        before=TimestampComponents(year=2023, month=10, day=27, hour=11),
    ).check(context)

    assert not Before(
        before=TimestampComponents(year=2023),
    ).check(context)

    assert not Before(
        before=TimestampComponents(month=10),
    ).check(context)

    assert not Before(
        before=TimestampComponents(day=27),
    ).check(context)

    assert not Before(
        before=TimestampComponents(hour=10),
    ).check(context)

    assert not Before(
        before=TimestampComponents(year=2022, month=12),
    ).check(context)

    assert not Before(
        before=TimestampComponents(year=2022, month=12, day=31),
    ).check(context)


def test_after():
    context = EventTimestampContext(
        timestamp=datetime.fromisoformat('2023-10-27T10:30:20.500000Z'),
    )

    assert After(
        after=TimestampComponents(year=2022),
    ).check(context)

    assert After(
        after=TimestampComponents(month=9),
    ).check(context)

    assert After(
        after=TimestampComponents(day=26),
    ).check(context)

    assert After(
        after=TimestampComponents(hour=9),
    ).check(context)

    assert After(
        after=TimestampComponents(minute=29),
    ).check(context)

    assert After(
        after=TimestampComponents(second=19),
    ).check(context)

    assert After(
        after=TimestampComponents(microsecond=400_000),
    ).check(context)

    assert After(
        after=TimestampComponents(year=2023),
    ).check(context)

    assert After(
        after=TimestampComponents(month=10),
    ).check(context)

    assert After(
        after=TimestampComponents(day=27),
    ).check(context)

    assert After(
        after=TimestampComponents(hour=10),
    ).check(context)

    assert After(
        after=TimestampComponents(year=2023, month=10),
    ).check(context)

    assert After(
        after=TimestampComponents(year=2023, month=10, day=27),
    ).check(context)

    assert After(
        after=TimestampComponents(year=2023, month=10, day=27, hour=10),
    ).check(context)

    assert not After(
        after=TimestampComponents(hour=11),
    ).check(context)

    assert not After(
        after=TimestampComponents(year=2023, month=10, day=27, hour=11),
    ).check(context)


def test_matches():
    context = EventStateContext(
        locals=State({'field': 'abc'}),
        shared=...,
        globals=...,
    )
    assert Matches(
        matches={'locals.field': r'^a.*c$'},
    ).check(context)
    assert not Matches(
        matches={'locals.field': r'^b.*c$'},
    ).check(context)


def test_defined():
    context = EventStateContext(
        locals=State({'field': 10}),
        shared=...,
        globals=...,
    )
    assert Defined(defined='locals.field').check(context)
    assert not Defined(defined='locals.other_field').check(context)


def test_or():
    context = EventContext(
        timestamp=...,
        tags=('tag1',),
        locals=State({'field': 10}),
        shared=...,
        globals=...,
    )

    assert Or(
        or_=[
            Eq(eq={'locals.field': 5}),
            HasTags(has_tags='tag1'),
        ],
    ).check(context)

    assert not Or(
        or_=[
            Eq(eq={'locals.field': 5}),
            HasTags(has_tags='tag2'),
        ],
    ).check(context)


def test_and():
    context = EventContext(
        timestamp=...,
        tags=('tag1',),
        locals=State({'field': 15}),
        shared=...,
        globals=...,
    )

    assert And(
        and_=[
            Gt(gt={'locals.field': 10}),
            HasTags(has_tags='tag1'),
        ],
    ).check(context)

    assert not And(
        and_=[
            Gt(gt={'locals.field': 10}),
            HasTags(has_tags='tag2'),
        ],
    ).check(context)


def test_not():
    context = EventContext(
        timestamp=...,
        tags=('tag1',),
        locals=State({'field': 5}),
        shared=...,
        globals=...,
    )

    assert Not(
        not_=Eq(
            eq={'locals.field': 10},
        ),
    ).check(context)
    assert not Not(
        not_=Eq(
            eq={'locals.field': 5},
        ),
    ).check(context)


def test_complex_condition():
    context = EventContext(
        timestamp=...,
        tags=('tag1',),
        locals=State({'field1': 10, 'field2': 'abc'}),
        shared=...,
        globals=...,
    )

    condition = Or(
        or_=[
            And(
                and_=[
                    Gt(gt={'locals.field1': 5}),
                    Lt(lt={'locals.field1': 15}),
                ],
            ),
            Not(
                not_=Matches(
                    matches={'locals.field2': r'^a.*c$'},
                ),
            ),
        ],
    )

    assert condition.check(context)


def test_invalid_timestamp_components():
    with pytest.raises(ValueError):
        TimestampComponents()


def test_always():
    context = EventContext(
        timestamp=...,
        tags=...,
        locals=...,
        shared=...,
        globals=...,
    )

    assert Always(always=None).check(context) is True


def test_never():
    context = EventContext(
        timestamp=...,
        tags=...,
        locals=...,
        shared=...,
        globals=...,
    )

    assert Never(never=None).check(context) is False
