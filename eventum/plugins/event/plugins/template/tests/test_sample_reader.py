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
    Sample,
    SampleLoadError,
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
    assert row.name == 'John'
    assert row.email == 'john@example.com'
    assert row.position == 'Manager'


def test_csv_sample_without_header_no_named_access(
    no_header_csv_sample_config,
):
    sample_reader = SamplesReader(no_header_csv_sample_config, BASE_PATH)
    sample = sample_reader['csv_sample']

    row = sample[0]
    assert not hasattr(row, 'name')
    assert row[0] == 'name'


def test_items_sample_no_named_access(items_sample_config):
    sample_reader = SamplesReader(items_sample_config, BASE_PATH)
    sample = sample_reader['items_sample']

    row = sample[0]
    assert not hasattr(row, 'name')
    assert row[0] == 'one'


def test_missing_samples(items_sample_config):
    sample_reader = SamplesReader(items_sample_config, BASE_PATH)
    with pytest.raises(KeyError):
        sample_reader['missing_samples']
