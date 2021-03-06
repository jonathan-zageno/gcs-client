#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

"""
test_base
----------------------------------

Tests base classes
"""
import unittest

import mock

from gcs_client import base
from gcs_client import common
from gcs_client import errors as gcs_errors


class TestGCS(unittest.TestCase):
    """Test Google Cloud Service base class."""

    def setUp(self):
        self.test_class = base.GCS

    def test_init(self):
        """Test init."""
        # NOTE(geguileo): We store gcs on the instance so Fillable tests can
        # use it.
        self.gcs = self.test_class(mock.sentinel.credentials)
        self.assertEqual(mock.sentinel.credentials, self.gcs.credentials)
        self.assertIs(common.RetryParams.get_default(), self.gcs._retry_params)

    def test_set_credentials(self):
        """Test setting credentials."""
        gcs = self.test_class(None)
        gcs.credentials = mock.sentinel.new_credentials
        self.assertEqual(mock.sentinel.new_credentials, gcs.credentials)

    def test_set_same_credentials(self):
        """Test setting the same credentials."""
        gcs = self.test_class(mock.sentinel.credentials)
        gcs.credentials = mock.sentinel.credentials
        self.assertEqual(mock.sentinel.credentials, gcs.credentials)

    def test_get_retry_params(self):
        """Test retry_params getter method."""
        gcs = self.test_class(mock.sentinel.credentials)
        self.assertIs(common.RetryParams.get_default(), gcs._retry_params)
        self.assertIs(common.RetryParams.get_default(), gcs.retry_params)

    def test_set_retry_params_to_none(self):
        """Test retry_params setter method with None value."""
        gcs = self.test_class(mock.sentinel.credentials)
        gcs.retry_params = None
        self.assertIs(None, gcs.retry_params)

    def test_set_retry_params(self):
        """Test retry_params setter method with RetryParams instance."""
        gcs = self.test_class(mock.sentinel.credentials)
        new_params = common.RetryParams()
        gcs.retry_params = new_params
        self.assertIsNot(common.RetryParams.get_default(), gcs.retry_params)
        self.assertIs(new_params, gcs.retry_params)

    def test_set_retry_params_incorrect_value(self):
        """Test retry_params setter method with incorrect value."""
        gcs = self.test_class(mock.sentinel.credentials)
        self.assertRaises(AssertionError, setattr, gcs, 'retry_params', 1)
        self.assertIs(common.RetryParams.get_default(), gcs.retry_params)

    @mock.patch('requests.request', **{'return_value.status_code': 200})
    @mock.patch('requests.utils.quote')
    def test_request_default_ok(self, quote_mock, request_mock):
        """Test _request method with default values."""
        creds = mock.Mock()
        gcs = self.test_class(creds)
        self.assertEqual(request_mock.return_value, gcs._request())
        request_mock.assert_called_once_with(
            'GET', self.test_class._URL, params={},
            headers={'Authorization': creds.authorization}, json=None)
        self.assertEqual(1, quote_mock.call_count)
        self.assertFalse(request_mock.return_value.json.called)

    def _request_setup_gcs(self, url):
        self.creds = mock.Mock()
        gcs = self.test_class(self.creds)
        setattr(gcs, 'size', 123)
        gcs._required_attributes = ['size']
        gcs._URL = url
        return gcs

    @mock.patch('requests.request', **{'return_value.status_code': 200})
    @mock.patch('requests.utils.quote')
    def test_request_default_ok_url_params(self, quote_mock, request_mock):
        """Test _request method with default values."""
        quote_mock.side_effect = lambda s, *args, **kwargs: s
        gcs = self._request_setup_gcs('url_{size}')

        self.assertEqual(request_mock.return_value, gcs._request())
        request_mock.assert_called_once_with(
            'GET', 'url_123', params={},
            headers={'Authorization': self.creds.authorization}, json=None)
        quote_mock.assert_called_once_with('123', safe='')
        self.assertFalse(request_mock.return_value.json.called)

    @mock.patch('requests.request', **{'return_value.status_code': 200})
    def test_request_url_without_params(self, request_mock):
        """Test _request method with an url that has no parameters."""
        url = 'url_456'
        gcs = self._request_setup_gcs(url)

        self.assertEqual(request_mock.return_value, gcs._request())
        request_mock.assert_called_once_with(
            'GET', url, params={},
            headers={'Authorization': self.creds.authorization}, json=None)
        self.assertFalse(request_mock.return_value.json.called)

    @mock.patch('requests.request', **{'return_value.status_code': 200})
    def test_request_url_with_params(self, request_mock):
        """Test _request method with an url that has parameters."""
        url = 'url_{nosize}'
        gcs = self._request_setup_gcs(url)
        setattr(gcs, 'nosize', 456)
        gcs._required_attributes += ['nosize']

        self.assertEqual(request_mock.return_value, gcs._request(url=url))
        request_mock.assert_called_once_with(
            'GET', 'url_456', params={},
            headers={'Authorization': self.creds.authorization}, json=None)
        self.assertFalse(request_mock.return_value.json.called)

    @mock.patch('requests.request', **{'return_value.status_code': 200})
    @mock.patch('requests.utils.quote')
    def test_request_url_no_formatting(self, quote_mock, request_mock):
        """Test _request method with an url and forcing no formatting."""
        url = 'url_{nosize}'
        gcs = self._request_setup_gcs(url)

        result = gcs._request(url=url, format_url=False)
        self.assertEqual(request_mock.return_value, result)
        request_mock.assert_called_once_with(
            'GET', url, params={},
            headers={'Authorization': self.creds.authorization}, json=None)
        quote_mock.assert_not_called()
        self.assertFalse(request_mock.return_value.json.called)

    @mock.patch('requests.request', **{'return_value.status_code': 404})
    @mock.patch('requests.utils')
    def test_request_default_error(self, utils_mock, request_mock):
        """Test _request method with default values."""
        creds = mock.Mock()
        gcs = self.test_class(creds)
        self.assertRaises(gcs_errors.NotFound, gcs._request)
        request_mock.assert_called_once_with(
            'GET', self.test_class._URL, params={},
            headers={'Authorization': creds.authorization}, json=None)
        self.assertEqual(1, utils_mock.quote.call_count)
        self.assertFalse(request_mock.return_value.json.called)

    @mock.patch('requests.request', **{'return_value.status_code': 203})
    @mock.patch('requests.utils.quote')
    def test_request_non_default_ok(self, quote_mock, request_mock):
        """Test _request method with default values."""
        creds = mock.Mock()
        gcs = self.test_class(creds)
        res = gcs._request(op=mock.sentinel.op, headers={'head': 'hello'},
                           body=mock.sentinel.body, parse=True, ok=(203,),
                           param1=mock.sentinel.param1)
        self.assertEqual(request_mock.return_value, res)
        request_mock.assert_called_once_with(
            mock.sentinel.op, self.test_class._URL,
            params={'param1': mock.sentinel.param1},
            headers={'Authorization': creds.authorization, 'head': 'hello'},
            json=mock.sentinel.body)
        self.assertEqual(1, quote_mock.call_count)
        self.assertTrue(request_mock.return_value.json.called)

    @mock.patch('requests.request', **{'return_value.status_code': 200})
    @mock.patch('requests.utils.quote')
    def test_request_default_json_error(self, quote_mock, request_mock):
        """Test _request method with default values."""
        request_mock.return_value.json.side_effect = ValueError()
        creds = mock.Mock()
        gcs = self.test_class(creds)
        self.assertRaises(gcs_errors.Error, gcs._request, parse=True)
        request_mock.assert_called_once_with(
            'GET', self.test_class._URL, params={},
            headers={'Authorization': creds.authorization}, json=None)
        self.assertEqual(1, quote_mock.call_count)
        self.assertTrue(request_mock.return_value.json.called)

    @mock.patch('gcs_client.base.GCS._request')
    def test_exists(self, mock_request):
        """Test repr representation."""
        mock_request.return_value.status_code = 200
        obj = self.test_class(mock.Mock())
        self.assertTrue(obj.exists())
        mock_request.assert_called_once_with(op='HEAD')

    @mock.patch('gcs_client.base.GCS._request')
    def test_exists_not_found(self, mock_request):
        """Test repr representation."""
        mock_request.side_effect = gcs_errors.NotFound()
        obj = self.test_class(mock.Mock())
        self.assertFalse(obj.exists())
        mock_request.assert_called_once_with(op='HEAD')

    @mock.patch('gcs_client.base.GCS._request')
    def test_exists_bad_request(self, mock_request):
        """Test repr representation."""
        mock_request.side_effect = gcs_errors.BadRequest()
        obj = self.test_class(mock.Mock())
        self.assertFalse(obj.exists())
        mock_request.assert_called_once_with(op='HEAD')


class TestFillable(TestGCS):
    """Test Fillable class."""

    def setUp(self):
        self.test_class = base.Fillable

    def test_init(self):
        """Variables are initialized correctly."""
        super(TestFillable, self).test_init()
        self.assertFalse(self.gcs._data_retrieved)
        self.assertIsNone(self.gcs._exists)

    def test_get_data(self):
        """Class doesn't implement _get_data method."""
        fill = self.test_class(None)
        self.assertRaises(NotImplementedError, fill._get_data)

    @mock.patch('gcs_client.base.Fillable._get_data')
    def test_auto_fill_get_existing_attr(self, mock_get_data):
        """Getting an attribute that exists on the model.

        When requesting a non exiting attribute the Fillable class will first
        get data (calling _get_data method) and create attributes in the object
        with that data, then try to return requested attribute.

        This test confirms that for an valid attribute we can retrieve it and
        return it.
        """
        mock_get_data.return_value = {'name': mock.sentinel.name}
        fill = self.test_class(None)
        self.assertEquals(mock.sentinel.name, fill.name)
        self.assertTrue(fill._exists)
        self.assertTrue(fill._data_retrieved)
        mock_get_data.assert_called_once_with()

        # Calling non existing attribute will not trigger another _get_data
        # call
        mock_get_data.reset_mock()
        self.assertRaises(AttributeError, getattr, fill, 'wrong_name')
        self.assertFalse(mock_get_data.called)

    @mock.patch('gcs_client.base.Fillable._get_data')
    def test_auto_fill_skip_assignment(self, mock_get_data):
        """Getting an attribute skipping existing attribute.

        When requesting a non exiting attribute the Fillable class will first
        get data (calling _get_data method) and create attributes in the object
        with that data, then try to return requested attribute.

        This test confirms that the filling of attributes will overshadow
        existing attributes.
        """
        mock_get_data.return_value = {'size': mock.sentinel.gcs_size,
                                      'name': mock.sentinel.name}
        fill = self.test_class(mock.sentinel.original_credentials)
        fill.size = mock.sentinel.my_size
        # We check that retrieving an initialized attribute doesn't trigger
        # gcs data retrieval
        self.assertEquals(mock.sentinel.my_size, fill.size)
        self.assertFalse(mock_get_data.called)
        # Getting an unkown field will trigger the data retrieval
        self.assertEquals(mock.sentinel.name, fill.name)
        mock_get_data.assert_called_once_with()
        self.assertTrue(fill._exists)
        self.assertTrue(fill._data_retrieved)
        # And now retrieved size will overshadow the one we initialized
        self.assertEquals(mock.sentinel.gcs_size, fill.size)
        # But we'll still have access to the original one in __dict__
        self.assertEquals(mock.sentinel.my_size, fill.__dict__['size'])

        # Calling non existing attribute will not trigger another _get_data
        # call
        mock_get_data.reset_mock()
        self.assertRaises(AttributeError, getattr, fill, 'wrong_name')
        self.assertFalse(mock_get_data.called)

    @mock.patch('gcs_client.base.Fillable._get_data')
    def test_auto_fill_get_nonexistent_attr(self, mock_get_data):
        """Getting an attribute that exists on the model.

        When requesting a non exiting attribute the Fillable class will first
        get data (calling _get_data method) and create attributes in the object
        with that data, then try to return requested attribute.

        This test confirms that for an invalid attribute we can retrieve the
        data but we'll still return an AttributeError exception.
        """
        mock_get_data.return_value = {'name': mock.sentinel.name}
        fill = self.test_class(None)
        self.assertRaises(AttributeError, getattr, fill, 'wrong_name')
        self.assertTrue(fill._exists)
        self.assertTrue(fill._data_retrieved)
        mock_get_data.assert_called_once_with()

        # Calling another non existing attribute will not trigger another
        # _get_data call
        mock_get_data.reset_mock()
        self.assertRaises(AttributeError, getattr, fill, 'another_wrong_name')
        self.assertFalse(mock_get_data.called)

    @mock.patch('gcs_client.base.Fillable._get_data')
    def test_auto_fill_doesnt_exist(self, mock_get_data):
        """Raises Attribute error for non existing resource."""
        mock_get_data.side_effect = gcs_errors.NotFound()
        fill = self.test_class(None)
        self.assertRaises(AttributeError, getattr, fill, 'name')
        self.assertFalse(fill._exists)
        self.assertFalse(fill._data_retrieved)
        mock_get_data.assert_called_once_with()

    @mock.patch('gcs_client.base.Fillable._get_data')
    def test_auto_fill_other_http_error(self, mock_get_data):
        """Raises HTTP exception on non expected HTTP exceptions."""
        mock_get_data.side_effect = gcs_errors.BadRequest()
        fill = self.test_class(None)
        self.assertRaises(gcs_errors.BadRequest, getattr, fill, 'name')
        self.assertFalse(fill._exists)
        self.assertFalse(fill._data_retrieved)
        mock_get_data.assert_called_once_with()

    @mock.patch('gcs_client.base.Fillable._get_data')
    def test_obj_from_data(self, mock_get_data):
        """Test _obj_from_data class method."""
        data = {'name': 'my_name', 'one_entry_dict': {'value': '1dict'},
                'multi_entry_dict': {1: 1, 2: 2}}
        fill = self.test_class._obj_from_data(data, mock.sentinel.credentials)
        self.assertFalse(fill._exists)
        self.assertTrue(fill._data_retrieved)
        self.assertEqual('my_name', fill.name)
        self.assertEqual('1dict', fill.one_entry_dict)
        self.assertDictEqual({1: 1, 2: 2}, fill.multi_entry_dict)

        # Check that it will not try to retrieve data for non existing
        # attributes
        self.assertRaises(AttributeError, getattr, fill, 'wrong_name')
        self.assertFalse(mock_get_data.called)
