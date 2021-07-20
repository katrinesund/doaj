from parameterized import parameterized
from combinatrix.testintegration import load_parameter_sets

from doajtest.fixtures import JournalFixtureFactory
from doajtest.helpers import DoajTestCase
from portality.bll import DOAJ
from portality.bll import exceptions
from portality import models
from portality.lib.paths import rel2abs
from portality.core import app
from doajtest.mocks.store import StoreMockFactory
from doajtest.mocks.models_Cache import ModelCacheMockFactory
from portality import store
from io import StringIO
import os, shutil
from lxml import etree


def load_cases():
    return load_parameter_sets(rel2abs(__file__, "..", "matrices", "bll_sitemap"), "sitemap", "test_id",
                               {"test_id" : []})


EXCEPTIONS = {
    "ArgumentException" : exceptions.ArgumentException,
    "IOError" : IOError
}


class TestBLLSitemap(DoajTestCase):

    def setUp(self):
        super(TestBLLSitemap, self).setUp()
        self.svc = DOAJ.siteService()

        self.store_tmp_dir = app.config["STORE_TMP_DIR"]
        app.config["STORE_TMP_DIR"] = os.path.join("test_store", "tmp")
        self.store_local_dir = app.config["STORE_LOCAL_DIR"]
        app.config["STORE_LOCAL_DIR"] = os.path.join("test_store", "main")

        self.localStore = store.StoreLocal(None)
        self.tmpStore = store.TempStore()
        self.container_id = app.config.get("STORE_CACHE_CONTAINER")
        self.store_tmp_impl = app.config["STORE_TMP_IMPL"]
        self.store_impl = app.config["STORE_IMPL"]

        self.cache = models.cache.Cache
        models.cache.Cache = ModelCacheMockFactory.in_memory()
        models.Cache = models.cache.Cache

        self.toc_changefreq = app.config["TOC_CHANGEFREQ"]
        app.config["TOC_CHANGEFREQ"] = "daily"

        self.static_pages = app.config["STATIC_PAGES"]
        app.config["STATIC_PAGES"] = [
            ("/about", "monthly"),
            ("supporters", "weekly")
        ]

    def tearDown(self):
        app.config["STORE_TMP_IMPL"] = self.store_tmp_impl
        app.config["STORE_IMPL"] = self.store_impl
        if os.path.exists("test_store"):
            shutil.rmtree("test_store")
        self.localStore.delete_container(self.container_id)
        self.tmpStore.delete_container(self.container_id)

        models.cache.Cache = self.cache
        models.Cache = self.cache

        app.config["TOC_CHANGEFREQ"] = self.toc_changefreq
        app.config["STATIC_PAGES"] = self.static_pages

        super(TestBLLSitemap, self).tearDown()

    @parameterized.expand(load_cases)
    def test_sitemap(self, name, kwargs):

        prune_arg = kwargs.get("prune")
        tmp_write_arg = kwargs.get("tmp_write")
        main_write_arg = kwargs.get("main_write")
        raises_arg = kwargs.get("raises")

        ###############################################
        ## set up

        raises = EXCEPTIONS.get(raises_arg)
        prune = True if prune_arg == "True" else False if prune_arg == "False" else None

        if tmp_write_arg == "fail":
            app.config["STORE_TMP_IMPL"] = StoreMockFactory.no_writes_classpath()

        if main_write_arg == "fail":
            app.config["STORE_IMPL"] = StoreMockFactory.no_writes_classpath()

        journals = []
        for s in JournalFixtureFactory.make_many_journal_sources(count=10, in_doaj=True):
            j = models.Journal(**s)
            j.save()
            journals.append(j)
        models.Journal.blockall([(j.id, j.last_updated) for j in journals])

        expectations = [(j.bibjson().get_preferred_issn(), j.last_updated) for j in journals]

        if prune:
            self.localStore.store(self.container_id, "sitemap__doaj_20180101_0000_utf8.xml", source_stream=StringIO("test1"))
            self.localStore.store(self.container_id, "sitemap__doaj_20180601_0000_utf8.xml", source_stream=StringIO("test2"))
            self.localStore.store(self.container_id, "sitemap__doaj_20190101_0000_utf8.xml", source_stream=StringIO("test3"))


        ###########################################################
        # Execution

        if raises is not None:
            with self.assertRaises(raises):
                self.svc.sitemap(prune)

                tempFiles = self.tmpStore.list(self.container_id)
                assert len(tempFiles) == 0, "expected 0, received {}".format(len(tempFiles))
        else:
            url, action_register = self.svc.sitemap(prune)
            assert url is not None

            # Check the results
            ################################
            sitemap_info = models.cache.Cache.get_latest_sitemap()
            assert sitemap_info.get("filename") == url

            filenames = self.localStore.list(self.container_id)
            if prune:
                assert len(filenames) == 2, "expected 0, received {}".format(len(filenames))
                assert "sitemap__doaj_20180101_0000_utf8.xml" not in filenames
                assert "sitemap__doaj_20180601_0000_utf8.xml" not in filenames
                assert "sitemap__doaj_20190101_0000_utf8.xml" in filenames
            else:
                assert len(filenames) == 1, "expected 0, received {}".format(len(filenames))

            latest = None
            for fn in filenames:
                if fn != "sitemap__doaj_20190101_0000_utf8.xml":
                    latest = fn
                    break

            handle = self.localStore.get(self.container_id, latest, encoding="utf-8")

            # check the contents

            tocs = []
            statics = []
            NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

            tree = etree.parse(handle)
            urlElements = tree.getroot().getchildren()
            for urlElement in urlElements:
                loc = urlElement.find(NS + "loc").text
                lm = urlElement.find(NS + "lastmod")
                if lm is not None:
                    lm = lm.text
                cf = urlElement.find(NS + "changefreq").text

                if "/toc" in loc:
                    for exp in expectations:
                        if loc.endswith(exp[0]):
                            tocs.append(exp[0])
                            assert lm == exp[1]
                            assert cf == "daily"
                else:
                    for static in app.config["STATIC_PAGES"]:
                        if loc.endswith(static[0]):
                            statics.append(static[0])
                            assert lm is None
                            assert cf == static[1]


            # deduplicate the list of tocs, to check that we saw all journals
            list(set(tocs))
            assert len(tocs) == len(expectations)

            # deduplicate the statics, to check we saw all of them too
            list(set(statics))
            assert len(statics) == len(app.config["STATIC_PAGES"])




