import unittest

from apps.formulator.helpers import custom_sort_key


class TestFormulaSortKey(unittest.TestCase):
    """Unit tests for formula_view_report_custom_sort_key."""

    def test_empty_and_whitespace(self):
        self.assertEqual(custom_sort_key(""), (3, [(False, '')]))
        self.assertEqual(custom_sort_key(" "), (0, ' '))

    def test_numeric_strings(self):
        self.assertEqual(custom_sort_key("123"), (1, 123.0))
        self.assertEqual(custom_sort_key("42.5"), (1, 42.5))

    def test_alphanumeric_strings(self):
        self.assertEqual(
            custom_sort_key("A42"),
            (3, [(False, "a"), (True, 42.0), (False, '')]),
        )
        self.assertEqual(
            custom_sort_key("hello123world"),
            (3, [(False, "hello"), (True, 123.0), (False, "world")]),
        )

    def test_special_characters(self):
        self.assertEqual(
            custom_sort_key("!!!!"),
            (0, '!!!!'),
        )
        self.assertEqual(
            custom_sort_key("#$%@!"),
            (0, '#$%@!'),
        )

    def test_mixed_strings(self):
        self.assertEqual(
            custom_sort_key("abc!!!123"),
            (
                3,
                [
                    (False, 'abc'),
                    (False, '!'),
                    (False, ''),
                    (False, '!'),
                    (False, ''),
                    (False, '!'),
                    (False, ''),
                    (True, 123.0),
                    (False, ''),
                ],
            ),
        )
        self.assertEqual(
            custom_sort_key("10...9"),
            (2, ["", 10.0, "...", 9.0, ""]),
        )

if __name__ == '__main__':
    unittest.main()