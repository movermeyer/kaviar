# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
import logging

import pytest
from six import text_type

from kaviar import KvLoggerAdapter, EventKvLoggerAdapter

from .conftest import skip_if_pypy


@pytest.fixture
def logger():
    return KvLoggerAdapter.get_logger()


@pytest.fixture
def event_logger():
    return EventKvLoggerAdapter.get_logger()


@pytest.fixture
def assert_logged(caplog):
    def __assert_logged(*args):
        expected_records = ([('root', ) + args, ]
                            if (len(args) == 2 and
                                isinstance(args[0], int) and
                                isinstance(args[1], text_type))
                            else list(args))

        assert caplog.record_tuples() == expected_records

        actual_records = caplog.handler.records
        caplog.handler.records = []
        return actual_records

    return __assert_logged


log_test_data = pytest.mark.parametrize('log_level,method,kwargs,output', [
    (logging.DEBUG, 'debug', {'a': 23, 'b': 45}, 'a=23   b=45'),
    (logging.INFO, 'info', {'c': 67, 'd': 89}, 'c=67   d=89'),
    (logging.WARNING, 'warning', {'e': 12, 'f': 34}, 'e=12   f=34'),
    (logging.ERROR, 'error', {'g': 56, 'h': 78}, 'g=56   h=78'),
    (logging.CRITICAL, 'critical', {'i': 90, 'j': 12}, 'i=90   j=12'),
])


@log_test_data
def test_partial_log_data(logger, assert_logged,
                          log_level, method, kwargs, output):
    getattr(logger, method)(**kwargs)
    record = assert_logged(log_level, output)[0]
    assert not record.exc_info


def test_log_data(logger, assert_logged):
    logger.log(logging.WARNING, b=27, f=12)
    record = assert_logged(logging.WARNING, 'b=27   f=12')[0]
    assert not record.exc_info


def test_log_exception(logger, assert_logged):
    try:
        # noinspection PyUnusedLocal
        a = 42 / 0  # B00M!
    except ZeroDivisionError:
        logger.exception('ExceptionalException', a=11, b=12)
    else:  # pragma: no cover
        pytest.fail('Should not be reached')

    record = assert_logged(logging.ERROR, 'a=11   b=12')[0]
    assert record.exc_info and isinstance(record.exc_info[1],
                                          ZeroDivisionError)


def test_extra_context(assert_logged):
    logger_ = KvLoggerAdapter.get_logger(extra={'extrawurst': True, })
    logger_.info('IgnoredValue', log='value')

    assert_logged(logging.INFO, 'extrawurst=True   log=value')


@pytest.mark.parametrize('name_in,name_out',
                         [((), 'root'),
                          (('myapp', ), 'myapp'),
                          (('myapp.submodule', ), 'myapp.submodule'),
                          (('myapp...submodule', ), 'myapp.submodule'),
                          (('myapp.submodule...', ), 'myapp.submodule'),
                          (('myapp', 'submodule', ), 'myapp.submodule'),
                          (('myapp.', 'submodule', ), 'myapp.submodule'),
                          (('myapp.submodule', 'part'),
                           'myapp.submodule.part'), ])
def test_logger_name_easy(caplog, name_in, name_out):
    logger_ = KvLoggerAdapter.get_logger(*name_in)
    logger_.info(b=23, g=19)

    assert caplog.record_tuples() == [
        (name_out, logging.INFO, 'b=23   g=19')
    ]


@skip_if_pypy
def test_define_logger_func(logger, assert_logged):
    logger_a = logger.define_logger_func(logging.INFO, 'z x y')
    logger_b = logger.define_logger_func(logging.DEBUG, 'a b c')

    logger_b('test', 'toast', 'taste')
    logger_a(1, 2, 3)

    assert_logged(('root', logging.DEBUG, 'a=test   b=toast   c=taste'),
                  ('root', logging.INFO, 'z=1   x=2   y=3'))


@log_test_data
def test_partial_event_log_data(event_logger, assert_logged,
                                log_level, method, kwargs, output):
    getattr(event_logger, method)('FANCY_EVENT', **kwargs)
    record = assert_logged(log_level, 'event=FANCY_EVENT   ' + output)[0]
    assert not record.exc_info


def test_event_name_required(event_logger):
    with pytest.raises(TypeError) as exc_info:
        event_logger.debug(a=42, b=23)

    assert (("missing required positional argument: 'event'", )
            == exc_info.value.args)


@skip_if_pypy
def test_define_event_logger_func(event_logger, assert_logged):
    logger_a = event_logger.define_logger_func(logging.INFO, 'z x y')
    logger_b = event_logger.define_logger_func(logging.DEBUG, 'a b c')

    logger_b('EVENT_B', 'test', 'toast', 'taste')
    logger_a('EVENT_A', 1, 2, 3)

    assert_logged(('root', logging.DEBUG, ('event=EVENT_B   a=test'
                                           '   b=toast   c=taste')),
                  ('root', logging.INFO, 'event=EVENT_A   z=1   x=2   y=3'))
