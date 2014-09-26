from datetime import datetime
from copy import deepcopy
from portality.models import Journal, Article

class OAIPMHRecord(object):
    earliest = {
        "query": {
            "bool": {
                "must": [
                    { "term": { "admin.in_doaj": True } }
                ]
            }
        },
        "size": 0,
        "facets": {
            "earliest": {
                "terms": {
                    "field": "last_updated",
                    "order": "term"
                }
            }
        }
    }

    sets = {
        "query": {
            "bool": {
                "must": [
                    { "term": { "admin.in_doaj": True } }
                ]
            }
        },
        "size": 0,
        "facets": {
            "sets": {
                "terms": {
                    "field": "index.schema_subject.exact",
                    "order": "term",
                    "size": 100000
                }
            }
        }
    }

    records = {
        "query": {
            "bool": {
                "must": [
                    { "term": { "admin.in_doaj": True } }
                ]
            }
        },
        "from": 0,
        "size": 25
    }

    set_limit = {"term" : { "index.schema_subject.exact" : "<set name>" }}
    range_limit = { "range" : { "last_updated" : {"gte" : "<from date>", "lte" : "<until date>"} } }
    created_sort = {"last_updated" : {"order" : "desc"}}

    def earliest_datestamp(self):
        result = self.query(q=self.earliest)
        dates = [t.get("term") for t in result.get("facets", {}).get("earliest", {}).get("terms", [])]
        for d in dates:
            if d > 0:
                return datetime.fromtimestamp(d / 1000.0).strftime("%Y-%m-%dT%H:%M:%SZ")
        return None

    def identifier_exists(self, identifier):
        obj = self.pull(identifier)
        return obj is not None

    def list_sets(self):
        result = self.query(q=self.sets)
        sets = [t.get("term") for t in result.get("facets", {}).get("sets", {}).get("terms", [])]
        return sets

    def list_records(self, from_date=None, until_date=None, oai_set=None, list_size=None, start_number=None):
        q = deepcopy(self.records)
        if from_date is not None or until_date is not None or oai_set is not None:

            if oai_set is not None:
                s = deepcopy(self.set_limit)
                s["term"]["index.schema_subject.exact"] = oai_set
                q["query"]["bool"]["must"].append(s)

            if until_date is not None or from_date is not None:
                d = deepcopy(self.range_limit)

                if until_date is not None:
                    d["range"]["last_updated"]["lte"] = until_date
                else:
                    del d["range"]["last_updated"]["lte"]

                if from_date is not None:
                    d["range"]["last_updated"]["gte"] = from_date
                else:
                    del d["range"]["last_updated"]["gte"]

                q["query"]["bool"]["must"].append(d)

        if list_size is not None:
            q["size"] = list_size

        if start_number is not None:
            q["from"] = start_number

        q["sort"] = [deepcopy(self.created_sort)]

        # do the query
        # print json.dumps(q)
        results = self.query(q=q)

        total = results.get("hits", {}).get("total", 0)
        return total, [hit.get("_source") for hit in results.get("hits", {}).get("hits", [])]


class OAIPMHArticle(OAIPMHRecord, Article):
    def list_records(self, from_date=None, until_date=None, oai_set=None, list_size=None, start_number=None):
        total, results = super(OAIPMHArticle, self).list_records(from_date=from_date,
            until_date=until_date, oai_set=oai_set, list_size=list_size, start_number=start_number)
        return total, [Article(**r) for r in results]

    def pull(self, identifier):
        # override the default pull, as we care about whether the item is in_doaj
        record = super(OAIPMHArticle, self).pull(identifier)
        if record is not None and record.is_in_doaj():
            return record
        return None

class OAIPMHJournal(OAIPMHRecord, Journal):
    def list_records(self, from_date=None, until_date=None, oai_set=None, list_size=None, start_number=None):
        total, results = super(OAIPMHJournal, self).list_records(from_date=from_date,
            until_date=until_date, oai_set=oai_set, list_size=list_size, start_number=start_number)
        return total, [Journal(**r) for r in results]

    def pull(self, identifier):
        # override the default pull, as we care about whether the item is in_doaj
        record = super(OAIPMHJournal, self).pull(identifier)
        if record is not None and record.is_in_doaj():
            return record
        return None