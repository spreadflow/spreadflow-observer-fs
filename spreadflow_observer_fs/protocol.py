from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
import hashlib
from bson import BSON


class Repository(object):

    def __init__(self):
        self._repo = set()


    def replace(self, repo):
        inserted = repo - self._repo
        deleted = self._repo - repo
        self._repo = repo

        return (deleted, inserted)


    def update(self, deletes, inserts):
        masked_paths = set(deletes + tuple(path for path, oid in inserts))
        repo = set([(path, oid) for path, oid in self._repo if path not in masked_paths] + inserts)
        return self.replace(repo)


class MessageFactory(object):

    CHUNK_SIZE = 8

    def __init__(self, port_name = 'default'):
        self.port_name = port_name
        self._repository = Repository()


    def _metadata_generate_oids(self, metadata):
        return tuple(hashlib.sha1(repr(meta)).hexdigest() for meta in metadata)


    def _metadata_generate_uris(self, paths):
        return tuple({'path': path} for path in paths)


    def _metadata_merge(self, *args):
        return tuple(reduce(lambda x, y: dict(x.items() + y.items()), dicts, {}) for dicts in zip(*args))

    def _construct_message(self, deleted_objects, inserted_objects, insertable_oids, insertable_meta):
        deleted_oids = ()
        inserted_oids = ()
        metadata = ()

        if deleted_objects:
            (deleted_paths, deleted_oids) = zip(*deleted_objects)
            metadata += tuple(zip(deleted_oids, self._metadata_generate_uris(deleted_paths)))

        if inserted_objects:
            (inserted_paths, inserted_oids) = zip(*inserted_objects)
            metadata += tuple((oid, meta) for oid, meta in zip(insertable_oids, insertable_meta) if oid in inserted_oids)

        item = {
            'type': 'delta',
            'date': datetime.datetime.now(),
            'deletes': deleted_oids,
            'inserts': inserted_oids,
            'data': dict(metadata)
        }

        msg = {
            'port': self.port_name,
            'item': item
        }

        return BSON.encode(msg)


    def _generate_messages(self, deleted_objects, inserted_objects, insertable_oids, insertable_meta):
        if len(deleted_objects) + len(inserted_objects) > self.CHUNK_SIZE:
            for i in xrange(0, len(deleted_objects), self.CHUNK_SIZE):
                yield self._construct_message(deleted_objects[i:i+self.CHUNK_SIZE], (), insertable_oids, insertable_meta)
            for i in xrange(0, len(inserted_objects), self.CHUNK_SIZE):
                yield self._construct_message((), inserted_objects[i:i+self.CHUNK_SIZE], insertable_oids, insertable_meta)
        elif len(deleted_objects) + len(inserted_objects) > 0:
            yield self._construct_message(deleted_objects, inserted_objects, insertable_oids, insertable_meta)


    def replace(self, paths, metadata):
        uri_metadata = self._metadata_generate_uris(paths)
        merged_metadata = self._metadata_merge(metadata, uri_metadata)
        oids = self._metadata_generate_oids(merged_metadata)

        (deleted_objects, inserted_objects) = self._repository.replace(set(zip(paths, oids)))
        return self._generate_messages(tuple(deleted_objects), tuple(inserted_objects), oids, merged_metadata)


    def update(self, deletable_paths, insertable_paths, insertable_meta):
        uri_metadata = self._metadata_generate_uris(insertable_paths)
        merged_metadata = self._metadata_merge(insertable_meta, uri_metadata)
        oids = self._metadata_generate_oids(merged_metadata)

        (deleted_objects, inserted_objects) = self._repository.update(deletable_paths, zip(insertable_paths, oids))
        return self._generate_messages(tuple(deleted_objects), tuple(inserted_objects), oids, merged_metadata)
