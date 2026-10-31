import os, sqlite3, tempfile, unittest
import selection_judge as j

class T(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp(); j.LOGDB = os.path.join(d, "j.db"); self.links = os.path.join(d, "inbox.tsv"); self.rung = []

    def run_(self, text, choose_fn):
        return j.judge(text, choose_fn=choose_fn, links=self.links, ring=self.rung.append, explain=lambda s: "it does X")

    def rows(self):
        return sqlite3.connect(j.LOGDB).execute("select kind, route, chars, jev_ok from Judge").fetchall()

    def test_link_kinds_no_jev(self):
        for url, kind in (("https://github.com/a/b", "github"), ("https://youtu.be/x", "youtube"), ("https://example.com/p", "web")):
            self.assertEqual(self.run_(" %s \n" % url, lambda *a: self.fail("Jev called"))[:2], (kind, "links"))
        self.assertEqual(len(open(self.links).read().splitlines()), 3)
        self.assertEqual(open(self.links).read().splitlines()[0].split("\t")[1:3], ["github", "https://github.com/a/b"])

    def test_url_inside_prose_is_not_a_link(self):
        self.assertEqual(self.run_("see https://github.com/a/b now", lambda *a: "no")[:2], ("text", "chat"))

    def test_messy_urls_still_links(self):
        for raw, kind in (("https://github.com/a/b.", "github"), ("<https://youtu.be/x>", "youtube"),
                          ("[repo](https://github.com/a/b)", "github"), ("github.com/a/b\n", "github"),
                          ("\"https://example.com/p\"", "web"), ("www.example.com/x", "web")):
            self.assertEqual(self.run_(raw, lambda *a: self.fail("Jev called"))[0], kind, raw)
        self.assertTrue(open(self.links).read().splitlines()[0].split("\t")[2].startswith("https://"))

    def test_code_goes_to_explain(self):
        self.assertEqual(self.run_("ls -la | wc -l", lambda *a: "yes"), ("code", "explain", "it does X"))

    def test_else_and_jev_down_go_to_chat(self):
        self.assertEqual(self.run_("fix the build", lambda *a: "no")[:2], ("text", "chat"))
        def boom(*a): raise RuntimeError("jev down")
        self.assertEqual(self.run_("ls -la", boom)[:2], ("text", "chat"))
        self.assertEqual(len(self.rung), 2)
        self.assertEqual(self.rows()[-1], ("text", "chat", 6, 0))

if __name__ == "__main__":
    unittest.main()
