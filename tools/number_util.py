def round_into_str_with_max_digits(number, digits_count):
    return "{:.{}f}".format(round(number, digits_count), digits_count)
