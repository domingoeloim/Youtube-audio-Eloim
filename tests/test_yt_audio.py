import unittest

import index


class MediaUrlTests(unittest.TestCase):
    def test_keeps_http_url(self):
        url = "https://www.youtube.com/watch?v=example"
        self.assertEqual(index.media_url(url), url)

    def test_converts_search_to_youtube_search(self):
        self.assertEqual(index.media_url("lofi radio"), "ytsearch1:lofi radio")

    def test_rejects_empty_query(self):
        with self.assertRaises(index.PlayerError):
            index.media_url("  ")


if __name__ == "__main__":
    unittest.main()
