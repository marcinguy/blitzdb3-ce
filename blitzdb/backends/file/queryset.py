# The MIT License (MIT)
# 
# Copyright (c) 2014 Andreas Dewes
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import copy

from blitzdb.queryset import QuerySet as BaseQuerySet


class QuerySet(BaseQuerySet):
    def delete(self):
        collection = self.backend.get_collection_for_cls(self.cls)
        self.backend.delete_by_store_keys(collection, self.keys)
        self.keys = []
        self._i = 0
        self.objects = {}

    def filter(self, *args, **kwargs):
        return self.backend.filter(self.cls, *args, initial_keys=self.keys, **kwargs)

    def filter_by_key(self, key, expression):
        return self.backend.filter_by_key(self.cls, expression, initial_keys=self.keys)

    def _clone(self, keys):
        return self.__class__(self.backend, self.cls, self.store, copy.copy(keys))

    def next(self):
        if self._i >= len(self):
            raise StopIteration

        self._i += 1
        return self[self._i - 1]

    __next__ = next

    def rewind(self):
        self._i = 0

    def sort(self, key, order=BaseQuerySet.ASCENDING):
        self.keys = self.backend.sort(self.cls, self.keys, key, order)
        return self

    def __init__(self, backend, cls, store, keys):
        super().__init__(backend, cls)
        self.store = store
        self.keys = list(keys)
        self.objects = {}
        self.rewind()

    def __getitem__(self, i):
        if isinstance(i, slice):
            return self.__class__(self.backend, self.cls, self.store, self.keys[i])

        key = self.keys[i]
        if key not in self.objects:
            self.objects[key] = self.backend.get_object(self.cls, key)
            self.objects[key]._store_key = key
        return self.objects[key]

    def __and__(self, other):
        return self._clone(set(self.keys) & set(other.keys))

    def __or__(self, other):
        return self._clone(set(self.keys) | set(other.keys))

    def __len__(self):
        return len(self.keys)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __invert__(self):
        collection = self.backend.get_collection_for_cls(self.cls)
        pk_index = self.backend.get_pk_index(collection)
        all_keys = pk_index.get_all_keys()
        keys = [key for key in all_keys if key not in self.keys]
        return self._clone(keys)

    def __contains__(self, obj):
        if not isinstance(obj, list) and not isinstance(obj, tuple):
            obj_list = [obj]
        else:
            obj_list = obj
        for obj in obj_list:
            try:
                storage_key = self.backend.get_storage_key_for(obj)
            except obj.DoesNotExist:
                return False

            if storage_key not in self.keys:
                return False

        return True

    def __eq__(self, other):
        if isinstance(other, QuerySet):
            if self.cls == other.cls and set(self.keys) == set(other.keys):
                return True

        elif isinstance(other, list):
            if len(other) != len(self.keys):
                return False

            objs = list(self)
            if other == objs:
                return True

        return False
