#  Drakkar-Software OctoBot-Commons
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
import mock
import pytest
import traceback

import octobot_commons.html_util as html_util


def test_summarize_page_content_invalid_content():
    assert html_util.summarize_page_content("plop") == [('message', 'plop')]
    with pytest.raises(TypeError):
        html_util.summarize_page_content(1234)
    with pytest.raises(TypeError):
        html_util.summarize_page_content(RuntimeError("124"))
    with pytest.raises(TypeError):
        html_util.summarize_page_content({})
    assert html_util.summarize_page_content(RATE_LIMIT_INVALID_HTMLS[0]) == []
    with pytest.raises(IndexError):
        html_util.summarize_page_content(RATE_LIMIT_INVALID_HTMLS[1])
    with pytest.raises(IndexError):
        html_util.summarize_page_content(RATE_LIMIT_INVALID_HTMLS[2])


def test_summarize_page_content_valid_content():
    assert html_util.summarize_page_content(RATE_LIMIT_HTML) == [
        ('title', 'Access denied | api.hollaex.com used Cloudflare to restrict access'),
        ('div', 'Please enable cookies.'),
        ('span', 'Error'),
        ('span', '1006'),
        ('span', 'Ray ID: 8e61e5180c749e8a •'),
        ('span', '2024-11-21 16:00:49 UTC'),
        ('h2', 'Access denied'),
        ('h2', 'What happened?'),
        ('p', 'The owner of this website (api.hollaex.com) has banned your IP address (123.123.123.123).'),
        ('div', 'Was this page helpful?'),
        ('div', 'Thank you for your feedback!'),
        ('span', 'Cloudflare Ray ID:'),
        ('strong', '8e61e5180c749e8a'),
        ('span', 'Your IP:'),
        ('span', '123.123.123.123'),
        ('span', 'Performance & security by'),
        ('a', 'Cloudflare')
    ]
    assert html_util.summarize_page_content(RATE_LIMIT_HTML_WITH_MESSAGE) == [
        ('message', 'hollaex GET https://api.sandbox.hollaex.com/v2/constants 403 Forbidden'),
        ('title', 'Access denied | api.hollaex.com used Cloudflare to restrict access'),
        ('div', 'Please enable cookies.'),
        ('span', 'Error'),
        ('span', '1006'),
        ('span', 'Ray ID: 8e61e5180c749e8a •'),
        ('span', '2024-11-21 16:00:49 UTC'),
        ('h2', 'Access denied'),
        ('h2', 'What happened?'),
        ('p', 'The owner of this website (api.hollaex.com) has banned your IP address (123.123.123.123).'),
        ('div', 'Was this page helpful?'),
        ('div', 'Thank you for your feedback!'),
        ('span', 'Cloudflare Ray ID:'),
        ('strong', '8e61e5180c749e8a'),
        ('span', 'Your IP:'),
        ('span', '123.123.123.123'),
        ('span', 'Performance & security by'),
        ('a', 'Cloudflare')
    ]
    assert html_util.summarize_page_content(RATE_LIMIT_HTML_WITH_MESSAGE, max_element_text_size=4) == [
        ('message', 'holl[...]'),
        ('title', 'Acce[...]'),
        ('div', 'Plea[...]'),
        ('span', 'Erro[...]'),
        ('span', '1006'),
        ('span', 'Ray [...]'),
        ('span', '2024[...]'),
        ('h2', 'Acce[...]'),
        ('h2', 'What[...]'),
        ('p', 'The [...]'),
        ('div', 'Was [...]'),
        ('div', 'Than[...]'),
        ('span', 'Clou[...]'),
        ('strong', '8e61[...]'),
        ('span', 'Your[...]'),
        ('span', '123.[...]'),
        ('span', 'Perf[...]'),
        ('a', 'Clou[...]')
    ]


def test_pretty_print_summary():
    assert html_util.pretty_print_summary(html_util.summarize_page_content(RATE_LIMIT_HTML_WITH_MESSAGE)) == (
        'message<hollaex GET https://api.sandbox.hollaex.com/v2/constants 403 '
        'Forbidden>; title<Access denied | api.hollaex.com used Cloudflare to '
        'restrict access>; div<Please enable cookies.>; span<Error>; span<1006>; '
        'span<Ray ID: 8e61e5180c749e8a •>; span<2024-11-21 16:00:49 UTC>; h2<Access '
        'denied>; h2<What happened?>; p<The owner of this website (api.hollaex.com) '
        'has banned your IP address (123.123.123.123).>; div<Was this page helpful?>; '
        'div<Thank you for your feedback!>; span<Cloudflare Ray ID:>; '
        'strong<8e61e5180c749e8a>; span<Your IP:>; span<123.123.123.123>; '
        'span<Performance & security by>; a<Cloudflare>'
    )


def test_is_html_content():
    assert html_util.is_html_content(RATE_LIMIT_HTML_WITH_MESSAGE) is True
    assert html_util.is_html_content(RATE_LIMIT_HTML) is True
    assert all(html_util.is_html_content(html) for html in RATE_LIMIT_INVALID_HTMLS)
    assert html_util.is_html_content("plpoop") is False
    assert html_util.is_html_content("<html>") is False
    assert html_util.is_html_content("</html/>") is False
    assert html_util.is_html_content("<html/>") is False
    assert html_util.is_html_content("</html>") is True


def test_get_html_summary_if_relevant():
    # valid html
    assert html_util.get_html_summary_if_relevant(RATE_LIMIT_HTML_WITH_MESSAGE) == (
        'message<hollaex GET https://api.sandbox.hollaex.com/v2/constants 403 '
        'Forbidden>; title<Access denied | api.hollaex.com used Cloudflare to '
        'restrict access>; div<Please enable cookies.>; span<Error>; span<1006>; '
        'span<Ray ID: 8e61e5180c749e8a •>; span<2024-11-21 16:00:49 UTC>; h2<Access '
        'denied>; h2<What happened?>; p<The owner of this website (api.hollaex.com) '
        'has banned your IP address (123.123.123.123).>; div<Was this page helpful?>; '
        'div<Thank you for your feedback!>; span<Cloudflare Ray ID:>; '
        'strong<8e61e5180c749e8a>; span<Your IP:>; span<123.123.123.123>; '
        'span<Performance & security by>; a<Cloudflare>'
    )
    # invalid html
    assert html_util.get_html_summary_if_relevant("PLOPOPDS") == "PLOPOPDS"
    # non string
    assert html_util.get_html_summary_if_relevant(123) == "123"
    assert html_util.get_html_summary_if_relevant(Exception("plop")) == "plop"
    # raising error does not propagate
    with mock.patch.object(html_util, "summarize_page_content", mock.Mock(side_effect=Exception("err"))) \
        as summarize_page_content_mock:
        # not html
        assert html_util.get_html_summary_if_relevant("PLOPOPDS") == "PLOPOPDS"
        summarize_page_content_mock.assert_not_called()
        # html
        assert html_util.get_html_summary_if_relevant(
            "dfdsfsdfsd</html>", max_element_text_size=3
        ) == "dfdsfsdfsd</html>"
        summarize_page_content_mock.assert_called_once_with(
            "dfdsfsdfsd</html>", max_element_text_size=3
        )
    # raising error does not propagate
    with mock.patch.object(html_util, "pretty_print_summary", mock.Mock(side_effect=Exception("err"))) \
        as pretty_print_summary_mock:
        # not html
        assert html_util.get_html_summary_if_relevant("PLOPOPDS") == "PLOPOPDS"
        pretty_print_summary_mock.assert_not_called()
        # html
        assert html_util.get_html_summary_if_relevant("<html>dfdsfsdfsd</html>") == "<html>dfdsfsdfsd</html>"
        pretty_print_summary_mock.assert_called_once_with(
            [('html', 'dfdsfsdfsd')]
        )


def test_summarize_exception_html_cause_if_relevant():
    assert html_util.summarize_exception_html_cause_if_relevant(Exception("plop")) is None
    try:
        # lvl. 1
        try:
            # lvl. 2
            try:
                # lvl. 3
                try:
                    # lvl. 4
                    raise IndexError(RATE_LIMIT_HTML_WITH_MESSAGE)
                except IndexError as err_4:
                    assert err_4.__cause__ is None
                    assert "<script>" in str(err_4)
                    str_traceback = traceback.format_exc()
                    assert "<script>" in str_traceback
                    # does not crash if __cause__ is None
                    html_util.summarize_exception_html_cause_if_relevant(err_4)
                    str_traceback = traceback.format_exc()
                    assert "<script>" not in str_traceback
                    raise KeyError(html_util.get_html_summary_if_relevant(err_4)) from err_4
            except KeyError as err_3:
                # lvl. 3
                assert err_3.args == (
                    'message<hollaex GET https://api.sandbox.hollaex.com/v2/constants 403 '
                    'Forbidden>; title<Access denied | api.hollaex.com used Cloudflare to '
                    'restrict access>; div<Please enable cookies.>; span<Error>; span<1006>; '
                    'span<Ray ID: 8e61e5180c749e8a •>; span<2024-11-21 16:00:49 UTC>; h2<Access '
                    'denied>; h2<What happened?>; p<The owner of this website (api.hollaex.com) '
                    'has banned your IP address (123.123.123.123).>; div<Was this page helpful?>; '
                    'div<Thank you for your feedback!>; span<Cloudflare Ray ID:>; '
                    'strong<8e61e5180c749e8a>; span<Your IP:>; span<123.123.123.123>; '
                    'span<Performance & security by>; a<Cloudflare>',
                )
                # cause is not summarized
                assert "<script>" not in str(err_3.__cause__.args)
                html_util.summarize_exception_html_cause_if_relevant(err_3)
                # cause has been summarized
                assert err_3.__cause__.args == (
                    'message<hollaex GET https://api.sandbox.hollaex.com/v2/constants 403 '
                    'Forbidden>; title<Access denied | api.hollaex.com used Cloudflare to '
                    'restrict access>; div<Please enable cookies.>; span<Error>; span<1006>; '
                    'span<Ray ID: 8e61e5180c749e8a •>; span<2024-11-21 16:00:49 UTC>; h2<Access '
                    'denied>; h2<What happened?>; p<The owner of this website (api.hollaex.com) '
                    'has banned your IP address (123.123.123.123).>; div<Was this page helpful?>; '
                    'div<Thank you for your feedback!>; span<Cloudflare Ray ID:>; '
                    'strong<8e61e5180c749e8a>; span<Your IP:>; span<123.123.123.123>; '
                    'span<Performance & security by>; a<Cloudflare>',
                )
                raise NotImplementedError(err_3) from err_3
        except NotImplementedError as err_2:
            # lvl. 2
            assert err_2.args[0].args == (
                'message<hollaex GET https://api.sandbox.hollaex.com/v2/constants 403 '
                'Forbidden>; title<Access denied | api.hollaex.com used Cloudflare to '
                'restrict access>; div<Please enable cookies.>; span<Error>; span<1006>; '
                'span<Ray ID: 8e61e5180c749e8a •>; span<2024-11-21 16:00:49 UTC>; h2<Access '
                'denied>; h2<What happened?>; p<The owner of this website (api.hollaex.com) '
                'has banned your IP address (123.123.123.123).>; div<Was this page helpful?>; '
                'div<Thank you for your feedback!>; span<Cloudflare Ray ID:>; '
                'strong<8e61e5180c749e8a>; span<Your IP:>; span<123.123.123.123>; '
                'span<Performance & security by>; a<Cloudflare>',
            )
            assert err_2.__cause__.__cause__.__class__ == IndexError
            assert err_2.__cause__.__class__ == KeyError
            raise ZeroDivisionError from err_2
    except ZeroDivisionError as err_1:
        # lvl. 1
        assert "<script>" not in str(err_1)
        str_traceback = traceback.format_exc()
        assert "<script>" not in str_traceback

    # no summary at lower levels
    try:
        # lvl. 1
        try:
            # lvl. 2
            try:
                # lvl. 3
                try:
                    # lvl. 4
                    raise IndexError(RATE_LIMIT_HTML_WITH_MESSAGE)
                except IndexError as err_4:
                    raise KeyError(html_util.get_html_summary_if_relevant(err_4)) from err_4
            except KeyError as err_3:
                # lvl. 3
                raise NotImplementedError(err_3) from err_3
        except NotImplementedError as err_2:
            # lvl. 2
            raise ZeroDivisionError from err_2
    except ZeroDivisionError as err_1:
        # lvl. 1
        # summarized in error message
        assert "<script>" not in str(err_1)
        # not yet summarized in causes (used by traceback)
        str_traceback = traceback.format_exc()
        assert "<script>" in str_traceback

        # summarize
        html_util.summarize_exception_html_cause_if_relevant(err_1)
        str_traceback = traceback.format_exc()
        assert "<script>" not in str_traceback


RATE_LIMIT_INVALID_HTMLS = [
"""
<!DOCTYPE html>
<!--[if lt IE 7]> <html class="no-js ie6 oldie" lang="en-US"> <![endif]-->
<!--[if IE 7]>    <html class="no-js ie7 oldie" lang="en-US"> <![endif]-->
<!--[if IE 8]>    <html class="no-js ie8 oldie" lang="en-US"> <![endif]-->
<!--[if gt IE 8]><!--> <html class="no-js" lang="en-US"> <!--<![endif]-->
<head>
</html>
""",
"""
PLOP
</html>
""",
"""
</ll>
PLOP
</html>
""",
]

RATE_LIMIT_HTML = """
<!DOCTYPE html>
<!--[if lt IE 7]> <html class="no-js ie6 oldie" lang="en-US"> <![endif]-->
<!--[if IE 7]>    <html class="no-js ie7 oldie" lang="en-US"> <![endif]-->
<!--[if IE 8]>    <html class="no-js ie8 oldie" lang="en-US"> <![endif]-->
<!--[if gt IE 8]><!--> <html class="no-js" lang="en-US"> <!--<![endif]-->
<head>
<title>Access denied | api.hollaex.com used Cloudflare to restrict access</title>
<meta charset="UTF-8" />
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta http-equiv="X-UA-Compatible" content="IE=Edge" />
<meta name="robots" content="noindex, nofollow" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<link rel="stylesheet" id="cf_styles-css" href="/cdn-cgi/styles/main.css" />


<script>
(function(){if(document.addEventListener&&window.XMLHttpRequest&&JSON&&JSON.stringify){var e=function(a){var c=document.getElementById("error-feedback-survey"),d=document.getElementById("error-feedback-success"),b=new XMLHttpRequest;a={event:"feedback clicked",properties:{errorCode:1006,helpful:a,version:1}};b.open("POST","https://sparrow.cloudflare.com/api/v1/event");b.setRequestHeader("Content-Type","application/json");b.setRequestHeader("Sparrow-Source-Key","c771f0e4b54944bebf4261d44bd79a1e");
b.send(JSON.stringify(a));c.classList.add("feedback-hidden");d.classList.remove("feedback-hidden")};document.addEventListener("DOMContentLoaded",function(){var a=document.getElementById("error-feedback"),c=document.getElementById("feedback-button-yes"),d=document.getElementById("feedback-button-no");"classList"in a&&(a.classList.remove("feedback-hidden"),c.addEventListener("click",function(){e(!0)}),d.addEventListener("click",function(){e(!1)}))})}})();
</script>

<script defer src="https://performance.radar.cloudflare.com/beacon.js"></script>
</head>
<body>
  <div id="cf-wrapper">
    <div class="cf-alert cf-alert-error cf-cookie-error hidden" id="cookie-alert" data-translate="enable_cookies">Please enable cookies.</div>
    <div id="cf-error-details" class="p-0">
      <header class="mx-auto pt-10 lg:pt-6 lg:px-8 w-240 lg:w-full mb-15 antialiased">
         <h1 class="inline-block md:block mr-2 md:mb-2 font-light text-60 md:text-3xl text-black-dark leading-tight">
           <span data-translate="error">Error</span>
           <span>1006</span>
         </h1>
         <span class="inline-block md:block heading-ray-id font-mono text-15 lg:text-sm lg:leading-relaxed">Ray ID: 8e61e5180c749e8a &bull;</span>
         <span class="inline-block md:block heading-ray-id font-mono text-15 lg:text-sm lg:leading-relaxed">2024-11-21 16:00:49 UTC</span>
        <h2 class="text-gray-600 leading-1.3 text-3xl lg:text-2xl font-light">Access denied</h2>
      </header>

      <section class="w-240 lg:w-full mx-auto mb-8 lg:px-8">
          <div id="what-happened-section" class="w-1/2 md:w-full">
            <h2 class="text-3xl leading-tight font-normal mb-4 text-black-dark antialiased" data-translate="what_happened">What happened?</h2>
            <p>The owner of this website (api.hollaex.com) has banned your IP address (123.123.123.123).</p>

          </div>


      </section>

      <div class="feedback-hidden py-8 text-center" id="error-feedback">
    <div id="error-feedback-survey" class="footer-line-wrapper">
        Was this page helpful?
        <button class="border border-solid bg-white cf-button cursor-pointer ml-4 px-4 py-2 rounded" id="feedback-button-yes" type="button">Yes</button>
        <button class="border border-solid bg-white cf-button cursor-pointer ml-4 px-4 py-2 rounded" id="feedback-button-no" type="button">No</button>
    </div>
    <div class="feedback-success feedback-hidden" id="error-feedback-success">
        Thank you for your feedback!
    </div>
</div>


      <div class="cf-error-footer cf-wrapper w-240 lg:w-full py-10 sm:py-4 sm:px-8 mx-auto text-center sm:text-left border-solid border-0 border-t border-gray-300">
  <p class="text-13">
    <span class="cf-footer-item sm:block sm:mb-1">Cloudflare Ray ID: <strong class="font-semibold">8e61e5180c749e8a</strong></span>
    <span class="cf-footer-separator sm:hidden">&bull;</span>
    <span id="cf-footer-item-ip" class="cf-footer-item hidden sm:block sm:mb-1">
      Your IP:
      <button type="button" id="cf-footer-ip-reveal" class="cf-footer-ip-reveal-btn">Click to reveal</button>
      <span class="hidden" id="cf-footer-ip">123.123.123.123</span>
      <span class="cf-footer-separator sm:hidden">&bull;</span>
    </span>
    <span class="cf-footer-item sm:block sm:mb-1"><span>Performance &amp; security by</span> <a rel="noopener noreferrer" href="https://www.cloudflare.com/5xx-error-landing" id="brand_link" target="_blank">Cloudflare</a></span>

  </p>
  <script>(function(){function d(){var b=a.getElementById("cf-footer-item-ip"),c=a.getElementById("cf-footer-ip-reveal");b&&"classList"in b&&(b.classList.remove("hidden"),c.addEventListener("click",function(){c.classList.add("hidden");a.getElementById("cf-footer-ip").classList.remove("hidden")}))}var a=document;document.addEventListener&&a.addEventListener("DOMContentLoaded",d)})();</script>
</div><!-- /.error-footer -->


    </div><!-- /#cf-error-details -->
  </div><!-- /#cf-wrapper -->

  <script>
  window._cf_translation = {};


</script>

</body>
</html>
"""
RATE_LIMIT_HTML_WITH_MESSAGE = \
    f"hollaex GET https://api.sandbox.hollaex.com/v2/constants 403 Forbidden {RATE_LIMIT_HTML}"