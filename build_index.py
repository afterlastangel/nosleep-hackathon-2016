from elasticsearch import Elasticsearch
from google.appengine.api import search


def delete_all_in_index(index):
    # index.get_range by returns up to 100 documents at a time, so we must
    # loop until we've deleted all items.
    while True:
        # Use ids_only to get the list of document IDs in the index without
        # the overhead of getting the entire document.
        document_ids = [
            document.doc_id
            for document
            in index.get_range(ids_only=True)]

        # If no IDs were returned, we've deleted everything.
        if not document_ids:
            break

        # Delete the documents for the given IDs
        index.delete(document_ids)


def add_document_to_index(index_name, document):
    index = search.Index(index_name)
    index.put(document)


def query_index(search):
    results = index.search(query_string)
    for scored_document in results:
        print(scored_document)


def upload_dictionary(index_name, dictionary):
    delete_all_in_index(index_name)
    for doc in dictionary :
        add_document_to_index(doc)

def process_file(index_name, fileobject):
    index_name = 'elastic_search'











