# -*- coding: utf-8 -*-
from __future__ import absolute_import

from gcs_client import bucket
from gcs_client import common
from gcs_client.constants import projection as gcs_projection
from gcs_client.constants import storage_class


class Project(common.GCS):
    """GCS Project Object representation."""

    _required_attributes = common.GCS._required_attributes + ['project_id']

    def __init__(self, project_id, credentials=None, retry_params=None):
        """Initialize a Project object.

        :param project_id: Project id as listed in Google's project management
                           https://console.developers.google.com/project.
        :param credentials: A credentials object to authorize the connection.
        """
        super(Project, self).__init__(credentials, retry_params)
        self.project_id = project_id

    @property
    def default_bucket_name(self):
        if not self.project_id:
            return None
        return self.project_id + '.appspot.com'

    @common.is_complete
    @common.retry
    @common.convert_exception
    def list_buckets(self, fields_to_return=None, max_results=None,
                     projection=gcs_projection.SIMPLE):
        buckets = self._service.buckets()

        req = buckets.list(project=self.project_id,
                           fields=fields_to_return,
                           maxResults=max_results)

        bucket_list = []
        while req:
            resp = req.execute()
            items = map(
                lambda b: bucket.Bucket.obj_from_data(b, self.credentials),
                resp.get('items', []))
            bucket_list.extend(items)
            req = buckets.list_next(req, resp)

        return bucket_list

    @common.is_complete
    @common.retry
    @common.convert_exception
    def create_bucket(self, name, location='US',
                      storage_class=storage_class.NEARLINE,
                      predefined_acl=None,
                      predefined_default_obj_acl=None,
                      projection=gcs_projection.SIMPLE, **kwargs):
        kwargs['name'] = name
        kwargs['location'] = location
        kwargs['storageClass'] = storage_class

        req = self._service.buckets().insert(
            project=self.project_id,
            predefinedAcl=predefined_acl,
            predefinedDefaultObjectAcl=predefined_default_obj_acl,
            projection=projection,
            body=kwargs)

        resp = req.execute()
        return bucket.Bucket.obj_from_data(resp, self.credentials)
