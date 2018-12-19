import math

from config import START_PENDING_EVAL_NOTE


def check_valid_eval_note(eval_note):
    return eval_note and eval_note is not START_PENDING_EVAL_NOTE and not math.isnan(eval_note)
