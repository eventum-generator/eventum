from pathlib import Path

import pytest

from eventum.plugins.event.plugins.template.config import (
    CSVSampleConfig,
    ItemsSampleConfig,
    JSONSampleConfig,
    SampleConfig,
    SampleType,
)
from eventum.plugins.event.plugins.template.sample_reader import (
    Row,
    Sample,
    SampleLoadError,
    SamplePickError,
    SamplesReader,
)

BASE_PATH = Path(__file__).parent


@pytest.fixture
def items_sample_config():
    return {
        'items_sample': SampleConfig(
            root=ItemsSampleConfig(
                type=SampleType.ITEMS,
                source=(('one', 'two'), ('three', 'four')),
            )
        )
    }


@pytest.fixture
def flat_items_sample_config():
    return {
        'items_sample': SampleConfig(
            root=ItemsSampleConfig(type=SampleType.ITEMS, source=(1, 2, 3))
        )
    }


@pytest.fixture
def csv_sample_config():
    return {
        'csv_sample': SampleConfig(
            root=CSVSampleConfig(
                type=SampleType.CSV,
                source=BASE_PATH / 'static/sample.csv',
                header=True,
                delimiter=',',
            )
        )
    }


@pytest.fixture
def no_header_csv_sample_config():
    return {
        'csv_sample': SampleConfig(
            root=CSVSampleConfig(
                type=SampleType.CSV,
                source=BASE_PATH / 'static/sample.csv',
                header=False,
                delimiter=',',
            )
        )
    }


@pytest.fixture
def not_existing_csv_sample_config():
    return {
        'csv_sample': SampleConfig(
            root=CSVSampleConfig(
                type=SampleType.CSV,
                source=BASE_PATH / 'static/not_existing.csv',
                header=True,
                delimiter=',',
            )
        )
    }


@pytest.fixture
def other_delimiter_csv_sample_config():
    return {
        'csv_sample': SampleConfig(
            root=CSVSampleConfig(
                type=SampleType.CSV,
                source=BASE_PATH / 'static/piped_sample.csv',
                header=True,
                delimiter='|',
            )
        )
    }


@pytest.fixture
def json_sample_config():
    return {
        'json_sample': SampleConfig(
            root=JSONSampleConfig(
                type=SampleType.JSON,
                source=BASE_PATH / 'static/sample.json',
            )
        )
    }


@pytest.fixture
def nested_json_sample_config():
    return {
        'json_sample': SampleConfig(
            root=JSONSampleConfig(
                type=SampleType.JSON,
                source=BASE_PATH / 'static/nested_sample.json',
            )
        )
    }


@pytest.fixture
def heterogeneous_json_sample_config():
    return {
        'json_sample': SampleConfig(
            root=JSONSampleConfig(
                type=SampleType.JSON,
                source=BASE_PATH / 'static/heterogeneous_sample.json',
            )
        )
    }


@pytest.fixture
def weighted_csv_sample_config():
    return {
        'weighted_csv': SampleConfig(
            root=CSVSampleConfig(
                type=SampleType.CSV,
                source=BASE_PATH / 'static/weighted_sample.csv',
                header=True,
                delimiter=',',
            )
        )
    }


@pytest.fixture
def weighted_json_sample_config():
    return {
        'weighted_json': SampleConfig(
            root=JSONSampleConfig(
                type=SampleType.JSON,
                source=BASE_PATH / 'static/weighted_sample.json',
            )
        )
    }


@pytest.fixture
def bad_weights_csv_sample_config():
    return {
        'bad_weights': SampleConfig(
            root=CSVSampleConfig(
                type=SampleType.CSV,
                source=BASE_PATH / 'static/bad_weights_sample.csv',
                header=True,
                delimiter=',',
            )
        )
    }


@pytest.fixture
def quoted_csv_sample_config():
    return {
        'csv_sample': SampleConfig(
            root=CSVSampleConfig(
                type=SampleType.CSV,
                source=BASE_PATH / 'static/quoted_sample.csv',
                header=True,
                delimiter=',',
            )
        )
    }


@pytest.fixture
def unquoted_commas_csv_sample_config():
    return {
        'csv_sample': SampleConfig(
            root=CSVSampleConfig(
                type=SampleType.CSV,
                source=BASE_PATH / 'static/unquoted_commas_sample.csv',
                header=True,
                delimiter=',',
            )
        )
    }


# --- Row class tests ---


def test_row_tuple_equality():
    row = Row(('a', 'b', 'c'), {'x': 0, 'y': 1, 'z': 2})
    assert row == ('a', 'b', 'c')


def test_row_named_access():
    row = Row(('a', 'b'), {'x': 0, 'y': 1})
    assert row.x == 'a'
    assert row.y == 'b'


def test_row_index_access():
    row = Row(('a', 'b'), {'x': 0, 'y': 1})
    assert row[0] == 'a'
    assert row[1] == 'b'


def test_row_numeric_field_access():
    row = Row(('a', 'b'), {'_0': 0, '_1': 1})
    assert row._0 == 'a'
    assert row._1 == 'b'


def test_row_missing_attr_raises():
    row = Row(('a',), {'x': 0})
    with pytest.raises(AttributeError):
        row.missing  # noqa: B018


def test_row_repr_with_fields():
    row = Row(('a', 'b'), {'x': 0, 'y': 1})
    assert repr(row) == "Row(x='a', y='b')"


def test_row_repr_without_fields():
    row = Row(('a', 'b'))
    assert repr(row) == "Row(('a', 'b'))"


def test_row_is_tuple():
    row = Row(('a', 'b'), {'x': 0, 'y': 1})
    assert isinstance(row, tuple)


def test_row_iteration():
    row = Row(('a', 'b', 'c'), {'x': 0, 'y': 1, 'z': 2})
    assert list(row) == ['a', 'b', 'c']


def test_row_len():
    row = Row(('a', 'b', 'c'))
    assert len(row) == 3


# --- Sample loading tests ---


def test_load_items_sample(items_sample_config):
    sample_reader = SamplesReader(items_sample_config, BASE_PATH)
    sample = sample_reader['items_sample']

    assert isinstance(sample, Sample)
    assert sample[0] == ('one', 'two')
    assert sample[1] == ('three', 'four')


def test_load_flat_items_sample(flat_items_sample_config):
    sample_reader = SamplesReader(flat_items_sample_config, BASE_PATH)
    sample = sample_reader['items_sample']

    assert isinstance(sample, Sample)
    assert sample[0] == (1,)
    assert sample[1] == (2,)
    assert sample[2] == (3,)


def test_load_csv_sample(csv_sample_config):
    sample_reader = SamplesReader(csv_sample_config, BASE_PATH)
    sample = sample_reader['csv_sample']

    assert isinstance(sample, Sample)
    assert sample[0] == ('John', 'john@example.com', 'Manager')
    assert sample[1] == ('Jane', 'jane@example.com', 'HR')


def test_load_csv_sample_with_wrong_path(not_existing_csv_sample_config):
    with pytest.raises(SampleLoadError):
        SamplesReader(not_existing_csv_sample_config, BASE_PATH)


def test_load_csv_sample_with_other_delimiter(
    other_delimiter_csv_sample_config,
):
    sample_reader = SamplesReader(other_delimiter_csv_sample_config, BASE_PATH)

    sample = sample_reader['csv_sample']
    assert sample[0] == ('John', 'john@example.com', 'Manager')
    assert sample[1] == ('Jane', 'jane@example.com', 'HR')


def test_load_csv_sample_without_header(no_header_csv_sample_config):
    sample_reader = SamplesReader(no_header_csv_sample_config, BASE_PATH)
    sample = sample_reader['csv_sample']

    assert sample[0] == ('name', 'email', 'position')
    assert sample[1] == ('John', 'john@example.com', 'Manager')
    assert sample[2] == ('Jane', 'jane@example.com', 'HR')


def test_load_json_sample(json_sample_config):
    sample_reader = SamplesReader(json_sample_config, BASE_PATH)
    sample = sample_reader['json_sample']

    assert isinstance(sample, Sample)
    assert sample[0] == ('John', 'john@example.com', 'Manager')
    assert sample[1] == ('Jane', 'jane@example.com', 'HR')


def test_load_nested_json_sample(nested_json_sample_config):
    sample_reader = SamplesReader(nested_json_sample_config, BASE_PATH)
    sample = sample_reader['json_sample']

    assert isinstance(sample, Sample)
    assert sample[0] == (
        {'firstname': 'John', 'lastname': 'Doe'},
        ['john@example.com', 'john.public@example.com'],
        'Manager',
    )
    assert sample[1] == (
        {'firstname': 'Jane', 'lastname': 'Doe'},
        ['jane@example.com', 'jane.public@example.com'],
        'HR',
    )


def test_csv_sample_named_access(csv_sample_config):
    sample_reader = SamplesReader(csv_sample_config, BASE_PATH)
    sample = sample_reader['csv_sample']

    row = sample[0]
    assert isinstance(row, Row)
    assert row.name == 'John'
    assert row.email == 'john@example.com'
    assert row.position == 'Manager'

    # Index access still works alongside named access
    assert row[0] == 'John'
    assert row[1] == 'john@example.com'
    assert row[2] == 'Manager'


def test_json_sample_named_access(json_sample_config):
    sample_reader = SamplesReader(json_sample_config, BASE_PATH)
    sample = sample_reader['json_sample']

    row = sample[0]
    assert isinstance(row, Row)
    assert row.name == 'John'
    assert row.email == 'john@example.com'
    assert row.position == 'Manager'

    # Index access still works alongside named access
    assert row[0] == 'John'
    assert row[1] == 'john@example.com'
    assert row[2] == 'Manager'


def test_csv_sample_without_header_numeric_access(
    no_header_csv_sample_config,
):
    sample_reader = SamplesReader(no_header_csv_sample_config, BASE_PATH)
    sample = sample_reader['csv_sample']

    row = sample[0]
    assert row._0 == 'name'
    assert row._1 == 'email'
    assert row._2 == 'position'

    # Index access still works alongside numeric named access
    assert row[0] == 'name'
    assert row[1] == 'email'
    assert row[2] == 'position'


def test_items_sample_numeric_access(items_sample_config):
    sample_reader = SamplesReader(items_sample_config, BASE_PATH)
    sample = sample_reader['items_sample']

    row = sample[0]
    assert row._0 == 'one'
    assert row._1 == 'two'

    # Index access still works alongside numeric named access
    assert row[0] == 'one'
    assert row[1] == 'two'


def test_load_heterogeneous_json_sample_raises(
    heterogeneous_json_sample_config,
):
    with pytest.raises(SampleLoadError, match='inconsistent keys'):
        SamplesReader(heterogeneous_json_sample_config, BASE_PATH)


def test_missing_samples(items_sample_config):
    sample_reader = SamplesReader(items_sample_config, BASE_PATH)
    with pytest.raises(KeyError):
        sample_reader['missing_samples']


def test_load_csv_sample_with_quoted_commas(quoted_csv_sample_config):
    """RFC 4180: quoted fields containing commas are parsed correctly."""
    sample_reader = SamplesReader(quoted_csv_sample_config, BASE_PATH)
    sample = sample_reader['csv_sample']

    assert len(sample) == 3

    row = sample[0]
    assert row.user_agent == (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
    assert row.category == 'browser'

    row = sample[1]
    assert row.user_agent == (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
    )
    assert row.category == 'browser'

    row = sample[2]
    assert row.user_agent == 'Simple-Agent'
    assert row.category == 'bot'


def test_load_csv_sample_with_unquoted_commas_raises(
    unquoted_commas_csv_sample_config,
):
    """Unquoted fields with commas produce a helpful error."""
    with pytest.raises(SampleLoadError, match='inconsistent column counts'):
        SamplesReader(unquoted_commas_csv_sample_config, BASE_PATH)


# --- Picking tests ---


def test_pick_returns_valid_row(csv_sample_config):
    sample_reader = SamplesReader(csv_sample_config, BASE_PATH)
    sample = sample_reader['csv_sample']

    row = sample.pick()
    assert isinstance(row, Row)
    assert row in (
        ('John', 'john@example.com', 'Manager'),
        ('Jane', 'jane@example.com', 'HR'),
    )


def test_pick_n_returns_correct_count(csv_sample_config):
    sample_reader = SamplesReader(csv_sample_config, BASE_PATH)
    sample = sample_reader['csv_sample']

    rows = sample.pick_n(5)
    assert len(rows) == 5
    assert all(isinstance(r, Row) for r in rows)


def test_weighted_pick_csv(weighted_csv_sample_config):
    sample_reader = SamplesReader(
        weighted_csv_sample_config, BASE_PATH,
    )
    sample = sample_reader['weighted_csv']

    row = sample.weighted_pick('weight')
    assert isinstance(row, Row)
    assert row.name in ('John', 'Jane', 'Bob')


def test_weighted_pick_json(weighted_json_sample_config):
    sample_reader = SamplesReader(
        weighted_json_sample_config, BASE_PATH,
    )
    sample = sample_reader['weighted_json']

    row = sample.weighted_pick('weight')
    assert isinstance(row, Row)
    assert row.name in ('John', 'Jane', 'Bob')


def test_weighted_pick_respects_distribution(
    weighted_csv_sample_config,
):
    sample_reader = SamplesReader(
        weighted_csv_sample_config, BASE_PATH,
    )
    sample = sample_reader['weighted_csv']

    counts: dict[str, int] = {}
    n = 10000
    for _ in range(n):
        row = sample.weighted_pick('weight')
        counts[row.name] = counts.get(row.name, 0) + 1

    # With weights 70/20/10, ordering should hold
    assert counts['John'] > counts['Jane'] > counts['Bob']
    assert counts['John'] / n > 0.5


def test_weighted_pick_n_returns_correct_count(
    weighted_csv_sample_config,
):
    sample_reader = SamplesReader(
        weighted_csv_sample_config, BASE_PATH,
    )
    sample = sample_reader['weighted_csv']

    rows = sample.weighted_pick_n('weight', 5)
    assert len(rows) == 5
    assert all(isinstance(r, Row) for r in rows)


def test_weighted_pick_nonexistent_column_raises(csv_sample_config):
    sample_reader = SamplesReader(csv_sample_config, BASE_PATH)
    sample = sample_reader['csv_sample']

    with pytest.raises(SamplePickError, match='not found'):
        sample.weighted_pick('nonexistent')


def test_weighted_pick_non_numeric_weight_raises(
    bad_weights_csv_sample_config,
):
    sample_reader = SamplesReader(
        bad_weights_csv_sample_config, BASE_PATH,
    )
    sample = sample_reader['bad_weights']

    with pytest.raises(SamplePickError, match='non-numeric'):
        sample.weighted_pick('weight')


def test_weighted_pick_no_headers_raises(flat_items_sample_config):
    sample_reader = SamplesReader(
        flat_items_sample_config, BASE_PATH,
    )
    sample = sample_reader['items_sample']

    with pytest.raises(SamplePickError, match='not found'):
        sample.weighted_pick('weight')


def test_weighted_pick_caches_weights(weighted_csv_sample_config):
    sample_reader = SamplesReader(
        weighted_csv_sample_config, BASE_PATH,
    )
    sample = sample_reader['weighted_csv']

    sample.weighted_pick('weight')
    assert 'weight' in sample._cum_weights_cache

    # Second call uses cache
    sample.weighted_pick('weight')
