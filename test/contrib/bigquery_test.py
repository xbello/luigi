# -*- coding: utf-8 -*-
#
# Copyright 2015 Twitter Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
These are the unit tests for the Bigquery-luigi binding.
"""


import luigi
from luigi.contrib import bigquery

from helpers import unittest
from mock import MagicMock

PROJECT_ID = 'projectid'
DATASET_ID = 'dataset'


class TestRunQueryTask(bigquery.BigqueryRunQueryTask):
    client = MagicMock()
    query = ''' SELECT 'hello' as field1, 2 as field2 '''
    table = luigi.Parameter()

    def output(self):
        return bigquery.BigqueryTarget(PROJECT_ID, DATASET_ID, self.table, client=self.client)


class TestRunQueryTaskWithRequires(bigquery.BigqueryRunQueryTask):
    client = MagicMock()
    table = luigi.Parameter()

    def requires(self):
        return TestRunQueryTask(table='table1')

    @property
    def query(self):
        requires = self.requires().output().table
        dataset = requires.dataset_id
        table = requires.table_id
        return 'SELECT * FROM [{dataset}.{table}]'.format(dataset=dataset, table=table)

    def output(self):
        return bigquery.BigqueryTarget(PROJECT_ID, DATASET_ID, self.table, client=self.client)


class BulkCompleteTest(unittest.TestCase):

    def test_bulk_complete(self):
        parameters = ['table1', 'table2']

        client = MagicMock()
        client.dataset_exists.return_value = True
        client.list_tables.return_value = ['table2', 'table3']
        TestRunQueryTask.client = client

        complete = list(TestRunQueryTask.bulk_complete(parameters))
        self.assertEquals(complete, ['table2'])

    def test_dataset_doesnt_exist(self):
        client = MagicMock()
        client.dataset_exists.return_value = False
        TestRunQueryTask.client = client

        complete = list(TestRunQueryTask.bulk_complete(['table1']))
        self.assertEquals(complete, [])


class RunQueryTest(unittest.TestCase):

    def test_query_property(self):
        task = TestRunQueryTask(table='table2')
        task.client = MagicMock()
        task.run()

        (_, job), _ = task.client.run_job.call_args
        query = job['configuration']['query']['query']
        self.assertEqual(query, TestRunQueryTask.query)

    def test_override_query_property(self):
        task = TestRunQueryTaskWithRequires(table='table2')
        task.client = MagicMock()
        task.run()

        (_, job), _ = task.client.run_job.call_args
        query = job['configuration']['query']['query']

        expected_table = '[' + DATASET_ID + '.' + task.requires().output().table.table_id + ']'
        self.assertIn(expected_table, query)
        self.assertEqual(query, task.query)
