from elasticsearch import Elasticsearch


es = Elasticsearch(
    ['http://2e11690033ef9f1a7d1149b3d7034348.us-east-1.aws.found.io:9200/'],
    http_auth=('admin', 'admin')
)


def query_index(index_name, keywords):
    return {}


def process_delete_index(index_name):
    es.indices.delete(index_name)


def process_upload_dictionary(index_name, fileobject):
    es.indices.create(index=index_name)

    for line in fileobject:
        doc = {'sentence': line}
        es.index(index=index_name, doc_type='dictionary', body=doc)
