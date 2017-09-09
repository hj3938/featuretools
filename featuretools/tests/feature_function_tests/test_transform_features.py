import pytest
import pandas as pd
from featuretools.synthesis.deep_feature_synthesis import match
from featuretools.computational_backends import PandasBackend
from featuretools.primitives import (Day, Hour, Diff, Compare, Not,
                                     DirectFeature, Count, Add,
                                     Subtract, Multiply, IdentityFeature,
                                     Divide, CumSum, CumCount, CumMin, CumMax,
                                     CumMean, Mod, And, Or, Negate, Sum,
                                     IsIn, Feature, IsNull, get_transform_primitives,
                                     Mode, Percentile)
from featuretools import Timedelta
from ..testing_utils import make_ecommerce_entityset
import numpy as np

@pytest.fixture(scope='module')
def es():
    return make_ecommerce_entityset()


@pytest.fixture(scope='module')
def int_es():
    return make_ecommerce_entityset(with_integer_time_index=True)


def test_make_trans_feat(es):
    f = Hour(es['log']['datetime'])

    pandas_backend = PandasBackend(es, [f])
    df = pandas_backend.calculate_all_features(instance_ids=[0],
                                               time_last=None)
    v = df[f.get_name()][0]
    assert v == 10


def test_diff(es):
    value = IdentityFeature(es['log']['value'])
    customer_id_feat = \
        DirectFeature(es['sessions']['customer_id'],
                      child_entity=es['log'])
    diff2 = Diff(value, es['log']['session_id'])
    diff3 = Diff(value, customer_id_feat)

    pandas_backend = PandasBackend(es, [diff2, diff3])
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)

    val2 = df[diff2.get_name()].values.tolist()
    val3 = df[diff3.get_name()].values.tolist()
    correct_vals2 = [np.nan, 5, 5, 5, 5, np.nan, 1, 1, 1, np.nan, np.nan, 5, np.nan, 7, 7]
    correct_vals3 = [np.nan, 5, 5, 5, 5, -20, 1, 1, 1, -3, np.nan, 5, -5, 7, 7]
    for i, v in enumerate(val2):
        v2 = val2[i]
        if np.isnan(v2):
            assert (np.isnan(correct_vals2[i]))
        else:
            assert v2 == correct_vals2[i]
        v3 = val3[i]
        if np.isnan(v3):
            assert (np.isnan(correct_vals3[i]))
        else:
            assert v3 == correct_vals3[i]


def test_compare_of_identity(es):
    to_test = [(Compare.EQ, [False, False, True, False]),
               (Compare.NE, [True, True, False, True]),
               (Compare.LT, [True, True, False, False]),
               (Compare.LE, [True, True, True, False]),
               (Compare.GT, [False, False, False, True]),
               (Compare.GE, [False, False, True, True])]

    features = []
    for test in to_test:
        features.append(Compare(es['log']['value'], test[0], 10))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1, 2, 3],
                                               time_last=None)

    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert v == test[1]


def test_compare_of_direct(es):
    log_rating = DirectFeature(es['products']['rating'],
                               child_entity=es['log'])
    to_test = [(Compare.EQ, [False, False, False, False]),
               (Compare.NE, [True, True, True, True]),
               (Compare.LT, [False, False, False, True]),
               (Compare.LE, [False, False, False, True]),
               (Compare.GT, [True, True, True, False]),
               (Compare.GE, [True, True, True, False])]

    features = []
    for test in to_test:
        features.append(Compare(log_rating, test[0], 4.5))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1, 2, 3],
                                               time_last=None)

    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert v == test[1]


def test_compare_of_transform(es):
    day = Day(es['log']['datetime'])
    to_test = [(Compare.EQ, [False, True]),
               (Compare.NE, [True, False]),
               (Compare.LT, [True, False]),
               (Compare.LE, [True, True]),
               (Compare.GT, [False, False]),
               (Compare.GE, [False, True])]

    features = []
    for test in to_test:
        features.append(Compare(day, test[0], 10))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 14],
                                               time_last=None)

    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert v == test[1]


def test_compare_of_agg(es):
    count_logs = Count(es['log']['id'],
                       parent_entity=es['sessions'])

    to_test = [(Compare.EQ, [False, False, False, True]),
               (Compare.NE, [True, True, True, False]),
               (Compare.LT, [False, False, True, False]),
               (Compare.LE, [False, False, True, True]),
               (Compare.GT, [True, True, False, False]),
               (Compare.GE, [True, True, False, True])]

    features = []
    for test in to_test:
        features.append(Compare(count_logs, test[0], 2))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1, 2, 3],
                                               time_last=None)

    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert v == test[1]


def test_compare_all_nans(es):
    nan_feat = Mode(es['log']['product_id'], es['sessions'])
    compare = nan_feat == 'brown bag'
    # before all data
    time_last = pd.Timestamp('1/1/1993')
    pandas_backend = PandasBackend(es, [nan_feat, compare])
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1, 2],
                                               time_last=time_last)
    assert df[nan_feat.get_name()].dropna().shape[0] == 0
    assert not df[compare.get_name()].any()


def test_arithmetic_of_val(es):
    to_test = [(Add, [2.0, 7.0, 12.0, 17.0], [2.0, 7.0, 12.0, 17.0]),
               (Subtract, [-2.0, 3.0, 8.0, 13.0], [2.0, -3.0, -8.0, -13.0]),
               (Multiply, [0, 10, 20, 30], [0, 10, 20, 30]),
               (Divide, [0, 2.5, 5, 7.5], [np.inf, 0.4, 0.2, 2 / 15.0],
                                          [np.nan, np.inf, np.inf, np.inf])]

    features = []
    logs = es['log']

    for test in to_test:
        features.append(test[0](logs['value'], 2))
        features.append(test[0](2, logs['value']))

    features.append(Divide(logs['value'], 0))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1, 2, 3],
                                               time_last=None)

    for i, test in enumerate(to_test):
        v = df[features[2 * i].get_name()].values.tolist()
        assert v == test[1]
        v = df[features[2 * i + 1].get_name()].values.tolist()
        assert v == test[2]

    test = to_test[-1][-1]
    v = df[features[-1].get_name()].values.tolist()
    assert (np.isnan(v[0]))
    assert v[1:] == test[1:]


def test_arithmetic_two_vals_fails(es):
    with pytest.raises(ValueError):
        Add(2, 2)


def test_arithmetic_of_identity(es):
    logs = es['log']

    to_test = [(Add, [0., 7., 14., 21.]),
               (Subtract, [0, 3, 6, 9]),
               (Multiply, [0, 10, 40, 90]),
               (Divide, [np.nan, 2.5, 2.5, 2.5])]

    features = []
    for test in to_test:
        features.append(test[0](logs['value'], logs['value_2']))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1, 2, 3],
                                               time_last=None)

    for i, test in enumerate(to_test[:-1]):
        v = df[features[i].get_name()].values.tolist()
        assert v == test[1]
    i, test = 3, to_test[-1]
    v = df[features[i].get_name()].values.tolist()
    assert (np.isnan(v[0]))
    assert v[1:] == test[1][1:]


def test_arithmetic_of_direct(es):
    rating = es['products']['rating']
    log_rating = DirectFeature(rating,
                               child_entity=es['log'])
    customer_age = es['customers']['age']
    session_age = DirectFeature(customer_age,
                                child_entity=es['sessions'])
    log_age = DirectFeature(session_age,
                            child_entity=es['log'])

    to_test = [(Add, [38, 37, 37.5, 37.5]),
               (Subtract, [28, 29, 28.5, 28.5]),
               (Multiply, [165, 132, 148.5, 148.5]),
               (Divide, [6.6, 8.25, 22. / 3, 22. / 3])]

    features = []
    for test in to_test:
        features.append(test[0](log_age, log_rating))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 3, 5, 7],
                                               time_last=None)

    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert v == test[1]


# P TODO: rewrite this  test
def test_arithmetic_of_transform(es):
    diff1 = Diff(IdentityFeature(es['log']['value']),
                 IdentityFeature(es['log']['product_id']))
    diff2 = Diff(IdentityFeature(es['log']['value_2']),
                 IdentityFeature(es['log']['product_id']))

    to_test = [(Add, [np.nan, 14., -7., 3.]),
               (Subtract, [np.nan, 6., -3., 1.]),
               (Multiply, [np.nan, 40., 10., 2.]),
               (Divide, [np.nan, 2.5, 2.5, 2.])]

    features = []
    for test in to_test:
        features.append(test[0](diff1, diff2))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 2, 11, 13],
                                               time_last=None)
    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert np.isnan(v.pop(0))
        assert np.isnan(test[1].pop(0))
        assert v == test[1]


def test_not_feature(es):
    likes_ice_cream = es['customers']['loves_ice_cream']
    not_feat = Not(likes_ice_cream)
    features = [not_feat]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1],
                                               time_last=None)
    v = df[not_feat.get_name()].values
    assert not v[0]
    assert v[1]


def test_arithmetic_of_agg(es):
    customer_id_feat = es['customers']['id']
    store_id_feat = es['stores']['id']
    count_customer = Count(customer_id_feat,
                           parent_entity=es['regions'])
    count_stores = Count(store_id_feat,
                         parent_entity=es['regions'])
    to_test = [(Add, [6, 2]),
               (Subtract, [0, -2]),
               (Multiply, [9, 0]),
               (Divide, [1, 0])]

    features = []
    for test in to_test:
        features.append(test[0](count_customer, count_stores))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=['United States', 'Mexico'],
                                               time_last=None)

    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert v == test[1]


def test_cum_sum(es):
    log_value_feat = es['log']['value']
    cum_sum = CumSum(log_value_feat, es['log']['session_id'])
    features = [cum_sum]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_sum.get_name()].values
    assert len(cvalues) == 15
    cum_sum_values = [0, 5, 15, 30, 50, 0, 1, 3, 6, 0, 0, 5, 0, 7, 21]
    for i, v in enumerate(cum_sum_values):
        assert v == cvalues[i]


def test_cum_min(es):
    log_value_feat = es['log']['value']
    cum_min = CumMin(log_value_feat, es['log']['session_id'])
    features = [cum_min]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_min.get_name()].values
    assert len(cvalues) == 15
    cum_min_values = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for i, v in enumerate(cum_min_values):
        assert v == cvalues[i]


def test_cum_max(es):
    log_value_feat = es['log']['value']
    cum_max = CumMax(log_value_feat, es['log']['session_id'])
    features = [cum_max]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_max.get_name()].values
    assert len(cvalues) == 15
    cum_max_values = [0, 5, 10, 15, 20, 0, 1, 2, 3, 0, 0, 5, 0, 7, 14]
    for i, v in enumerate(cum_max_values):
        assert v == cvalues[i]


def test_cum_sum_use_previous(es):
    log_value_feat = es['log']['value']
    cum_sum = CumSum(log_value_feat, es['log']['session_id'],
                     use_previous=Timedelta(3, 'observations',
                                            entity=es['log']))
    features = [cum_sum]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_sum.get_name()].values
    assert len(cvalues) == 15
    cum_sum_values = [0, 5, 15, 30, 45, 0, 1, 3, 6, 0, 0, 5, 0, 7, 21]
    for i, v in enumerate(cum_sum_values):
        assert v == cvalues[i]


def test_cum_sum_use_previous_integer_time(int_es):
    es = int_es

    log_value_feat = es['log']['value']
    with pytest.raises(AssertionError):
        CumSum(log_value_feat, es['log']['session_id'],
               use_previous=Timedelta(3, 'm'))

    cum_sum = CumSum(log_value_feat, es['log']['session_id'],
                     use_previous=Timedelta(3, 'observations',
                                            entity=es['log']))
    features = [cum_sum]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_sum.get_name()].values
    assert len(cvalues) == 15
    cum_sum_values = [0, 5, 15, 30, 45, 0, 1, 3, 6, 0, 0, 5, 0, 7, 21]
    for i, v in enumerate(cum_sum_values):
        assert v == cvalues[i]


def test_cum_sum_where(es):
    log_value_feat = es['log']['value']
    compare_feat = Compare(log_value_feat, '>', 3)
    dfeat = Feature(es['sessions']['customer_id'], es['log'])
    cum_sum = CumSum(log_value_feat, dfeat,
                     where=compare_feat)
    features = [cum_sum]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_sum.get_name()].values
    assert len(cvalues) == 15
    cum_sum_values = [0, 5, 15, 30, 50, 50, 50, 50, 50, 50,
                      0, 5, 5, 12, 26]
    for i, v in enumerate(cum_sum_values):
        if not np.isnan(v):
            assert v == cvalues[i]
        else:
            assert (np.isnan(cvalues[i]))


def test_cum_sum_use_previous_and_where(es):
    log_value_feat = es['log']['value']
    compare_feat = Compare(log_value_feat, '>', 3)
    # todo should this be cummean?
    dfeat = Feature(es['sessions']['customer_id'], es['log'])
    cum_sum = CumSum(log_value_feat, dfeat,
                     where=compare_feat,
                     use_previous=Timedelta(3, 'observations',
                                            entity=es['log']))
    features = [cum_sum]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)

    cum_sum_values = [0, 5, 15, 30, 45, 45, 45, 45, 45, 45,
                      0, 5, 5, 12, 26]
    cvalues = df[cum_sum.get_name()].values
    assert len(cvalues) == 15
    for i, v in enumerate(cum_sum_values):
        assert v == cvalues[i]


def test_cum_sum_group_on_nan(es):
    log_value_feat = es['log']['value']
    es['log'].df['product_id'] = (['coke zero'] * 3 + ['car'] * 2 +
                                  ['toothpaste'] * 3 + ['brown bag'] * 2 +
                                  ['shoes'] +
                                  [np.nan] * 4 +
                                  ['coke_zero'] * 2)
    cum_sum = CumSum(log_value_feat, es['log']['product_id'])
    features = [cum_sum]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_sum.get_name()].values
    assert len(cvalues) == 15
    cum_sum_values = [0, 5, 15,
                      15, 35,
                      0, 1, 3,
                      3, 3,
                      0,
                      np.nan, np.nan, np.nan, np.nan]
    for i, v in enumerate(cum_sum_values):
        if np.isnan(v):
            assert (np.isnan(cvalues[i]))
        else:
            assert v == cvalues[i]


def test_cum_sum_use_previous_group_on_nan(es):
    # TODO: Figure out how to test where `df`
    # in pd_rolling get_function() has multiindex
    log_value_feat = es['log']['value']
    es['log'].df['product_id'] = (['coke zero'] * 3 + ['car'] * 2 +
                                  ['toothpaste'] * 3 + ['brown bag'] * 2 +
                                  ['shoes'] +
                                  [np.nan] * 4 +
                                  ['coke_zero'] * 2)
    cum_sum = CumSum(log_value_feat, es['log']['product_id'], es["log"]["datetime"],
                     use_previous=Timedelta(40, 'seconds'))
    features = [cum_sum]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_sum.get_name()].values
    assert len(cvalues) == 15
    cum_sum_values = [0, 5, 15,
                      15, 35,
                      0, 1, 3,
                      3, 0,
                      0,
                      np.nan, np.nan, np.nan, np.nan]
    for i, v in enumerate(cum_sum_values):
        if np.isnan(v):
            assert (np.isnan(cvalues[i]))
        else:
            assert v == cvalues[i]


def test_cum_sum_use_previous_and_where_absolute(es):
    log_value_feat = es['log']['value']
    compare_feat = Compare(log_value_feat, '>', 3)
    dfeat = Feature(es['sessions']['customer_id'], es['log'])
    cum_sum = CumSum(log_value_feat, dfeat, es["log"]["datetime"],
                     where=compare_feat,
                     use_previous=Timedelta(40, 'seconds'))
    features = [cum_sum]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)

    cum_sum_values = [0, 5, 15, 30, 50, 0, 0, 0, 0, 0,
                      0, 5, 0, 7, 21]
    cvalues = df[cum_sum.get_name()].values
    assert len(cvalues) == 15
    for i, v in enumerate(cum_sum_values):
        assert v == cvalues[i]


def test_cum_mean(es):
    log_value_feat = es['log']['value']
    cum_mean = CumMean(log_value_feat, es['log']['session_id'])
    features = [cum_mean]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_mean.get_name()].values
    assert len(cvalues) == 15
    cum_mean_values = [0, 2.5, 5, 7.5, 10, 0, .5, 1, 1.5, 0, 0, 2.5, 0, 3.5, 7]
    for i, v in enumerate(cum_mean_values):
        assert v == cvalues[i]


def test_cum_mean_use_previous(es):
    log_value_feat = es['log']['value']
    cum_mean = CumMean(log_value_feat, es['log']['session_id'],
                       use_previous=Timedelta(3, 'observations',
                                              entity=es['log']))
    features = [cum_mean]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_mean.get_name()].values
    assert len(cvalues) == 15
    cum_mean_values = [0, 2.5, 5, 10, 15, 0, .5, 1, 2, 0, 0, 2.5, 0, 3.5, 7]
    for i, v in enumerate(cum_mean_values):
        assert v == cvalues[i]


def test_cum_mean_where(es):
    log_value_feat = es['log']['value']
    compare_feat = Compare(log_value_feat, '>', 3)
    dfeat = Feature(es['sessions']['customer_id'], es['log'])
    cum_mean = CumMean(log_value_feat, dfeat,
                       where=compare_feat)
    features = [cum_mean]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_mean.get_name()].values
    assert len(cvalues) == 15
    cum_mean_values = [0, 5, 7.5, 10, 12.5, 12.5, 12.5, 12.5, 12.5, 12.5,
                       0, 5, 5, 6, 26. / 3]

    for i, v in enumerate(cum_mean_values):
        if not np.isnan(v):
            assert v == cvalues[i]
        else:
            assert (np.isnan(cvalues[i]))


def test_cum_mean_use_previous_and_where(es):
    log_value_feat = es['log']['value']
    compare_feat = Compare(log_value_feat, '>', 3)
    # todo should this be cummean?
    dfeat = Feature(es['sessions']['customer_id'], es['log'])
    cum_mean = CumMean(log_value_feat, dfeat,
                       where=compare_feat,
                       use_previous=Timedelta(2, 'observations',
                                              entity=es['log']))
    features = [cum_mean]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)

    cum_mean_values = [0, 5, 7.5, 12.5, 17.5, 17.5, 17.5, 17.5, 17.5, 17.5,
                       0, 5, 5, 6, 10.5]
    cvalues = df[cum_mean.get_name()].values
    assert len(cvalues) == 15
    for i, v in enumerate(cum_mean_values):
        assert v == cvalues[i]


def test_cum_count(es):
    log_id_feat = es['log']['id']
    cum_count = CumCount(log_id_feat, es['log']['session_id'])
    features = [cum_count]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=range(15),
                                               time_last=None)
    cvalues = df[cum_count.get_name()].values
    assert len(cvalues) == 15
    cum_count_values = [1, 2, 3, 4, 5, 1, 2, 3, 4, 1, 1, 2, 1, 2, 3]
    for i, v in enumerate(cum_count_values):
        assert v == cvalues[i]


def test_arithmetic(es):
    # P TODO:
    return
    hour = Hour(es['log']['datetime'])
    day = Day(es['log']['datetime'])

    to_test = [(Add, [19, 19, 19, 19]),
               (Subtract, [-1, -1, -1, -1]),
               (Multiply, [90, 90, 90, 90]),
               (Divide, [.9, .9, .9, .9])]

    features = []
    features.append(day + hour)
    features.append(day - hour)
    features.append(day * hour)
    features.append(day / hour)

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 3, 5, 7],
                                               time_last=None)
    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert v == test[1]


def test_overrides(es):
    # P TODO:
    return
    hour = Hour(es['log']['datetime'])
    day = Day(es['log']['datetime'])

    feats = [Add, Subtract, Multiply, Divide,
             Mod, And, Or]
    compare_ops = ['>', '<', '=', '!=',
                   '>=', '<=']
    assert Negate(hour).hash() == (-hour).hash()

    compares = [(hour, hour),
                (hour, day),
                (day, 2)]
    overrides = [
        hour + hour,
        hour - hour,
        hour * hour,
        hour / hour,
        hour % hour,
        hour & hour,
        hour | hour,
        hour > hour,
        hour < hour,
        hour == hour,
        hour != hour,
        hour >= hour,
        hour <= hour,

        hour + day,
        hour - day,
        hour * day,
        hour / day,
        hour % day,
        hour & day,
        hour | day,
        hour > day,
        hour < day,
        hour == day,
        hour != day,
        hour >= day,
        hour <= day,

        day + 2,
        day - 2,
        day * 2,
        day / 2,
        day % 2,
        day & 2,
        day | 2,
        day > 2,
        day < 2,
        day == 2,
        day != 2,
        day >= 2,
        day <= 2,
    ]

    i = 0
    for left, right in compares:
        for feat in feats:
            f = feat(left, right)
            o = overrides[i]
            assert o.hash() == f.hash()
            i += 1

        for compare_op in compare_ops:
            f = Compare(left, compare_op, right)
            o = overrides[i]
            assert o.hash() == f.hash()
            i += 1

    our_reverse_overrides = [
        2 + day,
        2 - day,
        2 * day,
        2 / day,
        2 & day,
        2 | day]
    i = 0
    for feat in feats:
        if feat != Mod:
            f = feat(2, day)
            o = our_reverse_overrides[i]
            assert o.hash() == f.hash()
            i += 1

    python_reverse_overrides = [
        2 < day,
        2 > day,
        2 == day,
        2 != day,
        2 <= day,
        2 >= day]
    i = 0
    for compare_op in compare_ops:
        f = Compare(day, compare_op, 2)
        o = python_reverse_overrides[i]
        assert o.hash() == f.hash()
        i += 1


def test_override_boolean(es):
    # P TODO:
    return
    count = Count(es['log']['value'], es['sessions'])
    count_lo = Compare(count, '>', 1)
    count_hi = Compare(count, '<', 10)

    to_test = [[True, True, True],
               [True, True, False],
               [False, False, True]]

    features = []
    features.append(count_lo.OR(count_hi))
    features.append(count_lo.AND(count_hi))
    features.append(~(count_lo.AND(count_hi)))

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1, 2],
                                               time_last=None)
    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert v == test


def test_override_cmp_from_variable(es):
    count_lo = IdentityFeature(es['log']['value']) > 1

    to_test = [False, True, True]

    features = [count_lo]

    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1, 2],
                                               time_last=None)
    v = df[count_lo.get_name()].values.tolist()
    for i, test in enumerate(to_test):
        assert v[i] == test


def test_override_cmp(es):
    # P TODO:
    return
    count = Count(es['log']['value'], es['sessions'])
    _sum = Sum(es['log']['value'], es['sessions'])
    gt_lo = count > 1
    gt_other = count > _sum
    ge_lo = count >= 1
    ge_other = count >= _sum
    lt_hi = count < 10
    lt_other = count < _sum
    le_hi = count <= 10
    le_other = count <= _sum
    ne_lo = count != 1
    ne_other = count != _sum

    to_test = [[True, True, False],
               [False, False, True],
               [True, True, True],
               [False, False, True],
               [True, True, True],
               [True, True, False],
               [True, True, True],
               [True, True, False]]
    features = [gt_lo, gt_other, ge_lo, ge_other, lt_hi,
                lt_other, le_hi, le_other, ne_lo, ne_other]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(instance_ids=[0, 1, 2],
                                               time_last=None)
    for i, test in enumerate(to_test):
        v = df[features[i].get_name()].values.tolist()
        assert v == test


def test_isin_feat(es):
    isin = IsIn(es['log']['product_id'], ["toothpaste", "coke zero"])
    features = [isin]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(range(8), None)
    true = [True, True, True, False, False, True, True, True]
    v = df[isin.get_name()].values.tolist()
    assert true == v


def test_isin_feat_other_syntax(es):
    isin = Feature(es['log']['product_id']).isin(["toothpaste", "coke zero"])
    features = [isin]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(range(8), None)
    true = [True, True, True, False, False, True, True, True]
    v = df[isin.get_name()].values.tolist()
    assert true == v


def test_isin_feat_other_syntax_int(es):
    isin = Feature(es['log']['value']).isin([5, 10])
    features = [isin]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(range(8), None)
    true = [False, True, True, False, False, False, False, False]
    v = df[isin.get_name()].values.tolist()
    assert true == v


def test_isnull_feat(es):
    value = IdentityFeature(es['log']['value'])
    diff = Diff(value, es['log']['session_id'])
    isnull = IsNull(diff)
    features = [isnull]
    pandas_backend = PandasBackend(es, features)
    df = pandas_backend.calculate_all_features(range(15), None)
    # correct_vals_diff = [np.nan, 5, 5, 5, 5, np.nan, 1, 1, 1, np.nan, np.nan, 5, np.nan, 7, 7]
    correct_vals = [True, False, False, False, False, True, False, False,
                    False, True, True, False, True, False, False]
    values = df[isnull.get_name()].values.tolist()
    assert correct_vals == values


def test_init_and_name(es):
    log = es['log']
    features = [Feature(v) for v in log.variables] + [Compare(Feature(es["products"]["rating"], es["log"]), '>', 2.5)]
    # Add Timedelta feature
    features.append(pd.Timestamp.now() - Feature(log['datetime']))
    for transform_prim in get_transform_primitives():
        if transform_prim == Compare:
            continue
        # use the input_types matching function from DFS
        input_types = transform_prim.input_types
        if type(input_types[0]) == list:
            matching_inputs = [g for s in input_types for g in match(s, features)]
        else:
            matching_inputs = match(input_types, features)
        if len(matching_inputs) == 0:
            raise Exception("Transform Primitive %s not tested" % transform_prim.name)
        for s in matching_inputs:
            instance = transform_prim(*s)

            # try to get name and calculate
            instance.get_name()
            instance.head()

def test_percentile(es):
    v = Feature(es['log']['value'])
    p = Percentile(v)
    pandas_backend = PandasBackend(es, [v, p])
    df = pandas_backend.calculate_all_features(range(17), None)
    true = df[v.get_name()].rank(pct=True)
    for t, a in zip(true.values, df[p.get_name()].values):
        assert (pd.isnull(t) and pd.isnull(a)) or t == a


# P TODO: reimplement like
# def test_like_feat(es):
#     like = Like(es['log']['product_id'], "coke")
#     features = [like]
#     pandas_backend = PandasBackend(es, features)
#     df = pandas_backend.calculate_all_features(range(5), None)
#     true = [True, True, True, False, False]
#     v = df[like.get_name()].values.tolist()
#     assert true == v


# P TODO: reimplement like
# def test_like_feat_other_syntax(es):
#     like = Feature(es['log']['product_id']).LIKE("coke")
#     features = [like]
#     pandas_backend = PandasBackend(es, features)
#     df = pandas_backend.calculate_all_features(range(5), None)
#     true = [True, True, True, False, False]
#     v = df[like.get_name()].values.tolist()
#     assert true == v