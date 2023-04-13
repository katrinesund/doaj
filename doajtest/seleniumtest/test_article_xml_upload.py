import time
from pathlib import Path
from time import sleep
from typing import Type, Union

from parameterized import parameterized
from selenium.webdriver.common.by import By

from doajtest import selenium_helpers
from doajtest.fixtures import JournalFixtureFactory, AccountFixtureFactory, url_path, article_doajxml
from doajtest.fixtures.article_doajxml import ARTICLE_UPLOAD_SUCCESSFUL
from doajtest.fixtures.url_path import URL_PUBLISHER_UPLOADFILE
from doajtest.selenium_helpers import SeleniumTestCase
from portality import models, dao


def get_latest(domain_obj: Union[Type[dao.DomainObject], dao.DomainObject]):
    obj = domain_obj.iterate({
        "sort": [{"created_date": {"order": "desc"}}],
        "size": 1,
    })
    return next(obj, None)


class ArticleXmlUploadSTC(SeleniumTestCase):

    def goto_upload_page(self, acc: models.Account = None):
        if acc:
            publisher = acc
        else:
            publisher = models.Account(**AccountFixtureFactory.make_publisher_source())
        selenium_helpers.login_by_acc(self.selenium, publisher)
        selenium_helpers.goto(self.selenium, URL_PUBLISHER_UPLOADFILE)
        return publisher

    def upload_submit_file(self, file_path):
        self.selenium.find_element(By.ID, 'upload-xml-file').send_keys(file_path)
        self.selenium.find_element(By.ID, 'upload_form').submit()

    def test_without_file(self):
        """ similar to "Try uploading without providing a file" from testbook """
        self.goto_upload_page()
        self.selenium.find_element(By.ID, 'upload_form').submit()

        assert 'You must specify the file or upload from a link' in self.selenium.find_element(
            By.CSS_SELECTOR, '.form__question .error').text

    @parameterized.expand([
        # case "Upload a file which is not XML"
        (article_doajxml.NON_XML_FILE, 'Unable to parse XML file'),
        # case "Upload an XML file which does not meet the DOAJ schema"
        (article_doajxml.SCHEMA_INVALID, 'Unable to validate document with identified schema'),
        # case "Upload a malformed XML file"
        (article_doajxml.XML_MALFORMED, 'Unable to parse XML file'),
    ])
    def test_upload_fail(self, file_path, err_msg):
        """ cases about upload article failed with error message """
        self.goto_upload_page()
        self.upload_submit_file(file_path)

        alert_ele = self.selenium.find_element(By.CSS_SELECTOR, '.alert--message')
        assert alert_ele
        assert err_msg in alert_ele.text

        for _ in range(3):
            time.sleep(0.5) # wait for es update history of uploads
            self.selenium.refresh()
            rows = find_history_rows(self.selenium)
            if rows:
                break

        assert rows
        history_row_text = rows[0].text
        assert Path(file_path).name in history_row_text
        assert 'processing failed' in history_row_text

    def test_new_article_success(self):
        """ similar to "Successfully upload a file containing a new article" from testbook """

        publisher = models.Account(**AccountFixtureFactory.make_publisher_source())

        journal = models.Journal(**JournalFixtureFactory.make_journal_source(in_doaj=True))
        journal.set_owner(publisher.id)
        bib = journal.bibjson()
        bib.pissn = '1111-1111'
        bib.eissn = '2222-2222'
        journal.bibjson().is_replaced_by = []
        journal.bibjson().replaces = []
        journal.save(blocking=True)

        self.goto_upload_page(acc=publisher)

        # goto upload page and upload article xml file
        selenium_helpers.goto(self.selenium, URL_PUBLISHER_UPLOADFILE)

        n_file_upload = models.FileUpload.count()
        n_org_rows = len(find_history_rows(self.selenium))
        self.upload_submit_file(ARTICLE_UPLOAD_SUCCESSFUL)

        new_rows = find_history_rows(self.selenium)
        assert n_org_rows + 1 == len(new_rows)
        assert 'pending' in new_rows[0].text
        assert n_file_upload + 1 == models.FileUpload.count()

        sleep(14)  # wait for background job to finish

        new_file_upload: models.FileUpload = get_latest(models.FileUpload)

        # trigger upload article background job by function call
        print(new_file_upload)
        assert new_file_upload.filename == Path(ARTICLE_UPLOAD_SUCCESSFUL).name
        assert new_file_upload.status == 'processed'

        # back to /publisher/uploadfile check status updated
        selenium_helpers.goto(self.selenium, URL_PUBLISHER_UPLOADFILE)
        new_rows = find_history_rows(self.selenium)
        assert 'successfully processed 1 articles imported' in new_rows[0].text

        selenium_helpers.goto(self.selenium, url_path.url_toc(bib.eissn))
        assert 'The Title' in self.selenium.find_element(
            By.CSS_SELECTOR, 'main.page-content header h1').text


def find_history_rows(driver):
    return driver.find_elements(By.CSS_SELECTOR, "#previous_files tbody tr")
