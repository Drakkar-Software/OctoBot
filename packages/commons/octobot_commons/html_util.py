# pylint: disable=W0718, W1203
# Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import html.parser
import collections
import typing

# avoid cyclic imports with commons_logging
import logging


_IGNORED_ELEMENTS = ["script", "button"]
DEFAULT_ELEMENT_TEXT_MAX_SIZE = 100
MAX_RECURSIVE_EXCEPTION_CAUSES_DEPTH = 20


def summarize_page_content(
    html_content: str, max_element_text_size: int = DEFAULT_ELEMENT_TEXT_MAX_SIZE
) -> list[tuple[str, str]]:
    """
    :return: a list of (tag, content) tuples representing a html page's useful content
    """
    parser = _SummarizerHTMLParser(max_element_text_size)
    parser.feed(html_content)
    return parser.summary


def pretty_print_summary(summary: list[tuple[str, str]]) -> str:
    """
    :return: a str representing the summary of the page
    """
    return "; ".join(f"{element[0]}<{element[1]}>" for element in summary)


def is_html_content(html_content: str) -> bool:
    """
    :return: True if the given html_content looks like html
    """
    return "</html>" in html_content


def get_html_summary_if_relevant(
    html_content: typing.Any, max_element_text_size: int = DEFAULT_ELEMENT_TEXT_MAX_SIZE
) -> typing.Any:
    """
    :return: the str summary of the given html_content if
    it is html, the given html_content otherwise
    """
    try:
        str_html_content = (
            html_content if isinstance(html_content, str) else str(html_content)
        )
        if is_html_content(str_html_content):
            return pretty_print_summary(
                summarize_page_content(
                    str_html_content, max_element_text_size=max_element_text_size
                )
            )
        return str_html_content
    except BaseException as err:
        logging.getLogger("html_util").error(
            f"Error when parsing html_content '{html_content}', "
            f"error: {err} ({err.__class__.__name__})"
        )
    return html_content


def summarize_exception_html_cause_if_relevant(exception: BaseException, depth=0):
    """
    Recursively updates args and the __cause__ attribute
    of the exception to summarize html content if any
    """
    try:
        # Optimistic consideration of attributes being available: should always be the case.
        # However, if this is not the case, just catch the error not forward it
        if exception is not None:
            exception.args = tuple(
                get_html_summary_if_relevant(arg) for arg in exception.args
            )
            # condition should not be necessary but still make sure to avoid infinite recursive loops
            if depth < MAX_RECURSIVE_EXCEPTION_CAUSES_DEPTH:
                # recursive call to make sure nested causes are also summarized
                summarize_exception_html_cause_if_relevant(
                    exception.__cause__, depth=depth + 1
                )
    except BaseException:
        # Can't format html, nothing to do: just stop processing
        pass


class _SummarizerHTMLParser(html.parser.HTMLParser):
    """
    Walks through the give html document and stores its relevant into self.summary
    """

    # from https://docs.python.org/3/library/html.parser.html

    def __init__(self, max_element_text_size: int):
        super().__init__()
        self.summary: list[tuple[str, str]] = []

        self._path = collections.deque()
        self._max_element_text_size = max_element_text_size

    def handle_starttag(self, tag, attrs):
        self._path.append(tag)

    def handle_endtag(self, tag):
        self._path.pop()

    def handle_data(self, data):
        cleared_data = data.strip()
        if len(cleared_data) > self._max_element_text_size:
            cleared_data = f"{cleared_data[:self._max_element_text_size]}[...]"
        if len(cleared_data) > 1:
            try:
                element_name = self._path[-1]
                if element_name not in _IGNORED_ELEMENTS:
                    self.summary.append((element_name, cleared_data))
            except IndexError:
                # before or after html content
                self.summary.append(("message", cleared_data))
            except BaseException as err:
                logging.getLogger(self.__class__.__name__).error(
                    f"Error when parsing element for: '{data}', "
                    f"error: {err} ({err.__class__.__name__})",
                )
