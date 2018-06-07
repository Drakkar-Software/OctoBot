import numpy as np
import timeit

high_list = [float(i + 2) for i in range(0, 50)]
low_list = [float(i - 2) for i in range(0, 50)]
close_list = [float(i) for i in range(0, 50)]

high_np = np.array(high_list)
low_np = np.array(low_list)
close_np = np.array(close_list)


def test_as_array():
    np.asarray(high_list)


def test_np_array():
    np.array(high_list)


def test_edit_np_array():
    for i in range(len(high_np)):
        high_np[i] = i


def test_edit_one_np_array():
    high_np[-1] = 0


def print_bench(fct_str, number):
    print("{0} | n = {1} | Time : {2}".format(fct_str,
                                              number,
                                              timeit.timeit("{}()".format(fct_str),
                                                            setup="from __main__ import {}".format(fct_str),
                                                            number=number)))


exec_times = 5000000
print_bench("test_as_array", exec_times)
print_bench("test_np_array", exec_times)
print_bench("test_edit_one_np_array", exec_times)
print_bench("test_edit_np_array", exec_times)
