#
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

from heat.engine.clients import client_plugin
from heat.engine import constraints
from manilaclient import client as manila_client
from manilaclient import exceptions

MANILACLIENT_VERSION = "1"


class ManilaClientPlugin(client_plugin.ClientPlugin):

    exceptions_module = exceptions
    service_types = ['share']

    def _create(self):
        endpoint_type = self._get_client_option('manila', 'endpoint_type')
        endpoint = self.url_for(service_type=self.service_types[0],
                                endpoint_type=endpoint_type)

        args = {
            'service_catalog_url': endpoint,
            'input_auth_token': self.auth_token
        }

        client = manila_client.Client(MANILACLIENT_VERSION, **args)
        return client

    def is_not_found(self, ex):
        return isinstance(ex, exceptions.NotFound)

    def is_over_limit(self, ex):
        return isinstance(ex, exceptions.RequestEntityTooLarge)

    def is_conflict(self, ex):
        return isinstance(ex, exceptions.Conflict)

    @staticmethod
    def _find_resource_by_id_or_name(id_or_name, resource_list,
                                     resource_type_name):
        """The method is trying to find id or name in item_list

        The method searches item with id_or_name in list and returns it.
        If there is more than one value or no values then it raises an
        exception

        :param id_or_name: resource id or name
        :param resource_list: list of resources
        :param resource_type_name: name of resource type that will be used
                                   for exceptions
        :raises NotFound, NoUniqueMatch
        :return: resource or generate an exception otherwise
        """
        search_result_by_id = [res for res in resource_list
                               if res.id == id_or_name]
        if search_result_by_id:
            return search_result_by_id[0]
        else:
            # try to find resource by name
            search_result_by_name = [res for res in resource_list
                                     if res.name == id_or_name]
            match_count = len(search_result_by_name)
            if match_count > 1:
                message = ("Ambiguous {0} name '{1}'. Found more than one "
                           "{0} for this name in Manila."
                           ).format(resource_type_name, id_or_name)
                raise exceptions.NoUniqueMatch(message)
            elif match_count == 1:
                return search_result_by_name[0]
            else:
                message = ("{0} '{1}' was not found in Manila. Please "
                           "use the identity of existing {0} in Heat "
                           "template.").format(resource_type_name, id_or_name)
                raise exceptions.NotFound(message=message)

    def get_share_type(self, share_type_identity):
        return self._find_resource_by_id_or_name(
            share_type_identity,
            self.client().share_types.list(),
            "share type"
        )

    def get_share_network(self, share_network_identity):
        return self._find_resource_by_id_or_name(
            share_network_identity,
            self.client().share_networks.list(),
            "share network"
        )

    def get_share_snapshot(self, snapshot_identity):
        return self._find_resource_by_id_or_name(
            snapshot_identity,
            self.client().share_snapshots.list(),
            "share snapshot"
        )


class ManilaShareBaseConstraint(constraints.BaseCustomConstraint):
    # check that exceptions module has been loaded. Without this check
    # doc tests on gates will fail
    expected_exceptions = (exceptions.NotFound, exceptions.NoUniqueMatch)

    def validate_with_client(self, client, resource_id):
        getattr(client.client_plugin("manila"), self.resource_getter_name)(
            resource_id)


class ManilaShareNetworkConstraint(ManilaShareBaseConstraint):
    resource_getter_name = 'get_share_network'


class ManilaShareTypeConstraint(ManilaShareBaseConstraint):
    resource_getter_name = 'get_share_type'


class ManilaShareSnapshotConstraint(ManilaShareBaseConstraint):
    resource_getter_name = 'get_share_snapshot'
