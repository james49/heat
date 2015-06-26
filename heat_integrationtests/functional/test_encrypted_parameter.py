#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import yaml
import ConfigParser
import re
import MySQLdb
import json
import ipdb

from heat_integrationtests.common import test

class EncryptedParametersTest(test.HeatIntegrationTest):

    heat_conf = '/etc/heat/heat.conf'

    template = '''
heat_template_version: 2013-05-23
parameters:
  foo:
    type: string
    description: Parameter with encryption turned on 
    hidden: true 
    default: secret 
resources:
  random_key_name:
    type: OS::Heat::RandomString
    properties:
      length: 8
outputs:
  encrypted_foo_param:
    description: ''
    value: {get_param: foo}
'''

    def setUp(self):
        super(EncryptedParametersTest, self).setUp()
        self.client = self.orchestration_client

    def test_db_encryption(self):
       
        # Create a stack with a non-default value for 'foo' to be encrypted 
        foo_param = 'my_encrypted_foo'
        stack_identifier = self.stack_create(
            template=self.template,
            parameters={'foo':foo_param}
        )
        stack = self.client.stacks.get(stack_identifier)

        # Check that the stack's output value for the 'foo' parameter is viewable and matches the parameter value 
        for out in stack.outputs:
            if out['output_key'] == 'encrypted_foo_param':
                self.assertEqual(foo_param, out['output_value'])

        # Query the mysql database to ensure that encryption has taken place for the 'foo' parameter
        sql = """
		select environment 
		from raw_template inner join stack on raw_template.id=stack.raw_template_id
		where stack.id=%s
              """ 
        user_name,user_password,host_ip = self.get_db_credentials()
        conn = MySQLdb.connect(host=host_ip, user=user_name, passwd=user_password)
        conn.select_db('heat')
        cursor = conn.cursor()
        cursor.execute(sql, (stack.id))
        for row in cursor.fetchall():
            query_return=row[0]
        cursor.close()
        conn.close()

        # Instantiate a json object representing the environment field of the raw_template table and get the foo parameter 
	environment_field_obj = json.loads(query_return)
        foo_params = environment_field_obj["parameters"]["foo"]
        # Assert that the values are not equal to the original foo parameter
        for i in foo_params:
            self.assertNotEqual(foo_param, i)

    def get_db_credentials(self):
        config = ConfigParser.RawConfigParser()
        config.read(self.heat_conf)
        db_connection_conf = config.get('database', 'connection')
        # The connection value should be in the following form:  mysql+pymysql://<username>:<password>@127.0.0.1/heat?charset=utf8
        # First, parse to get the username and password
        try:
            found = re.search('//(.+?)@', db_connection_conf).group(1)
        except AttributeError:
            found = '' 
            self.assertTrue(False,'unable to parse db configuration for username/password')
        username = found.split(':')[0]
        password = found.split(':')[1]

        # Secondly, parse to get the ip to use to connect to the db
        try:
            found = re.search('@(.+?)/', db_connection_conf).group(1)
        except AttributeError:
            found = ''
            self.assertTrue(False,'unable to parse db configuration for host ip')
        host_ip = found.split(':')[0]

        return username, password, host_ip
