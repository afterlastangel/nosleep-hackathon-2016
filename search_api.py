from google.appengine.api import search
from decorators import task


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

        print document_ids
        # Delete the documents for the given IDs
        index.delete(document_ids)


def query_index(index_name, keywords):
    index = search.Index(index_name)
    querystring = ' OR '.join(keywords)
    print '=================='
    print querystring
    print '=================='
    search_query = search.Query(
              query_string=querystring,
              options=search.QueryOptions(
                            limit=5))
    results = index.search(search_query)
    fields = []
    for scored_document in results:
        fields += [scored_document.fields[0].value]
    return fields


def process_delete_index(index_name):
    index = search.Index(index_name)
    delete_all_in_index(index)


@task
def process_upload_dictionary(index_name, fileobject):
    index = search.Index(index_name)
    for line in fileobject:
        index.put(search.Document(
            fields=[
                search.TextField(name='sentence', value=line)
            ]
        ))
